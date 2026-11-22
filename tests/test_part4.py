"""part 4 tests: norges bank parser, daily weather, weekly alignment, correlation and river forecasts (no network)."""
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from src.currency import parse_exchange_csv, fetch_exchange_rates, weekly_rates
from src.correlation import sliding_correlation, lag_scan, align_weekly
from src.forecast import forecast_filling, backtest, seasonal_naive, future_exog, combine_exog
from src.weather import weekly_weather, download_daily, DAILY_VARIABLES, DAILY_UNITS

#csv in the layout returned by norges bank (codes and labels for each dimension)
CSV = ('FREQ;Frequency;BASE_CUR;Base Currency;QUOTE_CUR;Quote Currency;TENOR;Tenor;DECIMALS;Decimals;'
       'CALCULATED;Calculated;UNIT_MULT;Unit Multiplier;COLLECTION;Collection Indicator;TIME_PERIOD;OBS_VALUE\n'
       'B;Business;EUR;Euro;NOK;Norwegian krone;SP;Spot;4;4;false;false;0;Units;C;ECB concertation time 14:15 CET;2025-01-02;11.7915\n'
       'B;Business;EUR;Euro;NOK;Norwegian krone;SP;Spot;4;4;false;false;0;Units;C;ECB concertation time 14:15 CET;2025-01-03;11.8000\n'
       'B;Business;USD;US dollar;NOK;Norwegian krone;SP;Spot;4;4;false;false;0;Units;C;ECB concertation time 14:15 CET;2025-01-02;11.4000\n'
       'B;Business;USD;US dollar;NOK;Norwegian krone;SP;Spot;4;4;false;false;0;Units;C;ECB concertation time 14:15 CET;2025-01-03;11.4500\n'
       'B;Business;JPY;Japanese yen;NOK;Norwegian krone;SP;Spot;4;4;false;false;2;Hundreds;C;ECB;2025-01-03;7,2000\n')


def test_parse_exchange_csv_wide_table_and_unit_multiplier():
    rates = parse_exchange_csv(CSV)
    assert list(rates.columns) == ['EUR', 'JPY', 'USD']
    assert rates.loc['2025-01-02', 'EUR'] == pytest.approx(11.7915)
    #jpy is quoted per 100 units with a comma decimal; the parser gives nok per one yen
    assert rates.loc['2025-01-03', 'JPY'] == pytest.approx(.072)


def test_fetch_exchange_rates_builds_request_and_checks_currencies():
    session = MagicMock()
    session.get.return_value.text = CSV
    rates = fetch_exchange_rates('2025-01-01', '2025-01-05', session=session)
    url = session.get.call_args.args[0]
    assert url.endswith('/EXR/B.EUR+USD.NOK.SP') and list(rates.columns) == ['EUR', 'USD']
    assert session.get.call_args.kwargs['params']['format'] == 'csv'
    with pytest.raises(ValueError):
        fetch_exchange_rates('2025-01-01', '2025-01-05', currencies=['GBP'], session=session)
    with pytest.raises(ValueError):
        fetch_exchange_rates('2025-02-01', '2025-01-05', session=session)


def test_weekly_rates_use_weeks_ending_sunday():
    rates = parse_exchange_csv(CSV)
    weekly = weekly_rates(rates)
    assert weekly.index[0] == pd.Timestamp('2025-01-05') and weekly.index[0].day_name() == 'Sunday'


def fake_daily_payload(n, start, end):
    days = pd.date_range(start, end, freq='D')
    one = {'daily_units': DAILY_UNITS, 'daily': {'time': [d.strftime('%Y-%m-%d') for d in days],
                                                  **{v: list(np.arange(len(days), dtype=float)) for v in DAILY_VARIABLES}}}
    return [one] * n if n > 1 else one


def test_download_daily_requests_oslo_days_and_parses_units():
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = fake_daily_payload(2, '2024-01-01', '2024-01-14')
    frames = download_daily([60, 61], [10, 11], '2024-01-01', '2024-01-14', session=session)
    params = session.get.call_args.kwargs['params']
    assert params['timezone'] == 'Europe/Oslo' and params['models'] == 'era5'
    assert len(frames) == 2 and len(frames[0]) == 14


def test_weekly_weather_sums_amounts_and_rejects_partial_weeks():
    days = pd.date_range('2024-01-01', '2024-01-17', freq='D')
    daily = pd.DataFrame({'temperature_2m_mean': 1., 'precipitation_sum': 2.}, index=days)
    weekly = weekly_weather(daily)
    assert weekly.index[0] == pd.Timestamp('2024-01-07')
    assert weekly.loc['2024-01-07', 'precipitation_sum'] == 14 and weekly.loc['2024-01-07', 'temperature_2m_mean'] == 1
    #the third week has only three days, so it is not used
    assert weekly.loc['2024-01-21'].isna().all()


def test_utc_and_oslo_days_differ_for_hourly_data():
    #one hour of rain at 23:30 utc on 31 december belongs to 1 january in norway
    index = pd.date_range('2024-12-31 00:00', '2025-01-01 23:00', freq='h', tz='UTC')
    rain = pd.Series(0., index=index)
    rain['2024-12-31 23:00'] = 5
    assert rain.resample('D').sum().iloc[0] == 5
    assert rain.tz_convert('Europe/Oslo').resample('D').sum().loc['2025-01-01'] == 5


def weekly_signal(years=8, noise=0., seed=0):
    rng = np.random.default_rng(seed)
    index = pd.date_range('2010-01-03', periods=52 * years, freq='W-SUN')
    season = .55 + .3 * np.sin(2 * np.pi * (index.day_of_year.to_numpy() / 365.25 - .4))
    return pd.Series(np.clip(season + noise * rng.normal(size=len(index)), 0, 1), index=index)


def test_sliding_correlation_detects_known_lag():
    x = weekly_signal(noise=.05, seed=1)
    y = x.shift(3)
    scan = lag_scan(x, y, lags=range(-6, 7))
    assert scan.idxmax() == 3 and scan.max() > .99
    frame = sliding_correlation(x, y, lag=3, window=26)
    assert frame.correlation.dropna().min() > .99
    with pytest.raises(ValueError):
        sliding_correlation(x, y, lag=0, window=2)
    with pytest.raises(ValueError):
        align_weekly(x.loc[:'2011'], y.loc['2013':])


@pytest.mark.parametrize('model', ['lags', 'snarimax'])
def test_forecast_shapes_interval_and_bounds(model):
    series = weekly_signal()
    result = forecast_filling(series, model=model, train_end='2016-06-26', history_years=5, horizon=20)
    assert len(result.forecast) == 20 and result.forecast.index[0] == pd.Timestamp('2016-07-03')
    assert (result.forecast.lower <= result.forecast.forecast).all()
    assert (result.forecast.forecast <= result.forecast.upper).all()
    assert result.forecast.to_numpy().min() >= 0 and result.forecast.to_numpy().max() <= 100
    assert result.scores()['weeks_compared'] == 20


def test_lag_model_learns_a_clean_seasonal_signal():
    series = weekly_signal(years=12)
    result = forecast_filling(series, model='lags', train_end='2019-12-29', history_years=8, horizon=26)
    naive = seasonal_naive(series, '2019-12-29', 26)
    assert result.scores()['mae'] < 5 and len(naive) == 26


def test_forecast_with_exogenous_sources_and_future_strategies():
    series = weekly_signal(years=8)
    exog = {'weather': pd.DataFrame({'temperature_2m_mean': np.sin(np.arange(len(series)) / 8.3)}, index=series.index),
            'currency': pd.DataFrame({'EUR': np.linspace(9, 12, len(series))}, index=series.index)}
    result = forecast_filling(series, exog, train_end='2015-12-27', horizon=10, history_years=5)
    assert result.exog_columns == ['weather__temperature_2m_mean', 'currency__EUR']
    table = combine_exog(exog)
    future = pd.date_range('2016-01-03', periods=10, freq='W-SUN')
    estimated = future_exog(table, result.history, future, 'climatology')
    assert (estimated['currency__EUR'] == table.loc[:'2015-12-27', 'currency__EUR'].iloc[-1]).all()
    observed = future_exog(table, result.history, future, 'observed')
    np.testing.assert_allclose(observed['currency__EUR'], table['currency__EUR'].reindex(future))


def test_forecast_rejects_bad_settings():
    series = weekly_signal(years=3)
    with pytest.raises(ValueError):
        forecast_filling(series, model='prophet')
    with pytest.raises(ValueError):
        forecast_filling(series, history_years=1)
    with pytest.raises(ValueError):
        forecast_filling(series, resolution='D')
    with pytest.raises(ValueError):
        forecast_filling(series, unknown_parameter=1)


def test_backtest_reports_mean_errors():
    table = backtest(weekly_signal(years=10), horizon=8, model='lags', history_years=5,
                     origins=pd.to_datetime(['2017-06-25', '2018-06-24']))
    assert len(table) == 2 and set(table.attrs['mean']) >= {'mae', 'rmse', 'coverage'}
