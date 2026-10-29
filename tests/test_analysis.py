"""scientific checks using known signals, injected anomalies and invalid inputs."""
import numpy as np
import pandas as pd
import pytest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.analysis import spc_analysis,lof_analysis,stl_analysis,spectrogram_analysis
from src.reservoir import filter_dates,weekly_series
from src.weather import expected_hours,validate_hourly,estimate_download

def hourly(values):return pd.Series(values,index=pd.date_range('2024-01-01',periods=len(values),freq='h',tz='UTC'))

def test_spc_injected_spike_and_original_scale():
    rng=np.random.default_rng(320);s=hourly(5+np.sin(np.arange(8784)*2*np.pi/8784)+rng.normal(0,.1,8784));s.iloc[4000]+=20
    fig,table,summary=spc_analysis(s)
    assert table.outlier.iloc[4000]
    assert np.allclose(table.value,s)
    assert np.allclose(table.upper-table.lower,6*summary['robust_sigma'])
    plt.close(fig)

def test_constant_spc():
    fig,table,summary=spc_analysis(hourly(np.ones(100)))
    assert summary['outliers']==0 and summary['zero_scale'];plt.close(fig)

def test_lof_injected_extreme():
    s=hourly(np.random.default_rng(1).normal(0,1,1000));s.iloc[500]=50
    fig,table,summary=lof_analysis(s)
    assert table.outlier.iloc[500] and 8<=summary['outliers']<=12;plt.close(fig)

def test_stl_reconstruction_and_recovered_season():
    t=np.arange(520);season=.2*np.sin(t*2*np.pi/52)
    s=pd.Series(.5+t*.0001+season,index=pd.date_range('2010-01-03',periods=len(t),freq='7D'))
    fig,r=stl_analysis(s)
    assert np.allclose(r.trend+r.seasonal+r.resid,s)
    assert np.corrcoef(r.seasonal,season)[0,1]>.99;plt.close(fig)

def test_spectrogram_annual_peak():
    t=np.arange(1040);s=pd.Series(np.sin(2*np.pi*t/52),index=pd.date_range('2000-01-02',periods=len(t),freq='7D'))
    fig,result=spectrogram_analysis(s)
    peak=result['frequency'][result['power'].mean(axis=1).argmax()]
    assert abs(peak-1)<.01;plt.close(fig)

@pytest.mark.parametrize('method,args',[(spc_analysis,{'cutoff_days':0}),(spc_analysis,{'n_sigma':-1}),(lof_analysis,{'contamination':0}),(lof_analysis,{'n_neighbors':1000}),(stl_analysis,{'seasonal':12}),(stl_analysis,{'trend':52}),(spectrogram_analysis,{'window':52,'overlap':52})])
def test_invalid_parameters(method,args):
    with pytest.raises(ValueError):method(hourly(np.arange(200)),**args)

@pytest.mark.parametrize('method',[spc_analysis,lof_analysis,stl_analysis,spectrogram_analysis])
def test_missing_and_irregular_rejected(method):
    s=hourly(np.arange(300,dtype=float));s.iloc[10]=np.nan
    with pytest.raises(ValueError):method(s)
    with pytest.raises(ValueError):method(hourly(np.arange(300)).drop(hourly(np.arange(300)).index[5]))

def test_inclusive_dates():
    df=pd.DataFrame({'date':pd.to_datetime(['2024-01-01','2024-01-02 12:00','2024-01-03'],format='mixed')})
    assert len(filter_dates(df,'2024-01-01','2024-01-02'))==2

def test_leap_year_and_estimate():
    assert len(expected_hours('2024-01-01','2024-12-31'))==8784
    assert estimate_download('2024-01-01','2024-12-31')['values']==17568000

def test_weather_validation():
    times=expected_hours('2024-01-01','2024-01-01');df=pd.DataFrame({'temperature_2m':0.,'precipitation':1.},index=times)
    validate_hourly(df,'2024-01-01','2024-01-01')
    with pytest.raises(ValueError):validate_hourly(df.iloc[:-1],'2024-01-01','2024-01-01')
    df.iloc[0,1]=-1
    with pytest.raises(ValueError):validate_hourly(df,'2024-01-01','2024-01-01')


@pytest.mark.parametrize('method,frequency',[(spc_analysis,'7D'),(lof_analysis,'7D'),(stl_analysis,'h'),(spectrogram_analysis,'h')])
def test_incorrect_time_units_rejected(method,frequency):
    series=pd.Series(np.arange(300,dtype=float),index=pd.date_range('2020-01-01',periods=300,freq=frequency))
    with pytest.raises(ValueError):method(series)
