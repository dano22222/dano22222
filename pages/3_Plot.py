
import streamlit as st
import calendar
from nve_api import load_reservoir_data

# Page title
st.title("Reservoir Plot")
st.write("Explore Norwegian reservoir data from the NVE API.")

# Load and cache the API data
df = load_reservoir_data()

# Select the type of area
selected_type = st.radio(
    "Choose area type",
    ["EL", "NO", "VASS"],
    horizontal=True
)

# Filter the dataset by area type
type_df = df[df["area_type"] == selected_type]

# Select an area number
selected_area = st.selectbox(
    "Choose area",
    sorted(type_df["area"].unique())
)

area_df = type_df[
    type_df["area"] == selected_area
].copy()

# Select year
available_years = sorted(
    area_df["date"].dt.year.unique(),
    reverse=True
)

selected_year = st.selectbox(
    "Choose year",
    available_years
)

# Select months using a slider
selected_months = st.select_slider(
    "Choose months",
    options=list(range(1, 13)),
    value=(1, 1),
    format_func=lambda m: calendar.month_name[m]
)

start_month, end_month = selected_months

# Filter by year and selected months
filtered_df = area_df[
    (area_df["date"].dt.year == selected_year) &
    (area_df["date"].dt.month.between(
        start_month, end_month
    ))
].sort_values("date")



# Download only the observations selected by the user
if not filtered_df.empty:
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download selected reservoir data",
        data=csv_data,
        file_name=(
            f"reservoir_{selected_type}_{selected_area}_"
            f"{selected_year}_{start_month:02d}-{end_month:02d}.csv"
        ),
        mime="text/csv"
    )


# Select one variable or all variables
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

# Display the selected data
st.subheader(
    f"{selected_type} Area {selected_area} – {selected_year}"
)

if filtered_df.empty:
    st.info("No observations for the selected period.")
else:
    if selected_column == "All":
        # Separate plots keep variables with different units readable
        for column in numeric_columns:
            st.write(f"**{column}**")
            st.line_chart(
                filtered_df,
                x="date",
                y=column
            )
    else:
        st.line_chart(
            filtered_df,
            x="date",
            y=selected_column
        )

    st.caption(
        f"Showing {len(filtered_df)} observations "
        f"from the NVE API."
    )
