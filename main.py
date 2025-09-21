import pandas as pd
import plotly.express as px

df = pd.read_csv("Crime_Data_from_2020_to_Present.csv")

# Filter only Part 1 crimes
df = df[df["Part 1-2"] == 1]

# define with team
violent_list = [
    "AGGREVATED ASSULT",
    "GRAND THEFT AUTO",
    "CRIMINAL HOMICIDE",
    "FORCIBLE RAPE",
    "RAPE, ATTEMPTED"
]

# define with team
property_list = [

]

# 1 = violent, 0 = property
df["Violent"] = df["Crm Cd Desc"].isin(violent_list).astype(int)

# -----Creating Map-----

# Clean coordinates
df = df[(df["LAT"] != 0) & (df["LON"] != 0)]

# Sample
df = df.sample(n=100000, random_state=1)


# Create density heatmap
fig = px.density_mapbox(
    df,
    lat="LAT",
    lon="LON",
    z="Violent",
    radius=5,
    hover_data=["AREA NAME", "Crm Cd Desc"],
    center={"lat": 34.05, "lon": -118.25},
    zoom=9,
    height=700
)

#Offset label
fig.update_layout(
    mapbox_style="open-street-map",
    hovermode="closest",
    hoverdistance=40,
    hoverlabel=dict(
        bgcolor = "black",
        font_size=10,
        font_color="white",
        align="left"
    ),
    margin=dict(r=200)
)

fig.update_traces(
    hoverlabel=dict(
        namelength=-1
    )
)

fig.show()
