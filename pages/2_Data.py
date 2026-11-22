"""data overview: reservoir statistics (sparkline overview and table) and norges bank exchange rates.

the former separate linechartcolumn view is kept here as the compact
overview tab, next to the detailed table and the exchange rates, so all
plain data views are collected on one page.
"""
import pandas as pd
import requests
import streamlit as st
from nve_api import load_reservoir_data
from src.ui import page_header, area_selector, area_label, show
from src.reservoir import filter_dates
from src import data
from src.plots import currency_figure

page_header('Explore', 'Data overview', 'Reservoir statistics from the NVE API and exchange rates from Norges Bank.')

#loading the reservoir data directly from nve (cached for one hour)
try:
    with st.spinner('Loading NVE reservoir statistics...'):
        df = load_reservoir_data()
except Exception as error:
    st.error(f'Could not load reservoir data from NVE: {error}')
    st.stop()

#shared geographical selection persists across all pages
selected_type, selected_area = area_selector(df)
type_df = df[df["area_type"] == selected_type].copy()

#numerical columns shown in the overview and their readable names
numeric_columns = ["fill_level", "capacity_TWh", "stored_energy_TWh", "fill_level_previous_week", "change_in_fill_level"]

overview_tab, table_tab, currency_tab = st.tabs(['Reservoir overview', 'Reservoir table', 'Exchange rates'])

with overview_tab:
    #the date interval applies to the overview and the table
    limits = (type_df.date.min().date(), type_df.date.max().date())
    date_interval = st.date_input("Date interval", value=limits, min_value=limits[0], max_value=limits[1])
    if len(date_interval) != 2:
        st.info("Choose both a start and an end date.")
        st.stop()
    type_df = filter_dates(type_df, *date_interval)
    if type_df.empty:
        st.info("No observations in this date interval.")
        st.stop()
    #one row per area number, each cell a small line chart of the variable over time
    summary_rows = []
    for area_number, area_data in type_df.groupby("area"):
        area_data = area_data.sort_values("date")
        row = {"Area": area_number}
        for column in numeric_columns:
            row[column] = area_data[column].dropna().tolist()
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows).sort_values("Area")
    st.subheader(f"{selected_type} areas")
    st.caption("Each row shows the development of the reservoir variables in the chosen interval for one area.")
    st.dataframe(summary_df,
                 column_config={column: st.column_config.LineChartColumn(column.replace("_", " ").title())
                                for column in numeric_columns},
                 hide_index=True, width='stretch')

with table_tab:
    #the rows behind the overview for the selected area
    filtered_df = type_df[type_df["area"] == selected_area].sort_values("date")
    st.subheader(area_label(selected_type, selected_area))
    st.dataframe(filtered_df, hide_index=True, width='stretch')
    #export exactly the area and interval currently visible
    st.download_button("Download selected data", filtered_df.to_csv(index=False).encode("utf-8"),
                       file_name=f"reservoir_{selected_type}_{selected_area}.csv", mime="text/csv")

with currency_tab:
    #local setting: the period of exchange rates only applies to this tab
    today = pd.Timestamp.now(tz='Europe/Oslo').date()
    period = st.date_input('Exchange rate period', value=(today - pd.Timedelta(days=365 * 3), today),
                           max_value=today, key='currency_period')
    if len(period) == 2:
        try:
            with st.spinner('Downloading exchange rates from Norges Bank...'):
                rates = data.exchange_rates(str(period[0]), str(period[1]))
            show(currency_figure(rates))
            latest = rates.dropna().iloc[-1]
            columns = st.columns(len(rates.columns))
            for column, currency in zip(columns, rates.columns):
                column.metric(f'NOK per {currency}', f'{latest[currency]:.4f}', help=f'Rate on {rates.dropna().index[-1]:%d.%m.%Y}')
            st.caption('Middle rates published by Norges Bank on Norwegian business days (dates in Oslo time).')
        except (requests.RequestException, ValueError) as error:
            st.warning(f'Norges Bank exchange rates are not available right now: {error}')
    else:
        st.info('Choose both a start and an end date.')
