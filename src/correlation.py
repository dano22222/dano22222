"""sliding window correlation between weekly weather and reservoir statistics.

both series are weekly and use the nve weeks (ending on sunday, norwegian
calendar). a positive lag means that the weather leads: the weather in week
t - lag is compared with the reservoir value in week t. the correlation in
each window is the pearson correlation of the last `window` weeks.
"""
import numpy as np
import pandas as pd


def align_weekly(weather, reservoir):
    """put two weekly series on the same sunday based calendar (missing weeks stay nan)."""
    weather = pd.Series(weather, dtype=float).sort_index()
    reservoir = pd.Series(reservoir, dtype=float).sort_index()
    start = max(weather.first_valid_index(), reservoir.first_valid_index())
    end = min(weather.last_valid_index(), reservoir.last_valid_index())
    if start is None or end is None or start >= end:
        raise ValueError('The weather and reservoir series do not overlap in time.')
    index = pd.date_range(start, end, freq='W-SUN')
    return weather.reindex(index), reservoir.reindex(index)


def sliding_correlation(weather, reservoir, lag=0, window=26, min_fraction=.8):
    """rolling pearson correlation between lagged weather and a reservoir variable.

    lag and window are in weeks. a window needs at least min_fraction valid
    pairs, otherwise its correlation is nan (for example around missing weeks).
    returns a dataframe with the shifted weather, the reservoir variable and
    the rolling correlation, indexed by week.
    """
    if window < 4:
        raise ValueError('The window must be at least 4 weeks.')
    x, y = align_weekly(weather, reservoir)
    if abs(lag) >= len(x) - window:
        raise ValueError('The lag is too long for the selected period.')
    shifted = x.shift(int(lag))
    correlation = shifted.rolling(int(window), min_periods=max(3, int(window * min_fraction))).corr(y)
    #a constant window (for example no snow during summer) gives an undefined correlation
    correlation = correlation.replace([np.inf, -np.inf], np.nan)
    return pd.DataFrame({'weather': shifted, 'reservoir': y, 'correlation': correlation})


def lag_scan(weather, reservoir, lags=range(-26, 27)):
    """correlation over the whole period for each lag, to find the most informative delay."""
    x, y = align_weekly(weather, reservoir)
    values = {int(lag): x.shift(int(lag)).corr(y) for lag in lags}
    return pd.Series(values, name='correlation').rename_axis('lag_weeks')
