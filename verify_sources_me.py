import requests
import pandas as pd

header = {"User-Agent": "USF-course-project (enlukow@dons.usfca.edu)"}

# Access Wikipedia
print(requests.get("https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States", headers=header).status_code)

# Access NOAA API
r = requests.get(
    "https://www.ncei.noaa.gov/access/services/data/v1",
    params={
        "dataset": "daily-summaries",
        "dataTypes": "TMAX",
        "stations": "USW00023234",
        "startDate": "2025-07-01",
        "endDate": "2025-07-07",
        "format": "json",
    },
    headers=header,
)
print(r.status_code)
print(r.json()[:2])

# Access EPA
print(pd.read_csv("https://aqs.epa.gov/aqsweb/airdata/daily_88101_2025.zip").shape)