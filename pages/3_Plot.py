"""reservoir plots: one variable (or all) for the selected area or several areas, as interactive plotly lines."""
import calendar
import plotly.express as px
import streamlit as st
from nve_api import load_reservoir_data
from src.ui import page_header, area_selector, show

page_header('Explore', 'Reservoir plots', 'Explore Norwegian reservoir data from the NVE API.')

#loading the reservoir data directly from nve
try:
    df = load_reservoir_data()
except Exception as error:
    st.error(f'Could not load reservoir data from NVE: {error}')
    st.stop()

#the same global area selection as the other pages
selected_type, shared_area = area_selector(df)
type_df = df[df["area_type"] == selected_type].copy()
available_areas = sorted(type_df["area"].unique().tolist())
compare = st.checkbox("Compare several areas", value=False)
comparison_areas = st.multiselect("Areas to compare", available_areas, default=available_areas) if compare else [shared_area]
if not comparison_areas:
    st.info("Select at least one area.")
    st.stop()
area_df = type_df[type_df.area.isin(comparison_areas)].copy()

#local settings: year and month interval only apply to this page
left, right, column_box = st.columns([1, 2, 1.4])
available_years = sorted(area_df["date"].dt.year.dropna().astype(int).unique(), reverse=True)
selected_year = left.selectbox("Choose year", available_years)
start_month, end_month = right.select_slider("Choose months", options=list(range(1, 13)), value=(1, 12),
                                             format_func=lambda m: calendar.month_name[m])

#use explicit units so variables remain interpretable in separate panels
axis_labels = {"fill_level": "Filling fraction", "capacity_TWh": "Capacity (TWh)",
               "stored_energy_TWh": "Stored energy (TWh)", "fill_level_previous_week": "Previous filling fraction",
               "change_in_fill_level": "Change in filling fraction"}
selected_column = column_box.selectbox("Choose column", list(axis_labels) + ["All"], format_func=lambda c: axis_labels.get(c, c))

#observations in the selected year and months
filtered_df = area_df[(area_df["date"].dt.year == selected_year) &
                      (area_df["date"].dt.month.between(start_month, end_month))].sort_values(["date", "area"]).copy()

if filtered_df.empty:
    st.info("No observations for the selected period.")
    st.stop()

filtered_df["Area"] = selected_type + " " + filtered_df["area"].astype(str)
columns_to_plot = list(axis_labels) if selected_column == "All" else [selected_column]
for column in columns_to_plot:
    #one line per area, hover shows the exact week and value
    fig = px.line(filtered_df, x="date", y=column, color="Area", markers=len(filtered_df) < 80,
                  labels={"date": "Week ending", column: axis_labels[column]},
                  title=f"{axis_labels[column]} | {selected_year}")
    fig.update_layout(height=340, hovermode="x unified")
    show(fig)

st.caption(f"Separate panels keep different units readable. Showing {len(filtered_df)} observations from the NVE API.")
area_name = "all" if compare else str(shared_area)
st.download_button("Download selected reservoir data", filtered_df.drop(columns="Area").to_csv(index=False).encode("utf-8"),
                   file_name=f"reservoir_{selected_type}_{area_name}_{selected_year}_{start_month:02d}-{end_month:02d}.csv",
                   mime="text/csv")
