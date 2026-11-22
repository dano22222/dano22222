"""helpers that turn norwegian calendar periods into utc limits for queries on utc timestamps."""
import pandas as pd

LOCAL = 'Europe/Oslo'


def oslo_year_utc_limits(year):
    """utc start (included) and end (excluded) of a norwegian calendar year.

    for example 2025 starts at 2024-12-31 23:00 utc, because oslo is utc+1 in
    winter. querying a utc database with these limits gives exactly the hours
    of the norwegian year, unlike a filter on a year field computed in utc.
    """
    start = pd.Timestamp(f'{int(year)}-01-01', tz=LOCAL).tz_convert('UTC')
    end = pd.Timestamp(f'{int(year) + 1}-01-01', tz=LOCAL).tz_convert('UTC')
    return start, end
