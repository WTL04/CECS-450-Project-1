# Los Angeles Crime Visualization Dashboard

This project is an interactive Dash web app that visualizes crime data across LAPD geographic divisions. It uses open-source datasets from the Los Angeles Open Data Portal and presents both violent and property crime distributions across different years (2020–2024) on a dynamic map and interactive tables/pie charts.

🎯 Purpose

The goal of this project is to make it easier to **explore and understand patterns in violent crimes** across Los Angeles. Users can:

* View crime trends by year or across all years (2020–2024)
* Interactively explore crime density by LAPD division
* Compare violent vs property crime ratios
* See top crime categories per area or citywide

 🧠 How It Works

The app loads the main CSV dataset (`Crime_Data_from_2020_to_Present.csv`) and the LAPD divisions GeoJSON file (`LAPD_Division_5922489107755548254.geojson`).
It then:

1. Cleans and filter* the dataset to include only Part 1 (serious) crimes.
2. Parses and extracts the occurrence year from each crime record.
3. Flags violent crimes based on keywords like “ASSAULT,” “ROBBERY,” “RAPE,” etc.
4. Aggregates data by year and LAPD division.
5. Uses Plotly to render an interactive choropleth map of violent crime ratios.
6. Displays either a ranking table or pie chart of top crimes when a user clicks on a division.

🗺️ Features

* Choropleth Map:
  Shows the ratio of violent crimes to total crimes by LAPD division.

* Dropdown Year Selector:
  Choose between individual years (2020–2024) or view all years combined.

* Interactive Table & Pie Chart:
  Switch between a sortable data table or a pie chart of top crimes.

* Division Click Interaction:
  Click any division on the map to drill down into its local crime stats.


🧩 Tech Stack

| Component        | Technology                                     |
| ---------------- | ---------------------------------------------- |
| Backend / Server | Python 3.x                                     |
| Web Framework    | Dash (Plotly)                                  |
| Data Processing  | pandas                                         |
| Visualization    | plotly.express                                 |
| Dataset          | Los Angeles Open Data Portal (LAPD Crime Data) |
| Map Data         | LAPD Division GeoJSON                          |

---

⚙️ Setup Instructions

1. Install dependencies
   pip install pandas plotly dash

2. **Add data files**
   Place these files in the same directory as combo_map_2.py:

   Crime_Data_from_2020_to_Present.csv
   LAPD_Division_5922489107755548254.geojson

3. Run the app
   python combo_map_2.py

4. Open in your browser
   Visit:
   http://127.0.0.1:8050/

📊 Data Notes

* Only Part 1 crimes (serious offenses) are included.
* The app automatically removes invalid coordinates (e.g., LAT/LON = 0 or NaN).
* Violent crimes are identified using predefined keywords.
* Missing or malformed dates are parsed using multiple formats for accuracy.

📸 Output

When the app runs, you’ll see:

* A choropleth map of Los Angeles divided by LAPD divisions.
* A table or pie chart on the left summarizing top crimes.
* Dropdowns to switch years.


💡 Possible Improvements

* Add a time-series trend line for each division.
* Include filters for specific crime types or categories.
* Deploy on Heroku or Render for public access.
* Add monthly heatmaps or animations to show changes over time.

---

👤 Author
