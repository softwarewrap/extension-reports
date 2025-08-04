"""
create_report.py

Generates an interactive folium-based map visualizing Gardening Helpline request counts
per ZIP code, using a CSV of monthly request totals and a GeoJSON file of ZIP boundaries.

The output HTML map includes:
- Colored polygons for each ZIP code, scaled by request volume
- Labels showing exact request counts
- Radio-button controls to switch between aggregate and monthly views
- A dynamic legend that updates with the selected data layer

Usage (from command line):
    python create_report.py --csv data.csv --geojson zipcodes.geojson --output map.html

Dependencies:
    - pandas:     for structured CSV reading and data manipulation
    - geopandas:  for merging ZIP geometries and handling spatial joins
    - folium:     for building the interactive Leaflet.js-based map
    - branca:     for color scales and custom HTML/JS injection in folium
    - shapely:    for centroid and geometry operations on ZIP polygons
"""

import pandas as pd
import geopandas as gpd
import folium
from branca.colormap import linear
from shapely.geometry import Point
from branca.colormap import LinearColormap
import argparse


def create_report(csv_path: str, geojson_path: str, output_path: str) -> None:
    """
    Creates a ZIP-code-level folium map showing Gardening Helpline request volumes.

    Args:
        csv_path (str): Path to a CSV file containing request counts per ZIP code.
                        Expected structure: ZIP code index, columns for 'Aggregate', months, and optionally 'Unknown'.
        geojson_path (str): Path to a GeoJSON file with ZIP code polygons. Must include a 'ZIPNUM' property.
        output_path (str): Path to save the generated interactive HTML map.

    Returns:
        None. Writes a fully self-contained HTML map to the specified output path.
    """

    # ===========================
    # Load and preprocess data
    # ===========================
    df = pd.read_csv(csv_path, index_col=0)
    gdf = gpd.read_file(geojson_path)

    # Ensure ZIP code identifiers are strings for merging
    gdf["ZIPNUM"] = gdf["ZIPNUM"].astype(str)
    df.index = df.index.astype(str)

    # Compute "Aggregate" if not pre-computed in the CSV
    if "Aggregate" not in df.columns:
        months = [col for col in df.columns if col != "Unknown"]
        df["Aggregate"] = df[months].sum(axis=1)
    else:
        months = [col for col in df.columns if col not in ["Unknown", "Aggregate"]]

    # Map layers to generate
    data_layers = ["Aggregate"] + months

    # Exclude ZIP code "Unknown" when computing color scale maxima
    df_no_unknown = df.loc[~df.index.to_series().str.strip().eq("Unknown")]
    max_vals = {col: df_no_unknown[col].max() for col in data_layers}

    # ===========================
    # Colormap setup
    # ===========================
    def simulate_opacity(hex_color: str, alpha: float) -> str:
        """Blend white with a given hex color to simulate opacity on non-transparent elements."""
        from matplotlib.colors import to_rgb
        r, g, b = to_rgb(hex_color)
        r = int((1 - alpha) * 255 + alpha * r * 255)
        g = int((1 - alpha) * 255 + alpha * g * 255)
        b = int((1 - alpha) * 255 + alpha * b * 255)
        return f'rgb({r},{g},{b})'

    # Build colormaps
    colormaps = {}
    for col in data_layers:
        colormap = LinearColormap(
            colors=["#edf8fb", "#b3cde3", "#2b8cbe"],  # Light to medium blues
            vmin=1,
            vmax=max_vals[col]
        )
        colormap.caption = "Requests per ZIP Code"
        colormaps[col] = colormap

    # ===========================
    # Merge ZIP geometry with request data
    # ===========================
    merged = gdf.merge(df, how="left", left_on="ZIPNUM", right_index=True)
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            merged[col] = merged[col].fillna(0)  # Assume 0 requests where data is missing

    # Re-infer object types
    merged = merged.infer_objects(copy=False)  # Optional cleanup step

    # ===========================
    # Setup folium map
    # ===========================
    m = folium.Map(location=[35.8, -78.7], zoom_start=10, control_scale=True, name="map")
    folium.TileLayer("openstreetmap", control=False).add_to(m)

    # Compute centroids (in projected space, then convert back to match map CRS)
    projected = merged.to_crs(epsg=3857)
    merged["centroid"] = projected.centroid.to_crs(merged.crs)

    # For dynamic legend logic
    legend_id = "dynamic-legend"
    legend_js = ""

    # ===========================
    # Build each data layer (month or aggregate)
    # ===========================
    for layer_name in data_layers:
        group = folium.FeatureGroup(name=layer_name, show=(layer_name == "Aggregate"), overlay=False, control=True)

        # Add ZIP polygons
        for _, row in merged.iterrows():
            value = row[layer_name]
            zip_str = row["ZIPNUM"]
            is_zero = value == 0
            color = "white" if is_zero else colormaps[layer_name](value)

            folium.GeoJson(
                row.geometry,
                style_function=lambda _, color=color: {
                    "fillColor": color,
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.7,
                },
                tooltip=folium.Tooltip(
                    f"<b>Zip Code:</b> {zip_str}<br>"
                    f"<b>Zip Name:</b> {row.get('ZIPNAME', 'Unknown')}<br>"
                    f"<b>Requests:</b> {int(value)}"
                ),
                highlight_function=lambda _: {
                    "weight": 3,
                    "color": "black",
                    "fillColor": "rgba(255, 255, 180, 0.8)",  # Pale yellow highlight
                    "fillOpacity": 0.7
                },
                options={"pane": "shadowPane"}
            ).add_to(group)

        # Add label with request count at ZIP centroid
        for _, row in merged.iterrows():
            val = row[layer_name]
            x, y = row["centroid"].x, row["centroid"].y
            folium.map.Marker(
                [y, x],
                icon=folium.DivIcon(html=f"<div style='font-size:10pt;font-weight:bold'>{int(val)}</div>")
            ).add_to(group)

        group.add_to(m)

        # ===========================
        # Build dynamic legend HTML for this layer
        # ===========================
        unknown_count = int(df.loc["Unknown", layer_name]) if "Unknown" in df.index else 0

        legend_colormap = colormaps[layer_name]
        start_color = simulate_opacity(legend_colormap(1), 0.7)
        end_color = simulate_opacity(legend_colormap(max_vals[layer_name]), 0.7)

        svg_legend = f"""
        <div style='line-height:1.3'>
          <b>Requests per ZIP Code</b><br>
          <svg width="100%" height="20">
            <defs>
              <linearGradient id="grad_{layer_name}" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="{start_color}"/>
                <stop offset="100%" stop-color="{end_color}"/>
              </linearGradient>
            </defs>
            <rect width="100%" height="20" fill="url(#grad_{layer_name})"/>
          </svg>
          <div style="display:flex; justify-content:space-between">
            <span>1</span><span>{max_vals[layer_name]}</span>
          </div>
        </div>
        """.replace("\n", "")

        legend_js += f"""
        if (e.name === "{layer_name}") {{
          document.getElementById('{legend_id}').innerHTML = `{svg_legend}<div><b>Unknown ZIPs:</b> {unknown_count}</div>`;
        }}
        """

    # ===========================
    # Initial legend content and JS
    # ===========================
    initial_layer = "Aggregate"
    unknown_initial = int(df.loc["Unknown", initial_layer]) if "Unknown" in df.index else 0
    legend_colormap = getattr(linear, "Blues_09").scale(1, max_vals[initial_layer])
    start_color = simulate_opacity(legend_colormap(1), 0.7)
    end_color = simulate_opacity(legend_colormap(max_vals[initial_layer]), 0.7)

    init_legend = f"""
    <div style='line-height:1.3'>
      <b>Requests per ZIP Code</b><br>
      <svg width="100%" height="20">
        <defs>
          <linearGradient id="grad_{initial_layer}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="{start_color}"/>
            <stop offset="100%" stop-color="{end_color}"/>
          </linearGradient>
        </defs>
        <rect width="100%" height="20" fill="url(#grad_{initial_layer})"/>
      </svg>
      <div style="display:flex; justify-content:space-between">
        <span>1</span><span>{max_vals[initial_layer]}</span>
      </div>
    </div>
    """

    legend_html = f"""
    <div id="{legend_id}" style="position: fixed; bottom: 10px; right: 10px; z-index: 9999; background: white; padding: 10px; border:2px solid gray; border-radius: 4px;">
        {init_legend}
        <div><b>Unknown ZIPs:</b> {unknown_initial}</div>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    # ===========================
    # Layer control and legend interactivity
    # ===========================
    folium.LayerControl(collapsed=False).add_to(m)

    # Add JavaScript to support legend switching
    map_var = m.get_name()

    # Force legend to sync on load with initial layer
    js_script = f"""
    <script>
    window.onload = function() {{
      const map = {map_var};
      map.on('baselayerchange', function(e) {{
        {legend_js}
      }});
      const event = {{ name: "{initial_layer}" }};
      {legend_js.replace("e.name", "event.name")}
    }};
    </script>
    """

    m.get_root().html.add_child(folium.Element(js_script))

    m.save(output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an interactive folium map from ZIP-level request data.")
    parser.add_argument("--csv", required=True, help="Path to input CSV with ZIP code request data.")
    parser.add_argument("--geojson", required=True, help="Path to GeoJSON ZIP boundaries.")
    parser.add_argument("--output", required=True, help="Path to write the output HTML map.")
    args = parser.parse_args()

    create_report(args.csv, args.geojson, args.output)
