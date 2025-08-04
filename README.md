# Extension Reports

**Open-source reporting tools for Cooperative Extension programs—automating map visualizations, analytics, and compliance-ready outputs for county and state reporting.**

This project enables Extension personnel, researchers, and developers to:
- Generate interactive HTML reports from CSV and GeoJSON inputs
- Visualize Gardening Helpline request counts by ZIP code
- Toggle between monthly and aggregate views on a single map
- Produce compliance-ready outputs suitable for Slack, Confluence, and GitHub workflows

## 🔍 Current Capability

The primary script, `create_report.py`, reads a ZIP-level CSV of monthly request data and a GeoJSON boundary file, then generates an interactive HTML map using **folium**. The map includes:

- Colored ZIP code polygons scaled to request volume
- Tooltip overlays showing ZIP code, name, and request count
- Centroid labels with numeric values
- A dynamic legend that updates when users toggle data layers

## 📂 Directory Layout

```
extension-reports/
├── data/                     # Input files (.csv, .geojson)
├── output/                   # Generated .html maps
├── create_report.py          # Main script (self-contained)
├── requirements.txt          # Minimal dependencies (generated via pipreqs)
├── README.md
```

## ▶️ Example Usage

```bash
python create_report.py \
  --csv data/helpline_summary.csv \
  --geojson data/wake_zipcodes.geojson \
  --output output/wake_gardening_map.html
```

- The CSV file should include ZIP codes as row indices and at least one column labeled `Aggregate`.
- The GeoJSON must include a `ZIPNUM` property matching the ZIP codes in the CSV.

## 📦 Dependencies

Install required packages in a virtual environment:

```bash
pip install -r requirements.txt
```

Dependencies are kept minimal and specific to this script:
- `pandas` for reading CSVs and handling tabular data
- `geopandas` for merging and manipulating geospatial ZIP boundaries
- `folium` for building interactive Leaflet maps
- `branca` for legends and HTML injection
- `shapely` for geometry operations like centroids

## ✅ Project Status

- **Active** — Maintained by [Server Science Incorporated](https://serverscience.com)
- This version is a standalone CLI prototype using only `create_report.py`
- Future versions will integrate modular utilities and support plugin-based rendering

## 📚 License

[GNU General Public License v3.0](LICENSE)

## 🤝 How to Contribute

We welcome bug reports, feedback, and suggestions via GitHub Issues. Development is coordinated through the Software Wrap initiative and aligns with Cooperative Extension needs.