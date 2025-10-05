import json
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table, Input, Output

CSV_PATH = "Crime_Data_from_2020_to_Present.csv"
DIVISIONS_GEOJSON = "LAPD_Division_5922489107755548254.geojson"


CENTER = dict(lat=34.05, lon=-118.25)
ZOOM  = 9
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

df_area = df.groupby("AREA NAME"). agg(
    total=("Crm Cd Desc","count"),
    violent=("Violent","sum")
).reset_index()
df_area["violent_ratio"] = df_area["violent"] / df_area["total"]

rankings = (
    df.groupby(["AREA NAME", "Crm Cd Desc"])
        .size()
        .reset_index(name="count")
)

with open(DIVISIONS_GEOJSON, "r") as f:
    gj = json.load(f)

for ft in gj["features"]:
    name = str(ft["properties"].get("APREC", "")).strip().upper()
    ft["properties"]["APREC_UP"] = name

df_area["APREC"] = df_area["AREA NAME"]

all_divisions = [f["properties"]["APREC_UP"] for f in gj["features"]]

all_df = pd.DataFrame({"APREC": all_divisions})
df_area = all_df.merge(df_area, on="APREC", how="left")

df_area["total"] = df_area["total"].fillna(0)
df_area["violent"] = df_area["violent"].fillna(0)
df_area["violent_ratio"] = df_area["violent_ratio"].fillna(0)

choropleth = px.choropleth_map(
    df_area,
    geojson=gj,
    featureidkey="properties.APREC_UP",
    locations="APREC",
    color="violent_ratio",
    color_continuous_scale="Reds",
    center=CENTER,
    zoom=ZOOM,
    height=650
)

choropleth.update_traces(
    marker_opacity=0.45,
    marker_line_width=1.5,
    marker_line_color="black"
)

choropleth.update_traces(
    hovertemplate="<b>%{location}</b><br>Violent Ratio: %{z:.2%}<extra></extra>"
)

app = Dash(__name__)

app.layout = html.Div([
    html.H2("Los Angeles - Violent Crime Ratio by Division (2023)"),
    html.Div([
        html.Div([
            html.H4(id="ranking-title", children="Crime Ranking (2023)", style={"textAlign": "center", "marginBottom": "10px"}),
            dash_table.DataTable(
                id = "crime-ranking-table",
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
                page_size=20
            )
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),

        dcc.Graph(id="crime-map", figure=choropleth, style={"width": "68%", "display": "inline-block"})
    ])
])

@app.callback(
    [Output("crime-ranking-table", "data"),
    Output("ranking-title", "children")],
    Input("crime-map", "clickData")
)
def update_ranking_table(clickData):
    if clickData is None:
        area = df_area.iloc[0]["AREA NAME"]
    else:
        area = clickData["points"][0].get("location", df_area.iloc[0]["AREA NAME"])

    rank = (
        df[df["AREA NAME"] == area]
        .groupby("Crm Cd Desc")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    rank["Label"] = rank["Crm Cd Desc"].apply(
        lambda s: s.split()[0:3] and " ".join(s.split()[0:3]) + "..." if len(s.split()) > 3 else s
    )

    rank["Category"] = rank["Crm Cd Desc"].apply(
        lambda desc: "Violent" if is_violent(desc) else "Property"
    )

    title = f"Crime Ranking in {area} (2023)"
    return rank.to_dict("records"), title

if __name__ == "__main__":
    app.run(debug=True)
