import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#File paths for data sources
CSV_PATH = "Crime_Data_from_2020_to_Present.csv"
DIVISIONS_GEOJSON = "LAPD_Division_5922489107755548254.geojson"

#Configure map
CENTER = dict(lat=34.05, lon=-118.25)
ZOOM  = 9
HEIGHT = 820
MAP_STYLE = "open-street-map"

#Key words to identify violent crimes
VIOLENT_KEYS = [
    "ASSAULT", "ROBBERY", "HOMICIDE", "MANSLAUGHTER",
    "RAPE", "SEXUAL", "PENETRATION", "ORAL COPULATION",
    "SODOMY", "BRANDISH WEAPON", "SHOTS FIRED"
]

#Determine if a crime is violent based on keywords
def is_violent(desc: str) -> int:
    if not isinstance(desc, str):
        return 0
    u = desc.upper()
    return int(any(k in u for k in VIOLENT_KEYS))

#Convert "Date OCC" column in dataset to datetime to handle different format
def parse_occ_datetime(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if dt.isna().all():
        dt = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    miss = dt.isna()
    if miss.any():
        dt.loc[miss] = pd.to_datetime(series.loc[miss], errors="coerce")
    return dt

#Load raw CSV data
df = pd.read_csv(CSV_PATH, low_memory=False)

#Filter dataset to include Part 1 crimes ("Serious crimes")
if "Part 1-2" in df.columns:
    try:
        df = df[df["Part 1-2"].astype(float) == 1.0]
    except Exception:
        df = df[df["Part 1-2"] == 1]

#Drop rows with missing or invalid coordinates
if "LAT" in df.columns and "LON" in df.columns:
    df = df[(df["LAT"].notna()) & (df["LON"].notna())]
    df = df[(df["LAT"] != 0) & (df["LON"] != 0)]

#Parse date column and extract years
if "DATE OCC" in df.columns:
    df["OCC_DT"] = parse_occ_datetime(df["DATE OCC"])
    df = df.dropna(subset=["OCC_DT"])
    df["Year"] = df["OCC_DT"].dt.year
    #df = df[df["Year"] == 2023]
else:
    print("[warn] 'DATE OCC' missing; not filtering to 2023.")

#Label crimes as "Violent" or "Property" crimes
df["Violent"] = df["Crm Cd Desc"].apply(is_violent).astype(int)

#Normalize "AREA NAME" column to uppercase and remove blanks
if "AREA NAME" not in df.columns:
    df["AREA NAME"] = df.get("AREA", "").astype(str)
df["AREA NAME"] = df["AREA NAME"].astype(str).str.strip().str.upper()

#Aggregate total and violent crime counts per division
df_area = df.groupby("AREA NAME"). agg(
    total=("Crm Cd Desc","count"),
    violent=("Violent","sum")
).reset_index()
df_area["violent_ratio"] = df_area["violent"] / df_area["total"]

#Count crime type per division for ranking table
rankings = (
    df.groupby(["AREA NAME", "Crm Cd Desc"])
        .size()
        .reset_index(name="count")
)

#Load LAPD GeoJSON division boundaries
with open(DIVISIONS_GEOJSON, "r") as f:
    gj = json.load(f)

#Clean up division names and store normalized names in GeoJson
for ft in gj["features"]:
    name = str(ft["properties"].get("APREC", "")).strip().upper()
    ft["properties"]["APREC_UP"] = name

#Merge map divisions with aggregated crime counts
df_area["APREC"] = df_area["AREA NAME"]
all_divisions = [f["properties"]["APREC_UP"] for f in gj["features"]]
all_df = pd.DataFrame({"APREC": all_divisions})
df_area = all_df.merge(df_area, on="APREC", how="left")

#Fill missing division values with zeros
df_area["total"] = df_area["total"].fillna(0)
df_area["violent"] = df_area["violent"].fillna(0)
df_area["violent_ratio"] = df_area["violent_ratio"].fillna(0)
df_area["property"] = (df_area["total"] - df_area["violent"]).clip(lower=0)

#Define available years for filtering
YEARS = [2020, 2021, 2022, 2023, 2024]

#Maintain consistent division ordering across datasets
ALL_DIVISIONS = [f["properties"]["APREC_UP"] for f in gj["features"]]
div_order_df = pd.DataFrame({"APREC": ALL_DIVISIONS})

#Create yearly crime summaries by division
df_year_area = (
    df.groupby(["AREA NAME", "Year"])
    .agg(total=("Crm Cd Desc", "count"),
         violent=("Violent", "sum"))
    .reset_index()
    .rename(columns={"AREA NAME":"APREC"})
)

#Generate yearly map data (violent crime ratios and property crime counts)
year_map_data={}
for y in YEARS:
    ydf = df_year_area[df_year_area["Year"] == y][["APREC", "total", "violent"]].copy()
    ydf = div_order_df.merge(ydf, on="APREC", how="left")
    ydf[["total","violent"]] = ydf[["total","violent"]].fillna(0)
    ydf["violent_ratio"] = (ydf["violent"] / ydf["total"]).fillna(0)
    ydf["property"] = (ydf["total"] - ydf["violent"]).clip(lower=0)
    year_map_data[y] = ydf

#Calculate aggregate data for all years
ydf_all = (
    df.groupby("AREA NAME")
    .agg(total=("Crm Cd Desc", "count"),
         violent=("Violent", "sum"))
    .reset_index()
    .rename(columns={"AREA NAME": "APREC"})
)
ydf_all = div_order_df.merge(ydf_all, on="APREC", how="left")
ydf_all[["total", "violent"]] = ydf_all[["total", "violent"]].fillna(0)
ydf_all["violent_ratio"] = (ydf_all["violent"] / ydf_all["total"]).fillna(0)
ydf_all["property"] = (ydf_all["total"] - ydf_all["violent"]).clip(lower=0)
year_map_data["ALL"] = ydf_all

#Initialize map using dataset of all years
init_year = "ALL"
init_df_area = year_map_data[init_year]

#Create choropleth map showing violent crime ratios per division
choropleth = px.choropleth_map(
    init_df_area,
    geojson=gj,
    featureidkey="properties.APREC_UP",
    locations="APREC",
    color="violent_ratio",
    color_continuous_scale="Reds",
    center=CENTER,
    zoom=ZOOM,
    height=650,
    map_style=MAP_STYLE,
    custom_data=["total", "violent", "property"]
)

#Configure map visuals and hover information
choropleth.update_traces(
    marker_opacity=0.45,
    marker_line_width=1.5,
    marker_line_color="black",
    hovertemplate=(
        "<b>%{location}</b>"
        "<br>Total Crimes: %{customdata[0]:,}"
        "<br>Violent: %{customdata[1]:,}"
        "<br>Property: %{customdata[2]:,}"
        "<br>Violent Ratio: %{z:.2%}"
        "<extra></extra>"
    )
)

#Create subplot layout with map on the left and table on the right
fig = make_subplots(rows=1, cols=2, column_widths=[0.7, 0.3],
                    specs=[[{"type": "choroplethmap"}, {"type": "table"}]],
                    subplot_titles=("LA Violent Crime Ratio by LAPD Geographic Division", "Crime Ranking in Division (Descending)"))

#Adding choropleth map to subplot
for tr in choropleth.data:
    fig.add_trace(tr, row=1, col=1)

#Building initial ranking table for first division
default_area = df_area.iloc[0]["AREA NAME"]
rank = (df[df["AREA NAME"] == default_area]
        .groupby("Crm Cd Desc").size()
        .reset_index(name="count")
        .sort_values("count", ascending=False))
rank["Category"] = rank["Crm Cd Desc"].apply(lambda desc: "Violent" if is_violent(desc) else "Property")

#Create table visualization with color coding per category
table = go.Table(
    columnwidth=[60, 20, 20],
    header=dict(
        values=["Crime Type", "Count", "Category"],
        fill_color="lightgray",
        align="left",
        font=dict(size=13, color="black")
    ),
    cells=dict(
        values=[rank["Crm Cd Desc"], rank["count"], rank["Category"]],
        fill_color=[["white" if c=="Property" else "#ffcccc" for c in rank["Category"]]],
        align="left",
        font=dict(size=13, color="black"),
        height=25
    )
)

fig.add_trace(table, row=1, col=2)

#ADjust map layout within subplot
fig.update_layout(
    map=dict(
        center=CENTER,
        zoom=ZOOM,
        style=MAP_STYLE
    )
)

#Styling table font and headers
table_index = len(fig.data) - 1

fig.update_traces(
    selector=dict(type="table"),
    columnwidth=[60, 20, 20],
    cells=dict(align="left", height=25, font=dict(size=13, color="black")),
    header=dict(fill_color="lightgray", font=dict(size=13, color="black"))
)

#Build dropdown menu buttons for each division
buttons = []
for area in sorted(df["AREA NAME"].unique()):
    rank = (
        df[df["AREA NAME"] == area]
        .groupby("Crm Cd Desc").size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    rank["Category"] = rank["Crm Cd Desc"].apply(
        lambda desc: "Violent" if is_violent(desc) else "Property"
    )

    crimes = rank["Crm Cd Desc"].tolist()
    counts = rank["count"].tolist()
    cats = rank["Category"].tolist()
    colors = [["#ffffff" if c == "Property" else "#ffcccc" for c in cats]]

    buttons.append(dict(
        label=area,
        method="update",
        args=[
            {
                "cells": dict(
                    values=[crimes, counts, cats],
                    fill=dict(color=colors),
                    align="left",
                    height=25,
                    font=dict(size=13, color="black")
                ),
                "header": dict(
                    values=["Crime Type", "Count", "Category"],
                    fill=dict(color="lightgray"),
                    align="left",
                    font=dict(size=13, color="black")
                ),
                "columnwidth": [60, 20, 20]
            },
            {},
            [table_index]
        ]
    ))

#Option for "ALL DIvisions" which includes citywide crime totals
all_rank = (
    df.groupby("Crm Cd Desc")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

all_rank["Category"] = all_rank["Crm Cd Desc"].apply(
    lambda desc: "Violent" if is_violent(desc) else "Property"
)

crimes = all_rank["Crm Cd Desc"].tolist()
counts = all_rank["count"].tolist()
categories = all_rank["Category"].tolist()
colors = [["#ffffff" if c =="Property" else "ffcccc" for c in categories]]

buttons.insert(0, dict(   # insert at top so "ALL DIVISIONS" appears first
    label="ALL DIVISIONS",
    method="update",
    args=[
        {
            "cells": dict(
                values=[crimes, counts, categories],
                fill=dict(color=colors),
                align="left",
                height=25,
                font=dict(size=13, color="black")
            ),
            "header": dict(
                values=["Crime Type", "Count", "Category"],
                fill=dict(color="lightgray"),
                align="left",
                font=dict(size=13, color="black")
            ),
            "columnwidth": [60, 20, 20]
        },
        {},
        [table_index]
    ]
))

#Create year-based buttons for map updates
map_index = 0
YEARS = [2020, 2021, 2022, 2023, 2024]
city_rank_year = {}

#Build year-by-year rankings for entire city
for y in YEARS:
    r = (df[df["OCC_DT"].dt.year == y]
         .groupby("Crm Cd Desc").size()
         .reset_index(name="count")
         .sort_values("count", ascending=False))
    r["Category"] = r["Crm Cd Desc"].apply(lambda d: "Violent" if is_violent(d) else "Property")
    city_rank_year[y] = r

#Add combined statistics for all years
if "ALL" in year_map_data:
    r_all = (df.groupby("Crm Cd Desc")
             .size()
             .reset_index(name="count")
             .sort_values("count", ascending = False))
    r_all["Category"] = r_all["Crm Cd Desc"].apply(lambda d: "Violent" if is_violent(d) else "Property")
    city_rank_year["ALL"] = r_all

#Build year dropdown for switching years
year_options = (["ALL"] if "ALL" in year_map_data else []) + YEARS
year_buttons = []
for y in year_options:
    ydf = year_map_data[y]
    z_vals = ydf["violent_ratio"].tolist()
    custom = ydf[["total", "violent", "property"]].values.tolist()

    rt = city_rank_year[y]
    crimes = rt["Crm Cd Desc"].tolist()
    counts = rt["count"].tolist()
    categories = rt["Category"].tolist()
    colors = [["#ffffff" if c == "Property" else "ffcccc" for c in categories]]

    year_buttons.append(dict(
        label=str(y),
        method="restyle",
        args=[
            {
                "z": [z_vals],
                "customdata": [custom],
                "cells.values": [[crimes, counts, categories]],
                "cells.fill.color": [colors]
            },
            [map_index, table_index]
        ]
    ))

#Create definition for year dropdown meny
year_menu = dict(
    buttons=year_buttons,
    direction="down",
    showactive=True,
    x=0.2, xanchor="left",
    y=1.12, yanchor="top",
    active= year_options.index(init_year) if "init_year" in globals() and init_year in year_options else 0
)

#Position dropdown menus
year_menu.update({
    "type": "dropdown",
    "x": 0, "xanchor": "left",
    "y": 1, "yanchor": "bottom",
    "direction": "down",
    "showactive": True,
    "pad": {"t": 4, "r": 4}
})

fig.update_layout(
    updatemenus=[
        year_menu,
        dict(
            type="dropdown",
            active=0,
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0.86, xanchor="left",
            y=1.04, yanchor="bottom",
            pad={"t": 4, "r": 4}
         )],
    #Colorbar and layout configuration
    coloraxis_colorbar=dict(
        title=dict(
            text="Ratio of Violent to Property Crimes",
            side="right",
            font=dict(size=12),
        ),
        x=0.63, xanchor="left",
        y=0.5, yanchor="middle",
        len=0.9,
        thickness=12,
        bgcolor="rgba(255,255,255,0.7)",
        outlinewidth=0
    ),
    margin=dict(l=0, r=0, t=80, b=0),
    height=800,
    title="Los Angeles - Violent Crime Ratio and Rankings by LAPD Geographic Division"
)

#Export HTML file
fig.write_html("la_crime_ratio_2023.html", auto_open=True)
print("la_crime_ratio_2023.html created")