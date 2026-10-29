
import streamlit as st
import calendar
from nve_api import load_reservoir_data

#page title
st.title("Reservoir Plot")
st.write("Explore Norwegian reservoir data from the NVE API.")

#loading the reservoir data directly from NVE
df = load_reservoir_data()

#selection of the geographical area type
selected_type = st.radio(
    "Choose area type",
    ["EL", "NO", "VASS"],
    horizontal=True
)

#filtering observations by area type
type_df = df[df["area_type"] == selected_type].copy()

#to allow users to compare all areas or select one area
available_areas = sorted(type_df["area"].unique().tolist())

selected_area = st.selectbox(
    "Choose area",
    ["All areas"] + available_areas,
    index=1
)

#filtering by area if a specific area is selected
if selected_area == "All areas":
    area_df = type_df.copy()
else:
    area_df = type_df[
        type_df["area"] == selected_area
    ].copy()

#selecting an available year
available_years = sorted(
    area_df["date"].dt.year.dropna().astype(int).unique(),
    reverse=True
)

selected_year = st.selectbox(
    "Choose year",
    available_years
)

#then selecting the month interval
selected_months = st.select_slider(
    "Choose months",
    options=list(range(1, 13)),
    value=(1, 1),
    format_func=lambda m: calendar.month_name[m]
)

start_month, end_month = selected_months

#to filter observations by both the selected year and months
filtered_df = area_df[
    (area_df["date"].dt.year == selected_year) &
    (area_df["date"].dt.month.between(
        start_month, end_month
    ))
].sort_values(["date", "area"]).copy()

#downloading only the selected observations
if not filtered_df.empty:
    csv_data = filtered_df.to_csv(
        index=False
    ).encode("utf-8")

    area_filename = (
        "all" if selected_area == "All areas"
        else str(selected_area)
    )

    st.download_button(
        label="Download selected reservoir data",
        data=csv_data,
        file_name=(
            f"reservoir_{selected_type}_{area_filename}_"
            f"{selected_year}_{start_month:02d}-{end_month:02d}.csv"
        ),
        mime="text/csv"
    )

#to select one or all numerical variables
numeric_columns = [
    "fill_level",
    "capacity_TWh",
    "stored_energy_TWh",
    "fill_level_previous_week",
    "change_in_fill_level"
]

selected_column = st.selectbox(
    "Choose column",
    ["All"] + numeric_columns
)

#displaying the selected data
area_label = (
    "All areas" if selected_area == "All areas"
    else f"Area {selected_area}"
)

st.subheader(
    f"{selected_type} {area_label} | {selected_year}"
)

if filtered_df.empty:
    st.info("No observations for the selected period.")

else:
    #to determine which variables to plot
    columns_to_plot = (
        numeric_columns
        if selected_column == "All"
        else [selected_column]
    )

    for column in columns_to_plot:

        if selected_column == "All":
            st.write(f"**{column}**")

        if selected_area == "All areas":
            #one single line for each area number
            plot_df = filtered_df.pivot_table(
                index="date",
                columns="area",
                values=column,
                aggfunc="mean"
            ).sort_index()

            #use of descriptive labels for the area lines
            plot_df.columns = [
                f"{selected_type} Area {area}"
                for area in plot_df.columns
            ]

            st.line_chart(plot_df)

        else:
            #showing the selected area's development over time
            st.line_chart(
                filtered_df,
                x="date",
                y=column
            )

    st.caption(
        f"Showing {len(filtered_df)} observations "
        f"from the NVE API."
    )
