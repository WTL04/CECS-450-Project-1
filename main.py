import pandas as pd
import plotly.express as px

df = pd.read_csv("Crime_Data_from_2020_to_Present.csv")

# Filter only Part 1 crimes
df = df[df["Part 1-2"] == 1]

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

# # Total number of Part 1 crimes
# print(f"Total Part 1 crimes: {len(df):,}")

# # Count of each Part 1 crime description
# print("\nCounts by Crime Description:")
# print(df["Crm Cd Desc"].value_counts())

# # Count of Violent vs Property (1 vs 0)
# print("\nCounts by Violent Flag:")
# print(df["Violent"].value_counts().rename({1: "Violent", 0: "Property"}))

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
