"""interactive plotly figures for the streamlit app (they replace the matplotlib plots).

the functions only draw; all numbers come from src/analysis.py, src/forecast.py
and src/correlation.py, so the notebook and the app use the same results.
importing src.theme registers the common 'ind320' plotly template.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src import theme

OUTLIER = '#B5525C'


def spc_figure(table, label, title=None):
    """values, robust spc limits as a shaded band, and the flagged hours."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=table.index, y=table.lower, line=dict(width=0), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=table.index, y=table.upper, fill='tonexty', fillcolor='rgba(224,122,95,.18)',
                             line=dict(color=theme.ACCENT, width=1), name='Robust SPC limits'))
    fig.add_trace(go.Scatter(x=table.index, y=table.value, line=dict(color=theme.PRIMARY, width=1),
                             name='Regional mean'))
    flagged = table.loc[table.outlier]
    fig.add_trace(go.Scatter(x=flagged.index, y=flagged.value, mode='markers', name='Outlier',
                             marker=dict(color=OUTLIER, size=6)))
    fig.update_layout(title=title or f'{label.split(" (")[0]}: DCT high pass and robust SPC',
                      xaxis_title='Date (UTC)', yaxis_title=label, height=420)
    return fig


def satv_figure(table, label):
    """seasonally adjusted variations (high pass part) with the robust centre and limits."""
    centre = table.satv.median()
    spread = (table.upper - table.baseline - centre).iloc[0]
    fig = go.Figure(go.Scatter(x=table.index, y=table.satv, line=dict(color=theme.PRIMARY, width=1), name='SATV'))
    for value, name in [(centre + spread, 'Upper limit'), (centre - spread, 'Lower limit')]:
        fig.add_hline(y=value, line=dict(color=theme.ACCENT, dash='dash'), annotation_text=name)
    flagged = table.loc[table.outlier]
    fig.add_trace(go.Scatter(x=flagged.index, y=flagged.satv, mode='markers', name='Outlier',
                             marker=dict(color=OUTLIER, size=6)))
    fig.update_layout(title='Seasonally adjusted variations (SATV)', xaxis_title='Date (UTC)',
                      yaxis_title=f'Deviation from baseline ({label.split("(")[-1]}', height=320)
    return fig


def lof_figure(table, label):
    """hourly values with the local outlier factor anomalies highlighted."""
    fig = go.Figure(go.Scatter(x=table.index, y=table.value, line=dict(color=theme.PRIMARY, width=1),
                               name='Regional mean'))
    flagged = table.loc[table.outlier]
    fig.add_trace(go.Scatter(x=flagged.index, y=flagged.value, mode='markers', name='LOF anomaly',
                             marker=dict(color=OUTLIER, size=7),
                             customdata=flagged.lof_score, hovertemplate='%{x}<br>%{y:.2f}<br>LOF score %{customdata:.2f}'))
    fig.update_layout(title=f'{label.split(" (")[0]}: Local Outlier Factor', xaxis_title='Date (UTC)',
                      yaxis_title=label, height=420)
    return fig


def stl_figure(result):
    """observed, trend, seasonal and residual parts in four linked panels."""
    parts = [('Observed', result.observed), ('Trend', result.trend),
             ('Seasonal', result.seasonal), ('Residual', result.resid)]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=.04,
                        subplot_titles=[name for name, _ in parts])
    for i, (name, values) in enumerate(parts, start=1):
        mode = 'markers' if name == 'Residual' else 'lines'
        fig.add_trace(go.Scatter(x=values.index, y=values.values, mode=mode, name=name,
                                 marker=dict(size=3, color=theme.COLORWAY[i - 1]),
                                 line=dict(color=theme.COLORWAY[i - 1], width=1.4)), row=i, col=1)
    fig.update_layout(title='Reservoir filling: STL decomposition', height=720, showlegend=False)
    fig.update_yaxes(title_text='Fill fraction', row=1, col=1)
    return fig


def spectrogram_figure(spectrum):
    """power density in db over time (window centres) and frequency (cycles per year)."""
    keep = spectrum['frequency'] <= 6
    power = 10 * np.log10(np.maximum(spectrum['power'][keep], 1e-15))
    fig = go.Figure(go.Heatmap(x=spectrum['dates'], y=spectrum['frequency'][keep], z=power,
                               colorscale='Viridis', colorbar=dict(title='dB')))
    fig.update_layout(title='Reservoir filling: spectrogram', xaxis_title='Window centre',
                      yaxis_title='Frequency (cycles per 52-week year)', height=420)
    return fig


def correlation_figure(frame, weather_label, reservoir_label, lag, window):
    """both series on top (standardized so they share one axis) and the rolling correlation below."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.08, row_heights=[.55, .45],
                        subplot_titles=['Standardized series', f'Rolling correlation ({window}-week window)'])
    for column, label, color in [('weather', f'{weather_label} (lag {lag} w)', theme.ACCENT),
                                 ('reservoir', reservoir_label, theme.PRIMARY)]:
        values = frame[column]
        fig.add_trace(go.Scatter(x=frame.index, y=(values - values.mean()) / values.std(), name=label,
                                 line=dict(color=color, width=1.3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=frame.index, y=frame.correlation, name='Correlation', fill='tozeroy',
                             line=dict(color='#6C5B7B', width=1.5), fillcolor='rgba(108,91,123,.15)'), row=2, col=1)
    fig.update_yaxes(range=[-1, 1], title_text='Pearson r', row=2, col=1)
    fig.update_yaxes(title_text='z score', row=1, col=1)
    fig.update_layout(height=620, hovermode='x unified')
    return fig


def lag_scan_figure(scan, selected_lag):
    """overall correlation for each lag, with the selected lag highlighted."""
    colors = [theme.ACCENT if lag == selected_lag else theme.PRIMARY for lag in scan.index]
    fig = go.Figure(go.Bar(x=scan.index, y=scan.values, marker_color=colors))
    fig.update_layout(title='Correlation over the whole period for each lag', xaxis_title='Lag (weeks, weather leads)',
                      yaxis_title='Pearson r', height=300)
    return fig


def forecast_figure(result, title, animate=True, history_weeks=156):
    """history, forecast with prediction interval and (if known) the true values.

    with animate=True the forecast is revealed one period at a time by plotly
    animation frames (play button), which shows how the dynamic forecast is
    built step by step from its own earlier predictions.
    """
    history = result.history.iloc[-history_weeks:]
    forecast, actual = result.forecast, result.actual.dropna()
    level = int(round(result.settings['interval'] * 100))
    #the forecast line starts at the last training value so there is no gap
    start = pd.DataFrame({'forecast': history.iloc[-1], 'lower': history.iloc[-1], 'upper': history.iloc[-1]},
                         index=[history.index[-1]])
    path = pd.concat([start, forecast])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history.index, y=history.values, name='Training data', line=dict(color=theme.TEXT, width=1.4)))
    fig.add_trace(go.Scatter(x=actual.index, y=actual.values, name='Observed', mode='lines+markers',
                             line=dict(color='#3D9970', width=1.4, dash='dot'), marker=dict(size=4)))
    first = path.iloc[:1] if animate else path
    fig.add_trace(go.Scatter(x=first.index, y=first.lower, line=dict(width=0), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=first.index, y=first.upper, fill='tonexty', fillcolor='rgba(31,111,139,.18)',
                             line=dict(width=0), name=f'{level}% interval (quantile loss)'))
    fig.add_trace(go.Scatter(x=first.index, y=first.forecast, name='Forecast', line=dict(color=theme.ACCENT, width=2.5)))
    fig.update_layout(title=title, xaxis_title='Week', yaxis_title='Filling (%)', height=480,
                      yaxis=dict(range=[0, 100]), hovermode='x unified')
    if animate:
        frames = [go.Frame(name=str(k), traces=[2, 3, 4],
                           data=[go.Scatter(x=path.index[:k + 1], y=path.lower[:k + 1]),
                                 go.Scatter(x=path.index[:k + 1], y=path.upper[:k + 1]),
                                 go.Scatter(x=path.index[:k + 1], y=path.forecast[:k + 1])])
                  for k in range(1, len(path))]
        fig.frames = frames
        #fix the x axis so it does not jump while the animation runs
        right = max(path.index[-1], actual.index.max() if len(actual) else path.index[-1])
        fig.update_xaxes(range=[history.index[0], right + pd.Timedelta(weeks=2)])
        play = dict(label='▶ Play', method='animate',
                    args=[None, dict(frame=dict(duration=90, redraw=False), fromcurrent=True, transition=dict(duration=0))])
        pause = dict(label='❚❚ Pause', method='animate',
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode='immediate')])
        fig.update_layout(updatemenus=[dict(type='buttons', direction='left', x=0, y=-.18, xanchor='left',
                                            buttons=[play, pause], showactive=False)],
                          sliders=[dict(active=0, x=.18, len=.82, y=-.12, currentvalue=dict(prefix='Step: '),
                                        steps=[dict(label=str(k), method='animate',
                                                    args=[[str(k)], dict(mode='immediate', frame=dict(duration=0, redraw=False))])
                                               for k in range(1, len(path))])],
                          margin=dict(b=110))
    return fig


def currency_figure(rates):
    """daily nok exchange rates, one line per currency."""
    fig = go.Figure()
    for column in rates.columns:
        fig.add_trace(go.Scatter(x=rates.index, y=rates[column], name=f'NOK per {column}', line=dict(width=1.5)))
    fig.update_layout(title='Norges Bank exchange rates', xaxis_title='Date (Oslo business days)',
                      yaxis_title='NOK', height=380, hovermode='x unified')
    return fig
