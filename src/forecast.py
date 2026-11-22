"""forecasting of reservoir filling with the river online learning framework.

two model families are available:
  snarimax  river.time_series.SNARIMAX: seasonal arima with exogenous
            variables, where the coefficients are fitted online by a linear
            regressor (one pass over the training data).
  lags      a lag based machine learning model: a river linear regression on
            the last weekly changes, the change one year earlier, the season
            (week of year as sine and cosine) and the exogenous variables. it
            predicts the change in filling and is applied recursively.

both forecasts are dynamic: after the training period the model only sees its
own predictions, never the true filling. exogenous variables in the forecast
period are unknown in a real forecast, so weather (and electricity) use the
average for the same week of the year in the training data (climatology) and
exchange rates keep their last known value (persistence). future_exog=
'observed' instead uses the measured values when they exist, which shows the
best case with a perfect weather forecast.

prediction intervals come from extra models trained with the quantile
(pinball) loss, river.optim.losses.Quantile(alpha), one for each limit.

the filling fraction is handled in percent (0 to 100), which gives the
stochastic gradient descent better scaled gradients than fractions.
"""
from dataclasses import dataclass, field
import math
import time
import numpy as np
import pandas as pd
from river import compose, linear_model, optim, preprocessing, time_series

#time resolutions that can be used, with their pandas rule and the number of steps per year
RESOLUTIONS = {'W': ('W-SUN', 52), '2W': ('2W-SUN', 26), '4W': ('4W-SUN', 13)}

#how unknown future values of each exogenous source are filled in
FUTURE_STRATEGY = {'weather': 'climatology', 'electricity': 'climatology', 'currency': 'persistence'}

#best setting from the tests in the part 4 notebook (used as default in streamlit)
DEFAULTS = {'model': 'lags', 'resolution': 'W', 'history_years': 10, 'horizon': 26,
            'p': 2, 'd': 1, 'q': 0, 'sp': 1, 'sd': 1, 'sq': 0,
            'lags': 1, 'seasonal_lag': False, 'learning_rate': 0.003, 'epochs': 3,
            'interval': 0.9, 'exog': ()}


@dataclass
class ForecastResult:
    """everything the notebook and the app need to plot and judge a forecast."""
    history: pd.Series
    forecast: pd.DataFrame
    actual: pd.Series
    settings: dict
    seconds: float
    exog_columns: list = field(default_factory=list)

    def scores(self):
        """mean absolute and root mean square error (percentage points) where the truth is known."""
        joined = self.forecast.join(self.actual.rename('actual'), how='inner').dropna(subset=['actual'])
        if joined.empty:
            return {}
        error = joined['forecast'] - joined['actual']
        scores = {'mae': float(error.abs().mean()), 'rmse': float(np.sqrt((error ** 2).mean())),
                  'weeks_compared': int(len(joined))}
        if {'lower', 'upper'}.issubset(joined.columns):
            inside = (joined['actual'] >= joined['lower']) & (joined['actual'] <= joined['upper'])
            scores['coverage'] = float(inside.mean())
        return scores


def resample_series(series, resolution='W'):
    """mean filling per period; 'W' keeps the native weekly resolution of the nve data."""
    if resolution not in RESOLUTIONS:
        raise ValueError(f'Resolution must be one of {list(RESOLUTIONS)}.')
    if resolution == 'W':
        return series
    return series.resample(RESOLUTIONS[resolution][0]).mean().dropna()


def combine_exog(exog, resolution='W'):
    """join the selected exogenous sources into one table with columns named source__variable."""
    if not exog:
        return pd.DataFrame()
    frames = []
    for source, frame in exog.items():
        frame = pd.DataFrame(frame).copy()
        frame.columns = [f'{source}__{c}' for c in frame.columns]
        if resolution != 'W':
            frame = frame.resample(RESOLUTIONS[resolution][0]).mean()
        frames.append(frame)
    return pd.concat(frames, axis=1).sort_index()


def future_exog(exog, train, future_index, how='climatology'):
    """exogenous values for the forecast period (see the module text for the strategies)."""
    if exog.empty:
        return pd.DataFrame(index=future_index)
    past = exog.loc[exog.index.isin(train.index)]
    result = pd.DataFrame(index=future_index, columns=exog.columns, dtype=float)
    for column in exog.columns:
        strategy = FUTURE_STRATEGY.get(column.split('__')[0], 'climatology')
        if strategy == 'persistence':
            result[column] = past[column].dropna().iloc[-1]
        else:
            #average for the same week of the year (week 53 is merged with week 52)
            normals = past[column].groupby(_week(past.index)).mean()
            result[column] = normals.reindex(_week(future_index)).to_numpy()
        if how == 'observed':
            #measured values replace the estimates where they exist
            observed = exog[column].reindex(future_index)
            result[column] = observed.fillna(result[column])
    return result.ffill().bfill()


def _regressor(learning_rate, loss=None, intercept=0.):
    """scaled linear regression trained online with stochastic gradient descent."""
    return (preprocessing.StandardScaler() |
            linear_model.LinearRegression(optimizer=optim.SGD(learning_rate), loss=loss,
                                          intercept_init=intercept, intercept_lr=learning_rate))


def _season(date, harmonics=2):
    """position in the year as sines and cosines, so week 52 and week 1 are neighbours.

    two harmonics allow a sharper seasonal shape (fast snow melt in spring,
    slow drawdown in winter) than a single sine curve.
    """
    angle = 2 * math.pi * (date.day_of_year / 365.25)
    features = {}
    for k in range(1, harmonics + 1):
        features[f'season_sin_{k}'] = math.sin(k * angle)
        features[f'season_cos_{k}'] = math.cos(k * angle)
    return features


def _week(index):
    """week of the year, with week 53 merged into week 52."""
    return np.minimum(pd.DatetimeIndex(index).isocalendar().week.to_numpy(), 52)


class SnarimaxModel:
    """thin wrapper around river's snarimax with the same interface as the lag model."""

    def __init__(self, p, d, q, sp, sd, sq, m, learning_rate, loss=None):
        self.model = time_series.SNARIMAX(p=p, d=d, q=q, m=m, sp=sp, sd=sd, sq=sq,
                                          regressor=_regressor(learning_rate, loss))

    def fit(self, y, x):
        for i, value in enumerate(y.to_numpy()):
            features = x.iloc[i].to_dict() if not x.empty else None
            self.model.learn_one(y=float(value), x=features)
        return self

    def predict(self, future_x, horizon):
        xs = [row.to_dict() for _, row in future_x.iterrows()] if future_x.shape[1] else None
        return np.asarray(self.model.forecast(horizon=horizon, xs=xs), dtype=float)


class LagModel:
    """river regression on lagged changes, season and exogenous variables (recursive forecast)."""

    def __init__(self, lags, seasonal_lag, steps_per_year, learning_rate, epochs=1, loss=None):
        self.lags, self.seasonal_lag, self.m = int(lags), bool(seasonal_lag), steps_per_year
        self.epochs = int(epochs)
        self.model = _regressor(learning_rate, loss)

    def _features(self, changes, date, exog_row):
        features = {f'change_lag_{k}': changes[-k] for k in range(1, self.lags + 1)}
        if self.seasonal_lag:
            #the change in the same period one year earlier
            features['change_last_year'] = changes[-self.m]
        #the average change for this week of the year in the training data
        features['normal_change'] = self.normal_change.get(min(date.isocalendar()[1], 52), 0.)
        features.update(_season(date))
        features.update(exog_row)
        return features

    def fit(self, y, x):
        values = y.to_numpy(dtype=float)
        changes = np.diff(values)
        start = max(self.lags, self.m if self.seasonal_lag else 0)
        if len(changes) <= start + 1:
            raise ValueError('Too little training history for the chosen lags.')
        #climatology of the weekly change, computed from the training data only
        self.normal_change = pd.Series(changes, index=_week(y.index[1:])).groupby(level=0).mean().to_dict()
        for _ in range(self.epochs):
            for i in range(start, len(changes)):
                row = x.iloc[i + 1].to_dict() if not x.empty else {}
                features = self._features(changes[:i], y.index[i + 1], row)
                self.model.learn_one(features, changes[i])
        self.last_level, self.changes = values[-1], list(changes)
        return self

    def predict(self, future_x, horizon):
        level, changes, out = self.last_level, list(self.changes), []
        for step in range(horizon):
            row = future_x.iloc[step].to_dict() if future_x.shape[1] else {}
            change = self.model.predict_one(self._features(changes, future_x.index[step], row))
            #the filling fraction can never leave 0 to 100 percent
            level = float(np.clip(level + change, 0, 100))
            changes.append(change)
            out.append(level)
        return np.asarray(out)


def _make_model(settings, steps_per_year, loss=None):
    if settings['model'] == 'snarimax':
        return SnarimaxModel(settings['p'], settings['d'], settings['q'], settings['sp'],
                             settings['sd'], settings['sq'], steps_per_year, settings['learning_rate'], loss)
    if settings['model'] == 'lags':
        return LagModel(settings['lags'], settings['seasonal_lag'], steps_per_year,
                        settings['learning_rate'], settings['epochs'], loss)
    raise ValueError("Model must be 'snarimax' or 'lags'.")


def forecast_filling(target, exog=None, train_end=None, history_years=None, horizon=None,
                     resolution=None, future='climatology', progress=None, **parameters):
    """train a river model on reservoir filling and forecast the coming periods.

    target         weekly filling fraction (0 to 1) of one magasinstatistikk area
    exog           dict {source: dataframe} of weekly exogenous variables, for
                   example {'weather': ..., 'currency': ...}; None or {} for none
    train_end      last date used for training (default: the last observation)
    history_years  length of the training history in years
    horizon        number of periods to forecast
    resolution     'W' (weekly), '2W' or '4W'
    future         'climatology' or 'observed' values of exogenous variables
    progress       optional callback(fraction, text) used by streamlit
    parameters     model settings: model, p, d, q, sp, sd, sq, lags,
                   seasonal_lag, learning_rate, epochs, interval (see DEFAULTS)
    returns a ForecastResult with the forecast in percent.
    """
    started = time.perf_counter()
    unknown = set(parameters) - set(DEFAULTS)
    if unknown:
        raise ValueError(f'Unknown parameters: {sorted(unknown)}')
    settings = {**DEFAULTS, **parameters,
                'history_years': history_years or DEFAULTS['history_years'],
                'horizon': int(horizon or DEFAULTS['horizon']),
                'resolution': resolution or DEFAULTS['resolution'], 'future': future,
                'exog': tuple(sorted((exog or {}).keys()))}
    if settings['horizon'] < 1 or not 0 < settings['interval'] < 1:
        raise ValueError('Horizon must be positive and the interval between 0 and 1.')
    rule, steps_per_year = RESOLUTIONS.get(settings['resolution'], (None, None))
    if rule is None:
        raise ValueError(f'Resolution must be one of {list(RESOLUTIONS)}.')
    #work in percent at the chosen resolution
    full = resample_series(pd.Series(target).dropna().sort_index() * 100, settings['resolution'])
    end = pd.Timestamp(train_end) if train_end is not None else full.index.max()
    begin = end - pd.Timedelta(days=round(365.25 * float(settings['history_years'])))
    train = full.loc[(full.index > begin) & (full.index <= end)]
    if len(train) < 2 * steps_per_year + 2:
        raise ValueError('At least two years of training data are needed.')
    exog_table = combine_exog(exog, settings['resolution'])
    x_train = pd.DataFrame(index=train.index)
    if not exog_table.empty:
        x_train = exog_table.reindex(train.index)
        #drop the start of the history where an exogenous source has no data yet
        complete = x_train.notna().all(axis=1)
        if complete.sum() < 2 * steps_per_year + 2:
            raise ValueError('The selected exogenous data cover less than two years of the training period.')
        first = complete.idxmax()
        train, x_train = train.loc[first:], x_train.loc[first:].ffill()
    future_index = pd.date_range(train.index[-1], periods=settings['horizon'] + 1, freq=rule)[1:]
    x_future = future_exog(exog_table, train, future_index, future)
    #one model for the forecast and one quantile model for each interval limit
    alpha = (1 - settings['interval']) / 2
    runs = {'forecast': None, 'lower': optim.losses.Quantile(alpha), 'upper': optim.losses.Quantile(1 - alpha)}
    predictions = {}
    for i, (name, loss) in enumerate(runs.items()):
        if progress:
            progress(i / len(runs), f'Training the {name} model ({settings["model"]})')
        model = _make_model(settings, steps_per_year, loss).fit(train, x_train)
        predictions[name] = model.predict(x_future, settings['horizon'])
    forecast = pd.DataFrame(predictions, index=future_index).clip(0, 100)
    #quantile models can cross; sort the three values so the band always contains the forecast
    forecast[['lower', 'forecast', 'upper']] = np.sort(forecast[['lower', 'forecast', 'upper']].to_numpy(), axis=1)
    if progress:
        progress(1., 'Forecast finished')
    actual = full.loc[full.index > train.index[-1]].reindex(future_index)
    return ForecastResult(history=train, forecast=forecast, actual=actual, settings=settings,
                          seconds=time.perf_counter() - started, exog_columns=list(x_train.columns))


def backtest(target, exog=None, origins=None, horizon=26, **settings):
    """forecast from several earlier training end dates and average the errors.

    origins are training end dates; by default twelve dates, 13 weeks apart,
    over the last three years with known outcome, so every season is used
    as a starting point three times. returns a dataframe with one row per origin and the
    average in the attrs['mean'] dictionary.
    """
    series = pd.Series(target).dropna()
    if origins is None:
        last = series.index.max() - pd.Timedelta(weeks=horizon)
        origins = pd.date_range(end=last, periods=12, freq='13W')
    rows = []
    for origin in origins:
        origin = series.index[series.index <= origin].max()
        result = forecast_filling(series, exog, train_end=origin, horizon=horizon, **settings)
        rows.append({'origin': origin.date(), 'seconds': result.seconds, **result.scores()})
    table = pd.DataFrame(rows)
    table.attrs['mean'] = table.drop(columns='origin').mean(numeric_only=True).to_dict()
    return table


def seasonal_naive(target, train_end, horizon=26):
    """reference forecast: the filling in the same week one year earlier (percent)."""
    series = pd.Series(target).dropna() * 100
    end = series.index[series.index <= pd.Timestamp(train_end)].max()
    future = pd.date_range(end, periods=horizon + 1, freq='W-SUN')[1:]
    previous = series.reindex(future - pd.Timedelta(weeks=52)).to_numpy()
    return pd.Series(previous, index=future)
