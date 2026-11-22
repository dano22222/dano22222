"""euro and us dollar exchange rates from the norges bank (nb) open data api.

norges bank publishes one middle rate per norwegian business day (no rates on
weekends and holidays). the api follows the sdmx standard; the csv format is
the simplest to parse. a rate is the price in nok of 10**unit_mult units of
the base currency (unit_mult is 0 for eur and usd, so 1 eur = x nok).

timezone: the dates are norwegian calendar dates without a time of day, so
they are treated as europe/oslo dates and never shifted to utc.
"""
from io import StringIO
import pandas as pd
import requests

URL = 'https://data.norges-bank.no/api/data/EXR/B.{currencies}.NOK.SP'
CURRENCIES = ('EUR', 'USD')


def parse_exchange_csv(text):
    """turn the norges bank csv answer into a table with one column per currency.

    the separator is detected automatically, and comma decimals (norwegian
    locale) are accepted as well, so the parser works for both locale=en and
    locale=no. returns a dataframe indexed by date with columns such as EUR and USD.
    """
    raw = pd.read_csv(StringIO(text.lstrip('﻿')), sep=None, engine='python', dtype=str)
    #the csv repeats each dimension as a code and a label; the codes are upper case
    needed = {'BASE_CUR', 'TIME_PERIOD', 'OBS_VALUE'}
    if not needed.issubset(raw.columns):
        raise ValueError(f'Unexpected Norges Bank columns: {list(raw.columns)[:8]}')
    values = pd.to_numeric(raw['OBS_VALUE'].str.replace(',', '.', regex=False), errors='coerce')
    #unit_mult says whether the rate is per 1, 100 or more units of the base currency
    if 'UNIT_MULT' in raw.columns:
        multiplier = pd.to_numeric(raw['UNIT_MULT'], errors='coerce').fillna(0)
    else:
        multiplier = 0
    table = pd.DataFrame({'date': pd.to_datetime(raw['TIME_PERIOD']),
                          'currency': raw['BASE_CUR'].str.upper(),
                          'nok_per_unit': values / 10 ** multiplier})
    table = table.dropna(subset=['nok_per_unit'])
    wide = table.pivot_table(index='date', columns='currency', values='nok_per_unit', aggfunc='last')
    wide.columns.name = None
    wide.index.name = 'date'
    return wide.sort_index()


def fetch_exchange_rates(start, end, currencies=CURRENCIES, session=None, timeout=30):
    """download daily nok exchange rates for the given currencies (default eur and usd).

    start and end are dates (yyyy-mm-dd). returns a dataframe with a
    DatetimeIndex of business days and one column per currency (nok per unit).
    raises an error when the api answers with an error or with no data.
    """
    currencies = [c.upper() for c in currencies]
    if not currencies:
        raise ValueError('Choose at least one currency.')
    if pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError('Start must not follow end.')
    session = session or requests.Session()
    response = session.get(URL.format(currencies='+'.join(currencies)),
                           params={'format': 'csv', 'startPeriod': str(pd.Timestamp(start).date()),
                                   'endPeriod': str(pd.Timestamp(end).date()), 'locale': 'en'},
                           timeout=timeout)
    response.raise_for_status()
    rates = parse_exchange_csv(response.text)
    missing = [c for c in currencies if c not in rates.columns]
    if rates.empty or missing:
        raise ValueError(f'No exchange rates returned for {missing or currencies}.')
    return rates[currencies]


def weekly_rates(rates):
    """weekly mean rate for weeks ending on sunday, the same weeks as the nve reservoir statistics."""
    return rates.resample('W-SUN').mean()
