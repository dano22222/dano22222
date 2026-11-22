"""forecast of reservoir filling with river (snarimax or a lag based machine learning model).

all model parameters and exogenous variables can be chosen. the training
period and the horizon can follow the map time frame: the model is then
trained on the weeks before the frame and forecasts the frame itself, so the
forecast can be compared with what really happened. without the link the
training ends at the chosen date (default: the latest nve week) and the
forecast goes into the future. the default settings are the best ones from
the tests in the part 4 notebook.
"""
import pandas as pd
import pymongo.errors
import requests
import streamlit as st
from nve_api import load_reservoir_data
from src import data
from src.currency import weekly_rates
from src.forecast import DEFAULTS, DEFAULT_WEATHER, RESOLUTIONS, forecast_filling
from src.geography import region_key
from src.plots import forecast_figure
from src.reservoir import weekly_series
from src.ui import page_header, area_selector, area_label, show
from src.weather import DAILY_VARIABLES, WEATHER_LABELS, WeatherRateLimit, latest_era5_date

page_header('Predict', 'Forecast filling',
            'Dynamic forecasts of the reservoir filling with River, with prediction intervals from quantile loss.')

try:
    df = load_reservoir_data()
    kind, area = area_selector(df)
    target = weekly_series(df, kind, area)
except Exception as error:
    st.error(f'Unable to prepare the reservoir series: {error}')
    st.stop()
region = region_key(kind, area)
last_week = target.index.max()

#training period and horizon, optionally synced with the map time frame
st.subheader('Training period and horizon')
has_frame = 'time_frame' in st.session_state
sync = st.toggle('Forecast the time frame chosen on the map', value=has_frame,
                 help='Training ends the week before the map time frame, and the horizon covers the frame.')
history_years = st.slider('Length of training history (years)', 3, 30, DEFAULTS['history_years'])
if sync:
    frame_start, frame_end = st.session_state.get('time_frame', (last_week - pd.Timedelta(weeks=25), last_week))
    train_end = pd.Timestamp(frame_start) - pd.Timedelta(weeks=1)
    horizon = max(1, int((pd.Timestamp(frame_end) - pd.Timestamp(frame_start)).days // 7) + 1)
    st.caption(f'Map time frame {pd.Timestamp(frame_start):%d.%m.%Y}–{pd.Timestamp(frame_end):%d.%m.%Y}: training ends '
               f'{train_end:%d.%m.%Y}, horizon {horizon} weeks. Change the frame on the map page.')
else:
    left, right = st.columns(2)
    train_end = pd.Timestamp(left.date_input('Last training week', value=last_week.date(),
                                             min_value=(target.index.min() + pd.Timedelta(weeks=160)).date(),
                                             max_value=last_week.date()))
    horizon = right.slider('Forecast horizon (weeks)', 1, 104, DEFAULTS['horizon'])

#model and its parameters (local settings with the notebook defaults)
with st.expander('Model settings', expanded=True):
    left, middle, right = st.columns(3)
    model = left.radio('Model', ['lags', 'snarimax'], index=['lags', 'snarimax'].index(DEFAULTS['model']), key='forecast_model',
                       format_func={'lags': 'Lag based ML (River linear regression)', 'snarimax': 'SARIMAX (River SNARIMAX)'}.get)
    resolution = middle.selectbox('Time resolution', list(RESOLUTIONS), format_func={'W': 'Weekly', '2W': 'Two weeks', '4W': 'Four weeks'}.get,
                                  help='Weekly is the native NVE resolution and gave the best results in the notebook.')
    interval = right.select_slider('Prediction interval', [.5, .8, .9, .95], value=DEFAULTS['interval'], format_func=lambda v: f'{v:.0%}')
    parameters = {'model': model, 'interval': interval}
    columns = st.columns(4)
    if model == 'snarimax':
        names = [('p', 'AR order p'), ('d', 'Differencing d'), ('q', 'MA order q'), ('sp', 'Seasonal AR P'),
                 ('sd', 'Seasonal differencing D'), ('sq', 'Seasonal MA Q')]
        for i, (name, label) in enumerate(names):
            parameters[name] = columns[i % 4].number_input(label, 0, 4 if name in 'pq' else 2, DEFAULTS[name])
        st.caption('The seasonal period m is one year (52 weeks, 26 or 13 periods at coarser resolutions).')
    else:
        parameters['lags'] = columns[0].number_input('Number of lagged changes', 1, 12, DEFAULTS['lags'])
        parameters['seasonal_lag'] = columns[1].checkbox('Use the change one year earlier', DEFAULTS['seasonal_lag'])
        parameters['epochs'] = columns[2].number_input('Passes over the training data', 1, 10, DEFAULTS['epochs'])
    parameters['learning_rate'] = columns[3].select_slider('Learning rate (SGD)', [.0003, .001, .003, .01, .03, .1],
                                                           value=DEFAULTS['learning_rate'])

#exogenous variables
with st.expander('Exogenous variables', expanded=True):
    sources = st.multiselect('Data sources', ['weather', 'currency', 'electricity'], default=list(DEFAULTS['exog']),
                             format_func={'weather': 'Weather (Open-Meteo ERA5)', 'currency': 'Exchange rates (Norges Bank)',
                                          'electricity': 'Net export NO2–DK1 (MongoDB, from Oct 2024)'}.get)
    weather_variables = st.multiselect('Weather variables', DAILY_VARIABLES, default=list(DEFAULT_WEATHER),
                                       format_func=WEATHER_LABELS.get, disabled='weather' not in sources)
    future = st.radio('Exogenous values in the forecast period', ['climatology', 'observed'], horizontal=True,
                      format_func={'climatology': 'Estimated (weekly normal / last value)',
                                   'observed': 'Observed where available (perfect forecast)'}.get)

#download the selected exogenous data (cached, shared with the other pages)
exog = {}
first_day = f'{train_end.year - history_years - 1}-01-01'
last_day = str(latest_era5_date().date())
try:
    with st.spinner('Downloading exogenous data (the first download of ten years of weather takes one to two minutes, then it is cached)...'):
        if 'weather' in sources and weather_variables:
            exog['weather'] = data.weekly_weather(region, first_day, last_day, 3)[weather_variables]
        if 'currency' in sources:
            exog['currency'] = weekly_rates(data.exchange_rates(first_day, str(pd.Timestamp.now().date())))
        if 'electricity' in sources:
            exog['electricity'] = data.weekly_net_export()
except WeatherRateLimit as error:
    st.warning(f'{error} The forecast is made without weather.')
    exog.pop('weather', None)
except (requests.RequestException, ValueError, RuntimeError, pymongo.errors.PyMongoError) as error:
    st.warning(f'Some exogenous data could not be loaded ({error}); the forecast uses the remaining sources.')

#train and forecast with a progress bar for the three models (forecast, lower and upper limit)
progress = st.progress(0., text='Preparing the forecast...')
try:
    result = forecast_filling(target, exog, train_end=train_end, history_years=history_years, horizon=horizon,
                              resolution=resolution, future=future,
                              progress=lambda share, text: progress.progress(share, text=text), **parameters)
except ValueError as error:
    progress.empty()
    st.error(f'The forecast could not be made with these settings: {error}')
    st.stop()
progress.empty()

st.subheader(f'Forecast for {area_label(kind, area)}')
title = f"{model.upper() if model == 'snarimax' else 'Lag based ML'} | trained to {result.history.index[-1]:%d.%m.%Y} | {horizon} weeks ({result.settings['steps']} periods)"
show(forecast_figure(result, title, animate=True))
scores = result.scores()
columns = st.columns(4)
columns[0].metric('Training periods', f'{len(result.history):,}')
columns[1].metric('Run time', f'{result.seconds:.2f} s')
columns[2].metric('MAE (percentage points)', f"{scores['mae']:.1f}" if scores else 'future')
columns[3].metric('Interval coverage', f"{scores['coverage']:.0%}" if scores else 'future')
st.caption('Press ▶ Play to see the dynamic forecast step by step. The band comes from two extra models trained '
           'with River quantile loss (optim.losses.Quantile). Exogenous variables used: '
           f"{', '.join(result.exog_columns) or 'none'}.")
with st.expander('Forecast table'):
    table = result.forecast.join(result.actual.rename('observed'))
    st.dataframe(table.round(2), width='stretch')
    st.download_button('Download forecast', table.to_csv().encode(), file_name=f'forecast_{kind}{area}.csv')
