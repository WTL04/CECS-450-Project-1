import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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


fig.update_traces(hoverinfo="skip", hovertemplate=None)

#Adding invisible scattermapbox layer on heatmap
fig.add_trace(go.Scattermapbox(
    lat=df["LAT"],
    lon=df["LON"],
    mode="markers",
    marker=dict(size=5, opacity=0),
    hoverinfo="text",
    text=[
        f"Area: {area}<br>"
        f"Crime: {crime}<br>"
        f"Lat: {lat:.4f}<br>"
        f"Lon: {lon:.4f}<br>"
        f"Violent: {'Yes' if violent == 1 else 'No'}"
        for area, crime, lat, lon, violent in zip(
            df["AREA NAME"], df["Crm Cd Desc"], df["LAT"], df["LON"], df["Violent"]
        )
    ]

))


#Offset label
fig.update_layout(
    mapbox_style="open-street-map",
    hovermode="closest",
    hoverdistance=5,
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
