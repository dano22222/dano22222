"""Reusable Part 3 analyses. Inputs must be complete, regular time series."""
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
    """Reject silent interpolation, irregular spacing, duplicates and nonfinite data."""
    s = pd.Series(series).astype(float).sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise ValueError('A DatetimeIndex is required.')
    if len(s) < minimum or not np.isfinite(s).all() or s.index.has_duplicates:
        raise ValueError(f'Need at least {minimum} finite, unique observations.')
    steps = np.diff(s.index.asi8)
    if not np.all(steps == steps[0]) or steps[0] <= 0:
        raise ValueError('Observations must have regular time intervals.')
    return s


def style(ax, title, ylabel):
    ax.set(title=title, xlabel='Date (UTC for weather)', ylabel=ylabel)
    ax.grid(alpha=.2)
    ax.figure.autofmt_xdate()


def spc_analysis(series, cutoff_days=30., n_sigma=3.):
    """DCT-II high pass; median and Gaussian-consistent MAD over the entire input.

    Frequencies are k/(2*N*dt). Keep periods >= cutoff_days in the baseline.
    Plot baseline + residual median +/- n_sigma*MAD on the original scale.
    These are descriptive robust control limits, not calibrated rain probabilities.
    """
    s = clean_series(series)
    if cutoff_days <= 0 or not np.isfinite(cutoff_days) or n_sigma <= 0 or not np.isfinite(n_sigma):
        raise ValueError('Cutoff and sigma multiplier must be finite and positive.')
    dt_days = (s.index[1] - s.index[0]).total_seconds()/86400
    coefficients = dct(s.values, norm='ortho')
    frequencies = np.arange(len(s))/(2*len(s)*dt_days)
    coefficients[frequencies > 1/cutoff_days] = 0
    baseline = idct(coefficients, norm='ortho')
    residual = s.values - baseline
    centre = np.median(residual)
    scale = float(median_abs_deviation(residual, scale='normal'))
    #a zero robust scale is possible with sparse rain. do not substitute nonrobust std.
    tolerance = np.finfo(float).eps * max(1., float(np.max(np.abs(s)))) * 100
    if scale < tolerance:
        scale = 0.
    lower = baseline + centre - n_sigma*scale
    upper = baseline + centre + n_sigma*scale
    flags = (s.values < lower-tolerance) | (s.values > upper+tolerance)
    table = pd.DataFrame({'value':s, 'baseline':baseline, 'lower':lower,
                          'upper':upper, 'outlier':flags})
    fig, ax = plt.subplots(figsize=(12,4))
    ax.plot(s.index, s.values, lw=.7, label='Mean precipitation')
    ax.plot(s.index, lower, color='darkorange', lw=1, label='Robust SPC limits')
    ax.plot(s.index, upper, color='darkorange', lw=1)
    ax.scatter(s.index[flags], s.values[flags], c='crimson', s=12, label='Outlier', zorder=3)
    style(ax, 'Precipitation: DCT / robust SPC', 'Precipitation (mm per hour)')
    ax.legend(loc='upper right'); fig.tight_layout()
    return fig, table, {'observations':len(s), 'outliers':int(flags.sum()),
                        'fraction':float(flags.mean()), 'robust_sigma':scale,
                        'zero_scale':scale == 0}


def lof_analysis(series, contamination=.01, n_neighbors=48):
    """LOF on standardized [temperature, 1-hour change] to detect unusual states.

    The first change is set to zero; this boundary convention is explicit.
    LOF is descriptive: the requested fraction is a modelling assumption.
    """
    s = clean_series(series)
    if not 0 < contamination <= .5 or not 2 <= n_neighbors < len(s):
        raise ValueError('Use 0 < contamination <= .5 and 2 <= neighbors < N.')
    features = np.column_stack([s.values, s.diff().fillna(0).values])
    features = StandardScaler().fit_transform(features)
    model = LocalOutlierFactor(n_neighbors=int(n_neighbors), contamination=contamination)
    flags = model.fit_predict(features) == -1
    table = pd.DataFrame({'value':s, 'lof_score':-model.negative_outlier_factor_, 'outlier':flags})
    fig, ax = plt.subplots(figsize=(12,4))
    ax.plot(s.index, s.values, lw=.7, label='Mean temperature')
    ax.scatter(s.index[flags], s.values[flags], s=15, color='crimson', label='LOF anomaly', zorder=3)
    style(ax, 'Temperature: Local Outlier Factor', 'Temperature (°C)')
    ax.legend();fig.tight_layout()
    return fig, table, {'observations':len(s),'outliers':int(flags.sum()),'fraction':float(flags.mean())}


def stl_analysis(series, seasonal=13, trend=105, robust=True, period=52):
    """Annual seasonality approximated by 52 weekly samples; need >=2 cycles."""
    if period < 2 or seasonal < 3 or seasonal % 2 != 1 or trend <= period or trend % 2 != 1:
        raise ValueError('Seasonal must be odd >=3; trend odd > period; period >=2.')
    s = clean_series(series, minimum=2*period)
    result = STL(s, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()
    fig = result.plot();fig.set_size_inches(12,8)
    fig.axes[0].set_title('Reservoir filling: STL decomposition')
    fig.axes[0].set_ylabel('Fill fraction');fig.tight_layout()
    return fig, result


def spectrogram_analysis(series, window=156, overlap=130):
    """Hann-window power density, cycles/year; remove overall linear trend.

    Weekly sampling is assumed and checked. Resolution = 52/window cycles/year.
    """
    if not isinstance(window, (int,np.integer)) or not isinstance(overlap,(int,np.integer)):
        raise ValueError('Window and overlap must be integers.')
    if not 0 <= overlap < window or window < 8:
        raise ValueError('Need window >=8 and 0 <= overlap < window.')
    s = clean_series(series, minimum=window)
    step = (s.index[1]-s.index[0]).total_seconds()/86400
    if not np.isclose(step,7):
        raise ValueError('Spectrogram expects weekly data.')
    f,t,power = spectrogram(s.values, fs=52., window='hann', nperseg=window,
                            noverlap=overlap, detrend='linear', scaling='density')
    dates = s.index[0] + pd.to_timedelta(t*7*52,unit='D')
    fig, ax = plt.subplots(figsize=(12,4))
    mesh = ax.pcolormesh(dates, f, 10*np.log10(np.maximum(power,1e-15)), shading='auto', cmap='viridis')
    ax.set_ylim(0,6)
    style(ax,'Reservoir filling: spectrogram','Frequency (cycles per 52-week year)')
    fig.colorbar(mesh,ax=ax,label='Power density (dB, fraction² / cycles/year)')
    fig.tight_layout()
    return fig, {'frequency':f,'time_years':t,'power':power}
