"""reusable part 3 analyses, shared by the notebook and the streamlit app.

every function takes a pandas series with a regular DatetimeIndex and
returns a matplotlib figure plus the numbers behind it:
  spc_analysis          precipitation outliers (dct high pass + robust spc limits)
  lof_analysis          temperature anomalies (local outlier factor)
  stl_analysis          seasonal trend decomposition of reservoir filling
  spectrogram_analysis  time resolved frequency content of reservoir filling
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import STL


def clean_series(series, minimum=8):
    """check that a series is long enough, finite, unique and regularly spaced.

    gaps are rejected instead of interpolated, so no analysis runs on
    silently invented values.
    """
    s = pd.Series(series).astype(float).sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise ValueError('A DatetimeIndex is required.')
    if len(s) < minimum or not np.isfinite(s).all() or s.index.has_duplicates:
        raise ValueError(f'Need at least {minimum} finite, unique observations.')
    #all time steps must be equal (hourly weather or weekly reservoir data)
    steps = np.diff(s.index.asi8)
    if not np.all(steps == steps[0]) or steps[0] <= 0:
        raise ValueError('Observations must have regular time intervals.')
    return s


def style(ax, title, ylabel, xlabel='Date'):
    """common title, axis labels and grid for all analysis plots."""
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(alpha=.2)
    ax.figure.autofmt_xdate()


def spc_analysis(series, cutoff_days=30., n_sigma=3.):
    """precipitation outliers from statistical process control on dct high pass values.

    steps:
      1. dct ii of the hourly series. coefficient k has frequency k/(2*n*dt).
      2. low pass: keep only frequencies up to 1/cutoff_days (periods of at
         least cutoff_days); the inverse dct gives a smooth seasonal baseline.
      3. high pass = original minus baseline. these are the seasonally
         adjusted variations (satv). they are used, but not plotted.
      4. robust statistics over the whole year: median and mad (scaled to
         match the standard deviation of a normal distribution).
      5. spc limits = baseline + median +/- n_sigma * mad, i.e. on the original scale.
    returns the figure, a table with value, baseline, limits and outlier
    flag per hour, and a summary dictionary.
    """
    s = clean_series(series)
    if s.index[1] - s.index[0] != pd.Timedelta(hours=1):
        raise ValueError("spc expects hourly precipitation observations.")
    if cutoff_days <= 0 or not np.isfinite(cutoff_days) or n_sigma <= 0 or not np.isfinite(n_sigma):
        raise ValueError('Cutoff and sigma multiplier must be finite and positive.')
    #time step in days (1/24 for hourly data) and the frequency of each dct coefficient
    dt_days = (s.index[1] - s.index[0]).total_seconds() / 86400
    coefficients = dct(s.values, norm='ortho')
    frequencies = np.arange(len(s)) / (2 * len(s) * dt_days)
    #remove the fast components; what is left is the slowly varying baseline
    coefficients[frequencies > 1 / cutoff_days] = 0
    baseline = idct(coefficients, norm='ortho')
    #satv: the high pass part of the precipitation
    satv = s.values - baseline
    centre = np.median(satv)
    scale = float(median_abs_deviation(satv, scale='normal'))
    #with very dry periods the mad can be zero; then limits collapse onto the baseline
    tolerance = np.finfo(float).eps * max(1., float(np.max(np.abs(s)))) * 100
    if scale < tolerance:
        scale = 0.
    lower = baseline + centre - n_sigma * scale
    upper = baseline + centre + n_sigma * scale
    flags = (s.values < lower - tolerance) | (s.values > upper + tolerance)
    table = pd.DataFrame({'value': s, 'baseline': baseline, 'lower': lower,
                          'upper': upper, 'outlier': flags})
    #plot the original precipitation, the two limit curves and the outliers in red
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s.index, s.values, lw=.7, label='Mean precipitation')
    ax.plot(s.index, lower, color='darkorange', lw=1, label='Robust SPC limits')
    ax.plot(s.index, upper, color='darkorange', lw=1)
    ax.scatter(s.index[flags], s.values[flags], c='crimson', s=12, label='Outlier', zorder=3)
    style(ax, 'Precipitation: DCT / robust SPC', 'Precipitation (mm per hour)', 'Date (UTC)')
    ax.legend(loc='upper right')
    fig.tight_layout()
    summary = {'observations': len(s), 'outliers': int(flags.sum()), 'fraction': float(flags.mean()),
               'robust_sigma': scale, 'zero_scale': scale == 0}
    return fig, table, summary


def lof_analysis(series, contamination=.01, n_neighbors=48):
    """temperature anomalies with the local outlier factor.

    each hour is described by two standardized features: the temperature and
    its change since the previous hour (set to zero for the first hour).
    lof compares how dense the neighbourhood of each hour is with the density
    around its n_neighbors nearest neighbours; the contamination share with
    the lowest relative density is flagged. contamination is an assumption,
    so flagged hours are unusual, not necessarily wrong.
    """
    s = clean_series(series)
    if s.index[1] - s.index[0] != pd.Timedelta(hours=1):
        raise ValueError("lof expects hourly temperature observations.")
    if not 0 < contamination <= .5 or not 2 <= n_neighbors < len(s):
        raise ValueError('Use 0 < contamination <= .5 and 2 <= neighbors < N.')
    features = np.column_stack([s.values, s.diff().fillna(0).values])
    #standardize so temperature and hourly change get equal weight in the distances
    features = StandardScaler().fit_transform(features)
    model = LocalOutlierFactor(n_neighbors=int(n_neighbors), contamination=contamination)
    flags = model.fit_predict(features) == -1
    #a score above 1 means lower density than the neighbours
    table = pd.DataFrame({'value': s, 'lof_score': -model.negative_outlier_factor_, 'outlier': flags})
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s.index, s.values, lw=.7, label='Mean temperature')
    ax.scatter(s.index[flags], s.values[flags], s=15, color='crimson', label='LOF anomaly', zorder=3)
    style(ax, 'Temperature: Local Outlier Factor', 'Temperature (°C)', 'Date (UTC)')
    ax.legend()
    fig.tight_layout()
    summary = {'observations': len(s), 'outliers': int(flags.sum()), 'fraction': float(flags.mean())}
    return fig, table, summary


def stl_analysis(series, seasonal=13, trend=105, robust=True, period=52):
    """stl decomposition of a weekly series: observed = trend + seasonal + residual.

    period=52 weeks approximates one year. seasonal and trend are the loess
    window lengths (odd numbers of weeks); trend must be longer than one
    period. robust=True downweights unusual weeks when fitting.
    """
    if period < 2 or seasonal < 3 or seasonal % 2 != 1 or trend <= period or trend % 2 != 1:
        raise ValueError('Seasonal must be odd >=3; trend odd > period; period >=2.')
    #at least two full years are needed to separate season from trend
    s = clean_series(series, minimum=2 * period)
    if s.index[1] - s.index[0] != pd.Timedelta(days=7):
        raise ValueError("stl expects weekly reservoir observations.")
    result = STL(s, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()
    fig = result.plot()
    fig.set_size_inches(12, 8)
    fig.axes[0].set_title('Reservoir filling: STL decomposition')
    fig.axes[0].set_ylabel('Fill fraction')
    fig.axes[-1].set_xlabel('Date')
    fig.tight_layout()
    return fig, result


def spectrogram_analysis(series, window=156, overlap=130):
    """spectrogram of a weekly series with frequencies in cycles per year.

    window is the number of weeks in each hann window and overlap the number
    of weeks shared by neighbouring windows. each window is linearly
    detrended. the frequency resolution is 52/window cycles per year, so
    longer windows separate frequencies better but blur changes over time.
    """
    if not isinstance(window, (int, np.integer)) or not isinstance(overlap, (int, np.integer)):
        raise ValueError('Window and overlap must be integers.')
    if not 0 <= overlap < window or window < 8:
        raise ValueError('Need window >=8 and 0 <= overlap < window.')
    s = clean_series(series, minimum=window)
    step = (s.index[1] - s.index[0]).total_seconds() / 86400
    if not np.isclose(step, 7):
        raise ValueError('Spectrogram expects weekly data.')
    #fs=52 samples per year gives frequencies in cycles per year and times in years
    f, t, power = spectrogram(s.values, fs=52., window='hann', nperseg=window,
                              noverlap=overlap, detrend='linear', scaling='density')
    #convert window centres from years after the first week into dates
    dates = s.index[0] + pd.to_timedelta(t * 7 * 52, unit='D')
    fig, ax = plt.subplots(figsize=(12, 4))
    #log scale (db) so weak components are visible; the floor avoids log(0)
    mesh = ax.pcolormesh(dates, f, 10 * np.log10(np.maximum(power, 1e-15)), shading='auto', cmap='viridis')
    ax.set_ylim(0, 6)
    style(ax, 'Reservoir filling: spectrogram', 'Frequency (cycles per 52-week year)')
    fig.colorbar(mesh, ax=ax, label='Power density (dB, fraction² / cycles/year)')
    fig.tight_layout()
    return fig, {'frequency': f, 'time_years': t, 'power': power}
