import pandas as pd
import plotly.express as px
import json

CSV = "Crime_Data_from_2020_to_Present.csv"
GEO = "LAPD_Division_5922489107755548254.geojson"

# -----prep data-----
df = pd.read_csv(CSV)
df = df[df["Part 1-2"] == 1]
df = df[(df["LAT"] != 0) & (df["LON"] != 0)]

violent_keyWords = [
    "ASSAULT", "ROBBERY", "HOMICIDE", "MANSLAUGHTER",
    "RAPE", "SEXUAL", "PENETRATION", "ORAL COPULATION",
    "SODOMY", "BRANDISH WEAPON", "SHOTS FIRED"
]

# filters out violent crimes based on keywords
def is_violent(crime):
    return any(keyword in crime for keyword in violent_keyWords)

# 1 = violent, 0 = property
df["Violent"] = df["Crm Cd Desc"].apply(is_violent).astype(int)


# -----Creating Map-----

# Clean coordinates
df = df[(df["LAT"] != 0) & (df["LON"] != 0)]

# Sample
df = df.sample(n=100000, random_state=1)

# Create density heatmap
fig = px.density_map(
    df,
    lat="LAT",
    lon="LON",
    z="Violent",
    radius=5,
    hover_data=["AREA NAME", "Crm Cd Desc"],
    center={"lat": 34.05, "lon": -118.25},
    zoom=9,
    height=900
)

fig.update_layout(mapbox_style="open-street-map")
fig.show()
