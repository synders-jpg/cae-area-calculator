import streamlit as st
import math
import pandas as pd

# --- Functions ---
def dms_to_dd(d, m, s):
    """Converts Degrees, Minutes, Seconds to Decimal Degrees."""
    return d + (m / 60.0) + (s / 3600.0)

def dd_to_dms(dd):
    """Converts Decimal Degrees back to DMS for display."""
    abs_dd = abs(dd)
    d = int(abs_dd)
    m = int((abs_dd - d) * 60)
    s = (abs_dd - d - m/60) * 3600
    return f"{'-' if dd < 0 else ''}{d}° {m}' {s:.2f}\""

# --- 1. Configuration ---
st.set_page_config(page_title="Surveying Traverse Calculator", layout="wide")
st.sidebar.header("Traverse Settings")
sides = st.sidebar.selectbox("Number of Sides", [5, 6])

st.sidebar.subheader("Reference Azimuth")
st.sidebar.info("Enter the known Azimuth of the first side.")
az_d = st.sidebar.number_input("Azimuth Deg", value=98, step=1)
az_m = st.sidebar.number_input("Azimuth Min", value=17, step=1)
az_s = st.sidebar.number_input("Azimuth Sec", value=45.0, step=0.1)
start_az = dms_to_dd(az_d, az_m, az_s)

# --- 2. Input UI ---
st.title("Surveying Traverse & Area Calculator")
labels = ["A", "B", "C", "D", "E", "F"]
lengths = []
angles = []

st.markdown(f"### Input Data for {sides}-Sided Polygon")
for i in range(sides):
    with st.expander(f"Vertex {labels[i]} Data", expanded=True):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            next_idx = (i + 1) % sides
            l = st.number_input(f"Distance {labels[i]} to {labels[next_idx]}", min_value=0.01, value=500.0, key=f"l_{i}")
            lengths.append(l)
        st.write(f"**Interior Angle at {labels[i]}:**")
        with col2:
            d = st.number_input("Deg", min_value=0, max_value=360, value=108 if sides==5 else 120, key=f"d_{i}")
        with col3:
            m = st.number_input("Min", min_value=0, max_value=59, value=0, key=f"m_{i}")
        with col4:
            s = st.number_input("Sec", min_value=0.0, max_value=59.99, value=0.0, key=f"s_{i}")
        angles.append(dms_to_dd(d, m, s))

# --- 3. Calculation Logic ---
if st.button("Calculate Final Results", type="primary"):
    # A. Initial Azimuths, Latitudes, and Departures
    azimuths = []
    current_az = start_az
    for i in range(sides):
        azimuths.append(current_az)
        # Calculate next azimuth (Simplified for this example)
        # Note: In field work, you'd adjust angles first. 
        # Here we follow the provided Lat/Dep formulas.
        back_az = (current_az + 180) % 360
        current_az = (back_az + angles[(i+1)%sides]) % 360

    # Formulas: Latitude = Dist * cos(Az), Departure = Dist * sin(Az)
    raw_lats = [lengths[i] * math.cos(math.radians(azimuths[i])) for i in range(sides)]
    raw_deps = [lengths[i] * math.sin(math.radians(azimuths[i])) for i in range(sides)]
    
    perimeter = sum(lengths)
    closure_lat = sum(raw_lats)
    closure_dep = sum(raw_deps)

    # B. Compass Rule Adjustments
    # Formula: Correction = (Dist * Closure) / Perimeter
    adj_lats = []
    adj_deps = []
    for i in range(sides):
        lat_corr = (lengths[i] * closure_lat) / perimeter
        dep_corr = (lengths[i] * closure_dep) / perimeter
        # Corrected = Latitude - Correction (to zero out the error)
        adj_lats.append(raw_lats[i] - lat_corr)
        adj_deps.append(raw_deps[i] - dep_corr)

    # C. Adjusted Distances and Directions (Image 1)
    # Formula: Dist = sqrt(Lat^2 + Dep^2), Dir = atan(Dep/Lat)
    final_dists = []
    final_dirs = []
    for i in range(sides):
        d = math.sqrt(adj_lats[i]**2 + adj_deps[i]**2)
        direction_rad = math.atan2(adj_deps[i], adj_lats[i])
        direction_deg = math.degrees(direction_rad) % 360
        final_dists.append(d)
        final_dirs.append(direction_deg)

    # D. Coordinates (Starting at 0,0)
    # Formula: North_j = North_i + Latitude_ij
    norths, easts = [0.0], [0.0]
    for i in range(sides):
        norths.append(norths[-1] + adj_lats[i])
        easts.append(easts[-1] + adj_deps[i])

    # E. Area via "Down Left / Down Right Sums" (Image 2)
    # This is equivalent to the Shoelace formula
    down_right = sum(easts[i] * norths[i+1] for i in range(sides))
    down_left = sum(norths[i] * easts[i+1] for i in range(sides))
    
    area_sq_ft = abs(down_left - down_right) / 2
    area_acres = area_sq_ft / 43560

    # --- 4. Display Results ---
    st.divider()
    st.header("📊 Results")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Adjusted Area (sq ft)", f"{area_sq_ft:,.2f}")
    m2.metric("Area (Acres)", f"{area_acres:.4f}")
    m3.metric("Perimeter", f"{perimeter:,.2f}")

    # Adjustment Table
    st.subheader("Traverse Adjustment Table")
    data = {
        "Line": [f"{labels[i]}-{labels[(i+1)%sides]}" for i in range(sides)],
        "Raw Lat": raw_lats,
        "Raw Dep": raw_deps,
        "Adj Lat": adj_lats,
        "Adj Dep": adj_deps,
        "Final Dist": final_dists,
        "Final Azimuth": [dd_to_dms(d) for d in final_dirs]
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True)

    # Coordinate Table
    st.subheader("Coordinates")
    coord_data = pd.DataFrame({
        "Point": labels[:sides] + [f"{labels[0]} (Closed)"],
        "Northing (Y)": norths,
        "Easting (X)": easts
    })
    st.dataframe(coord_data, use_container_width=True)

    # Plot
    st.subheader("Traverse Map")
    chart_df = pd.DataFrame({"x": easts, "y": norths})
    st.line_chart(chart_df, x="x", y="y")
