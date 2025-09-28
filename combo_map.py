import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

CSV_PATH = "Crime_Data_from_2020_to_Present.csv"
DIVISIONS_GEOJSON = "LAPD_Division_5922489107755548254.geojson"


CENTER = dict(lat=34.05, lon=-118.25)
ZOOM   = 9
HEIGHT = 820
MAP_STYLE = "open-street-map"

VIOLENT_KEYS = [
    "ASSAULT", "ROBBERY", "HOMICIDE", "MANSLAUGHTER",
    "RAPE", "SEXUAL", "PENETRATION", "ORAL COPULATION",
    "SODOMY", "BRANDISH WEAPON", "SHOTS FIRED"
]

def is_violent(desc: str) -> int:
    if not isinstance(desc, str):
        return 0
    u = desc.upper()
    return int(any(k in u for k in VIOLENT_KEYS))

def parse_occ_datetime(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if dt.isna().all():
        dt = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    miss = dt.isna()
    if miss.any():
        dt.loc[miss] = pd.to_datetime(series.loc[miss], errors="coerce")
    return dt

df = pd.read_csv(CSV_PATH, low_memory=False)

if "Part 1-2" in df.columns:
    try:
        df = df[df["Part 1-2"].astype(float) == 1.0]
    except Exception:
        df = df[df["Part 1-2"] == 1]

if "LAT" in df.columns and "LON" in df.columns:
    df = df[(df["LAT"].notna()) & (df["LON"].notna())]
    df = df[(df["LAT"] != 0) & (df["LON"] != 0)]

if "DATE OCC" in df.columns:
    df["OCC_DT"] = parse_occ_datetime(df["DATE OCC"])
    df = df.dropna(subset=["OCC_DT"])
    df["Year"] = df["OCC_DT"].dt.year
    df = df[df["Year"] == 2023]
else:
    print("[warn] 'DATE OCC' missing; not filtering to 2023.")

df["Violent"] = df["Crm Cd Desc"].apply(is_violent).astype(int)


if "AREA NAME" not in df.columns:
    df["AREA NAME"] = df.get("AREA", "").astype(str)
df["AREA NAME"] = df["AREA NAME"].astype(str).str.strip().str.upper()

df_geo = df.groupby("AREA NAME", as_index=False).agg(
    value=("Crm Cd Desc", "count")
).rename(columns={"AREA NAME": "APREC"})

with open(DIVISIONS_GEOJSON, "r") as f:
    gj = json.load(f)

for ft in gj["features"]:
    name = str(ft["properties"].get("APREC", "")).strip().upper()
    ft["properties"]["APREC_UP"] = name

df_geo["APREC"] = df_geo["APREC"].str.strip().str.upper()

fig_choro = px.choropleth_map(
    df_geo,
    geojson=gj,
    featureidkey="properties.APREC_UP",
    locations="APREC",
    color="value",
    color_continuous_scale="Viridis",
    center=CENTER,
    zoom=ZOOM,
    height=HEIGHT,
    opacity=0.85,
    map_style=MAP_STYLE,
)
fig_choro.update_traces(marker_line_width=0.6, marker_line_color="black")
fig_choro.update_coloraxes(colorbar_title="Incidents (2023)")
fig_choro.update_traces(
    hovertemplate="<b>%{location}</b><br>Incidents: %{z:,}<extra></extra>"
)

sample_n = min(120_000, len(df))
df_samp = df.sample(n=sample_n, random_state=1) if sample_n else df

fig_dens = px.density_map(
    df_samp,
    lat="LAT",
    lon="LON",
    z="Violent",              
    radius=10,                
    opacity=0.70,
    hover_data={
        "AREA NAME": True,
        "Crm Cd Desc": True,
        "LAT": False, "LON": False
    },
    center=CENTER,
    zoom=ZOOM,
    height=HEIGHT,
    map_style=MAP_STYLE,
    color_continuous_scale="YlOrRd"
)
for tr in fig_dens.data:
    tr.hovertemplate = (
        "Area: %{customdata[0]}<br>"
        "Crime: %{customdata[1]}<extra></extra>"
    )


fig = go.Figure(data=list(fig_choro.data))
n_choro = len(fig_choro.data)

for tr in fig_dens.data:
    tr.visible = False
fig.add_traces(fig_dens.data)
n_dens = len(fig_dens.data)

fig.update_layout(
    map=dict(style=MAP_STYLE, center=CENTER, zoom=ZOOM),
    margin=dict(l=0, r=0, t=44, b=0),
    title="LA Crime — Choropleth (divisions) vs Density (hotspots) — 2023",
    updatemenus=[{
        "type": "buttons",
        "x": 0.02, "y": 0.98, "xanchor": "left",
        "buttons": [
            {
                "label": "Choropleth (by division)",
                "method": "update",
                "args": [
                    {"visible": [True]*n_choro + [False]*n_dens},
                    {"title": "LA Crime — Choropleth by LAPD Division (2023)"}
                ],
            },
            {
                "label": "Density (incident hotspots)",
                "method": "update",
                "args": [
                    {"visible": [False]*n_choro + [True]*n_dens},
                    {"title": "LA Crime — Density Heatmap of Incidents (2023)"}
                ],
            },
            {
                "label": "Both",
                "method": "update",
                "args": [
                    {"visible": [True]*n_choro + [True]*n_dens},
                    {"title": "LA Crime — Choropleth + Density (2023)"}
                ],
            },
        ]
    }]
)

fig.write_html(
    "la_crime.html",
    include_plotlyjs="inline",
    full_html=True,
    auto_open=True
)
print("[ok] la_crime.html and opened it.")
