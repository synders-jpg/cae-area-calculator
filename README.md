import streamlit as st
import math
import pandas as pd

# --- Functions ---
def dms_to_dd(d, m, s):
    """Converts Degrees, Minutes, Seconds to Decimal Degrees."""
    return d + (m / 60.0) + (s / 3600.0)

def dd_to_dms(dd):
    """Converts Decimal Degrees back to DMS for display."""
    d = int(dd)
    m = int((abs(dd) - abs(d)) * 60)
    s = (abs(dd) - abs(d) - m/60) * 3600
    return f"{d}° {m}' {s:.2f}\""

# --- 1. Configuration Sidebar ---
st.set_page_config(page_title="Surveying Traverse Calculator", layout="wide")
st.sidebar.header("Traverse Settings")
sides = st.sidebar.selectbox("Number of Sides", [5, 6])

st.sidebar.subheader("Reference Azimuth")
st.sidebar.info("Enter the known Azimuth of the LAST side (e.g., DE for a 5-sided polygon).")
az_d = st.sidebar.number_input("Azimuth Deg", value=98, step=1)
az_m = st.sidebar.number_input("Azimuth Min", value=17, step=1)
az_s = st.sidebar.number_input("Azimuth Sec", value=45.0, step=0.1)
start_az = dms_to_dd(az_d, az_m, az_s)

# --- 2. Input UI ---
st.title(" Surveying Traverse & Area Calculator")
st.markdown(f"### Input Data for {sides}-Sided Polygon")

labels = ["A", "B", "C", "D", "E", "F"]
lengths = []
angles = []

# Create a clean input grid
for i in range(sides):
    with st.expander(f"Vertex {labels[i]} Data", expanded=True):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            # Distance from current vertex to next
            next_idx = (i + 1) % sides
            l = st.number_input(f"Distance {labels[i]} ➔ {labels[next_idx]}", min_value=0.0, value=500.0, key=f"l_{i}")
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
    # 1. Angular Closure
    expected_sum = (sides - 2) * 180
    actual_sum = sum(angles)
    angular_error = actual_sum - expected_sum
    
    # 2. Compute Azimuths
    azimuths = []
    current_az = start_az
    for i in range(sides):
        back_az = (current_az + 180) % 360
        next_az = (back_az + angles[i]) % 360
        azimuths.append(next_az)
        current_az = next_az

    # 3. Latitudes and Departures
    lats = [lengths[i] * math.cos(math.radians(azimuths[i])) for i in range(sides)]
    deps = [lengths[i] * math.sin(math.radians(azimuths[i])) for i in range(sides)]
    
    # 4. Compass Rule Adjustment (Balancing)
    perim = sum(lengths)
    sum_lats, sum_deps = sum(lats), sum(deps)
    adj_lats = [lats[i] - (sum_lats * lengths[i] / perim) for i in range(sides)]
    adj_deps = [deps[i] - (sum_deps * lengths[i] / perim) for i in range(sides)]

    # 5. Coordinates (E = Origin)
    x, y = [0.0], [0.0]
    for i in range(sides):
        x.append(x[-1] + adj_deps[i])
        y.append(y[-1] + adj_lats[i])

    # 6. Area (Shoelace Formula)
    area_sq_units = 0.5 * abs(sum(x[i] * y[i+1] - x[i+1] * y[i] for i in range(sides)))

    # --- 4. Display Results ---
    st.divider()
    st.header("📊 Results")
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Adjusted Area", f"{area_sq_units:,.2f} sq units")
    res_col2.metric("Angular Error", f"{angular_error:.4f}°")
    res_col3.metric("Linear Misclosure", f"{math.sqrt(sum_lats**2 + sum_deps**2):.4f}")

    # Area conversions
    st.write(f"**Acres:** {area_sq_units / 43560:,.4f} | **Hectares:** {area_sq_units / 10000:,.4f}")

    # Data Table
    st.subheader("Coordinate List")
    coord_data = pd.DataFrame({
        "Point": labels[:sides] + [f"{labels[0]} (Closed)"],
        "X (Easting)": x,
        "Y (Northing)": y
    })
    st.dataframe(coord_data, use_container_width=True)

    # Visual Plot
    st.subheader("Traverse Map")
    chart_data = pd.DataFrame({"x": x, "y": y})
    st.line_chart(chart_data, x="x", y="y")
