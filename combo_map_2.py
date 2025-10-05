import json
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table, Input, Output

# Paths to data files
CSV_PATH = "Crime_Data_from_2020_to_Present.csv"
DIVISIONS_GEOJSON = "LAPD_Division_5922489107755548254.geojson"

# Map settings
CENTER = dict(lat=34.05, lon=-118.25)
ZOOM = 9
HEIGHT = 650

# Keywords that flag a crime as violent
VIOLENT_KEYS = [
    "ASSAULT", "ROBBERY", "HOMICIDE", "MANSLAUGHTER",
    "RAPE", "SEXUAL", "PENETRATION", "ORAL COPULATION",
    "SODOMY", "BRANDISH WEAPON", "SHOTS FIRED"
]

def is_violent(desc: str) -> int:
    # Return 1 if the description contains any violent keyword, else 0
    if not isinstance(desc, str):
        return 0
    u = str(desc).upper()
    return int(any(k in u for k in VIOLENT_KEYS))

def parse_occ_datetime(series: pd.Series) -> pd.Series:
    # Try parsing various date formats; fallback if parsing fails
    dt = pd.to_datetime(series, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if dt.isna().all():
        dt = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    miss = dt.isna()
    if miss.any():
        dt.loc[miss] = pd.to_datetime(series.loc[miss], errors="coerce")
    return dt

# Load and clean data
df_raw = pd.read_csv(CSV_PATH, low_memory=False)

# Keep only Part 1 crimes (serious offenses)
if "Part 1-2" in df_raw.columns:
    try:
        df_raw = df_raw[df_raw["Part 1-2"].astype(float) == 1.0]
    except Exception:
        df_raw = df_raw[df_raw["Part 1-2"] == 1]

# Remove invalid coordinates
if "LAT" in df_raw.columns and "LON" in df_raw.columns:
    df_raw = df_raw[(df_raw["LAT"].notna()) & (df_raw["LON"].notna())]
    df_raw = df_raw[(df_raw["LAT"] != 0) & (df_raw["LON"] != 0)]

# Parse occurrence date and extract year
if "DATE OCC" in df_raw.columns:
    df_raw["OCC_DT"] = parse_occ_datetime(df_raw["DATE OCC"])
    df_raw = df_raw.dropna(subset=["OCC_DT"])
    df_raw["Year"] = df_raw["OCC_DT"].dt.year
else:
    df_raw["Year"] = pd.NA

# Normalize area names
if "AREA NAME" not in df_raw.columns:
    df_raw["AREA NAME"] = df_raw.get("AREA", "").astype(str)
df_raw["AREA NAME"] = df_raw["AREA NAME"].astype(str).str.strip().str.upper()

# Mark whether a crime is violent
df_raw["Violent"] = df_raw["Crm Cd Desc"].apply(is_violent).astype(int)

# Focus only on years 2020â2024
df_raw = df_raw[df_raw["Year"].isin([2020, 2021, 2022, 2023, 2024])]

# Load LAPD division boundaries and prep names
with open(DIVISIONS_GEOJSON, "r") as f:
    gj = json.load(f)
for ft in gj["features"]:
    name_raw = str(ft["properties"].get("APREC", ""))
    ft["properties"]["APREC_UP"] = name_raw.strip().upper()

ALL_DIVISIONS = [f["properties"]["APREC_UP"] for f in gj["features"]]

# Aggregate stats
# By year and area
agg_year_area = (
    df_raw.groupby(["Year", "AREA NAME"])
          .agg(total=("Crm Cd Desc", "count"),
               violent=("Violent", "sum"))
          .reset_index()
          .rename(columns={"AREA NAME": "APREC"})
)
agg_year_area["violent_ratio"] = agg_year_area["violent"] / agg_year_area["total"]

# Citywide totals by year
agg_year_city = (
    df_raw.groupby(["Year", "Crm Cd Desc"])
          .size()
          .reset_index(name="count")
)

# Across all years by division
agg_all_area = (
    df_raw.groupby(["AREA NAME"])
          .agg(total=("Crm Cd Desc", "count"),
               violent=("Violent", "sum"))
          .reset_index()
          .rename(columns={"AREA NAME": "APREC"})
)
agg_all_area["violent_ratio"] = agg_all_area["violent"] / agg_all_area["total"]

# Citywide totals across all years
agg_all_city = (
    df_raw.groupby(["Crm Cd Desc"])
          .size()
          .reset_index(name="count")
)

def ensure_all_divisions(df_area: pd.DataFrame) -> pd.DataFrame:
    # Make sure every division is listed even if count is zero
    base = pd.DataFrame({"APREC": ALL_DIVISIONS})
    out = base.merge(df_area, on="APREC", how="left")
    for col in ["total", "violent", "violent_ratio"]:
        if col in out.columns:
            out[col] = out[col].fillna(0)
    return out

agg_all_area = ensure_all_divisions(agg_all_area)

# Add missing divisions per year
full_list = []
for year in [2020, 2021, 2022, 2023, 2024]:
    dfy = agg_year_area[agg_year_area["Year"] == year][["APREC","total","violent","violent_ratio"]].copy()
    dfy["Year"] = year
    dfy = ensure_all_divisions(dfy)
    full_list.append(dfy)
agg_year_area_full = pd.concat(full_list, ignore_index=True)

# Dropdown options
AVAILABLE_OPTIONS = [{"label": "All (2020â2024)", "value": "ALL"}] + \
                    [{"label": str(y), "value": y} for y in [2020, 2021, 2022, 2023, 2024]]

def build_map(df_area: pd.DataFrame):
    # Build a choropleth map showing violent crime ratio by division
    fig = px.choropleth_map(
        df_area,
        geojson=gj,
        featureidkey="properties.APREC_UP",
        locations="APREC",
        color="violent_ratio",
        color_continuous_scale="Reds",
        center=CENTER,
        zoom=ZOOM,
        height=HEIGHT,
    )
    fig.update_traces(
        marker_opacity=0.45,
        marker_line_width=1.5,
        marker_line_color="black",
        hovertemplate="<b>%{location}</b><br>Violent Ratio: %{z:.2%}<extra></extra>",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig

# Dash App setup
app = Dash(__name__)

DEFAULT_SELECTION = "ALL"  # Start with all years combined

# Initialize map and title
if DEFAULT_SELECTION == "ALL":
    df_area_init = agg_all_area.copy()
    initial_map = build_map(df_area_init)
    initial_title = "Citywide Crime Ranking (All 2020â2024)"
else:
    df_area_init = agg_year_area_full[agg_year_area_full["Year"] == DEFAULT_SELECTION][["APREC","total","violent","violent_ratio"]]
    initial_map = build_map(df_area_init)
    initial_title = f"Citywide Crime Ranking ({DEFAULT_SELECTION})"

# Layout
app.layout = html.Div([
    html.H2("Los Angeles - Violent Crime Ratio by Division"),

    html.Div([
        html.Label("Select Year:", style={"fontWeight": "bold", "marginRight": "10px"}),
        dcc.Dropdown(
            id="year-dropdown",
            options=AVAILABLE_OPTIONS,
            value=DEFAULT_SELECTION,
            clearable=False,
            style={"width": "220px"}
        ),
    ], style={"marginBottom": "12px"}),

    html.Div([
        # Left: Table
        html.Div([
            html.H4(id="ranking-title", children=initial_title, style={"textAlign": "center", "marginBottom": "10px"}),
            dash_table.DataTable(
                id="crime-ranking-table",
                columns=[
                    {"name": "Crime Type", "id": "Crm Cd Desc"},
                    {"name": "Count", "id": "count"},
                    {"name": "Category", "id": "Category"},
                ],
                style_table={'overflowY': 'auto', 'height': '650px', 'width': '400px'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '8px',
                    'fontSize': '14px',
                    'whiteSpace': 'normal',
                },
                style_header={
                    'fontWeight': 'bold',
                    'backgroundColor': '#f2f2f2'
                },
                page_size=20,
                data=[]
            )
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),

        # Right: Map
        dcc.Graph(id="crime-map", figure=initial_map, style={"width": "68%", "display": "inline-block"})
    ])
])

# Callbacks
@app.callback(
    Output("crime-map", "figure"),
    Input("year-dropdown", "value")
)
def update_map(selected):
    # Rebuild map when year changes
    if selected == "ALL":
        df_area = agg_all_area.copy()
    else:
        df_area = agg_year_area_full[agg_year_area_full["Year"] == selected][["APREC","total","violent","violent_ratio"]]
    return build_map(df_area)

@app.callback(
    [Output("crime-ranking-table", "data"),
     Output("ranking-title", "children")],
    [Input("crime-map", "clickData"),
     Input("year-dropdown", "value")]
)
def update_table(clickData, selected):
    # Update table and title when year or map selection changes
    if selected == "ALL":
        if clickData and "points" in clickData and clickData["points"]:
            # When a division is clicked, show its top crimes
            area = clickData["points"][0].get("location")
            rank = (df_raw[df_raw["AREA NAME"] == area]
                    .groupby("Crm Cd Desc")
                    .size()
                    .reset_index(name="count")
                    .sort_values("count", ascending=False))
            title = f"Crime Ranking in {area} (All 2020â2024)"
        else:
            # Otherwise show citywide totals
            rank = agg_all_city.sort_values("count", ascending=False).copy()
            title = "Citywide Crime Ranking (All 2020â2024)"
    else:
        if clickData and "points" in clickData and clickData["points"]:
            area = clickData["points"][0].get("location")
            year_mask = df_raw["Year"] == selected
            rank = (df_raw[year_mask & (df_raw["AREA NAME"] == area)]
                    .groupby("Crm Cd Desc")
                    .size()
                    .reset_index(name="count")
                    .sort_values("count", ascending=False))
            title = f"Crime Ranking in {area} ({selected})"
        else:
            # If no area clicked, show citywide ranking for that year
            rank = (agg_year_city[agg_year_city["Year"] == selected]
                    .sort_values("count", ascending=False)
                    .drop(columns=["Year"])
                    .copy())
            title = f"Citywide Crime Ranking ({selected})"

    # Label each crime as violent or property
    rank["Category"] = rank["Crm Cd Desc"].apply(lambda d: "Violent" if is_violent(d) else "Property")

    return rank.to_dict("records"), title

if __name__ == "__main__":
    app.run(debug=True)