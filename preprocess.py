import pandas as pd

data = pd.read_csv("Crime_Data_from_2020_to_Present.csv")
print(data.columns)


data.drop("TIME OCC", axis = 1)
print(data.columns)

