# run from terminal
import json, pandas as pd, plotly.express as px, plotly.io as pio
pio.renderers.default = "browser"   # opens in system browser

CSV = "Crime_Data_from_2020_to_Present.csv"
GEO = "LAPD_Division_5922489107755548254.geojson"

CENTER = {"lat":34.05,"lon":-118.25}
ZOOM = 9
HEIGHT = 800

# ---- load + prep ----
df = pd.read_csv(CSV)
df = df[df["Part 1-2"] == 1] # filter part 1 crimes, see google doc for details
df = df[(df["LAT"] != 0) & (df["LON"] != 0)] # cleaning up coord data

# set violent crimes = 1, via keywords
violent_kw = ["ASSAULT","ROBBERY","HOMICIDE","MANSLAUGHTER","RAPE","SEXUAL",
              "PENETRATION","ORAL COPULATION","SODOMY","BRANDISH WEAPON","SHOTS FIRED"]
pat = "|".join(violent_kw)
df["Violent"] = df["Crm Cd Desc"].str.upper().str.contains(pat, regex=True).astype(int)


# open up geojson for choropleth map
with open(GEO) as f:
    gj = json.load(f)

df_geo = pd.DataFrame({
    "APREC": [ft["properties"]["APREC"] for ft in gj["features"]],
    "value": range(len(gj["features"]))   # unique dummy values
})

# ---- choropleth (divisions) ----
fig_choro = px.choropleth_map(
    df_geo, 
    geojson=gj,
    featureidkey="properties.APREC",   
    locations="APREC",
    color="value",                       # dummy column drives fill
    color_continuous_scale="Viridis",
    map_style="open-street-map",
    center=CENTER, 
    zoom=ZOOM, 
    opacity=0.85, 
    height=HEIGHT
)
fig_choro.update_traces(marker_line_width=0.6, marker_line_color="black")


# ---- density (points) with sample----
fig_dens = px.density_map(
    df.sample(n=min(120_000, len(df)), random_state=1),
    lat="LAT", 
    lon="LON", 
    z="Violent",
    radius=5, 
    hover_data=["AREA NAME","Crm Cd Desc"],
    center=CENTER, 
    zoom=ZOOM, 
    height=HEIGHT
)
fig_dens.update_layout(map_style="open-street-map")

# ---- combine + toggle ----
fig = fig_choro
n_choro = len(fig_choro.data)
n_dens  = len(fig_dens.data)

# add density traces (initially hidden)
for tr in fig_dens.data:
    tr.visible = False
fig.add_traces(fig_dens.data)

fig.update_layout(
    updatemenus=[{
        "type":"buttons", "x":0.02, "y":0.98, "xanchor":"left",
        "buttons":[
            {"label":"Choropleth (by division)",
             "method":"update",
             "args":[{"visible":[True]*n_choro + [False]*n_dens}]},
            {"label":"Density (incident hotspots)",
             "method":"update",
             "args":[{"visible":[False]*n_choro + [True]*n_dens}]},
            {"label":"Both",
             "method":"update",
             "args":[{"visible":[True]*n_choro + [True]*n_dens}]},
        ]
    }],
    margin=dict(l=0,r=0,t=0,b=0)
)

fig.show()

