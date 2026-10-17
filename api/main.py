import json
from datetime import date
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.protobuf.json_format import MessageToDict

## These are our collectors: 
from epa_collector import *
from noaa_collector import *
from wikipedia_scraper import * 

## the transform.py will transform the data into once document before we can store it into gcs 
from transform import *

## storage - we can call the function inside storage.py 
from storage import *


from pydantic import BaseModel

from user_definition import *


app = FastAPI(
    title="Festival Smoke Detectors API",
    description="Collects raw festival (Wikipedia), heat (NOAA) and smoke (EPA) data into the team GCS bucket.",
    version="1.0.0",
)

@app.post("/collect/raw_epa")
def collect_raw_epa():
   epa = collect_stations()

   ## transform epa
   ## store transformed_epa
   return {"source": "success"}


@app.post("/collect/raw_noaa")
def collect_noaa():
   noaa = collect_stations()

   ## transform noaa
   ## store transformed_noaa

   ## upload to gcs raw
   
   return {"source": "success"}
    


@app.post("/collect/raw_festivals")
def collect_festivals():
   url = "https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States"
   wiki_scrape = get_scraped_festivals(url)
   ## upload to gcs raw
   return {"source": "success"}

def latest_blobs(bucket, source):
   blobs = []
   for b in bucket.list_blobs(prefix=f"raw/{source}/"):
      parts = b.name.split("/")
      if len(parts) == 4 and parts[3]:
            blobs.append(b)
      if not blobs:
            return []
      date = max(b.name.split("/")[2] for b in blobs)
      return [b for b in blobs if b.name.split("/")[2] == date]


# On first start of the app -- the transform and storage functions are run so that all of the data is reloaded

@app.post("/extract_and_save")
def extract_and_save():
   """
    Use 

    TODO:
    1. Split search_input.company_dict into two groups: the "Anthropic"
       entry (if present) and everything else.
    2. For EPA, the code should go to the corresponding value of
       `festival`, .
       Extract the information including title, and URL,
       and call qualification_parser to get qualification.
       (optional) To improve performance you can try the asynchronous version.
    3. Build up a single festival_data_response dict incrementally: start it
       empty, add Wikipedia results first (if any), then call
       noa for the noaa data, then call epa_collector for the epa data.
   5. Save the combined data to GCS the same way HW3 did.
   """
   print("PRINT PRINT PRINT !!!!")


   ## retrieve from bucket latest data 
   credentials = service_account.Credentials.from_service_account_file(
              service_account_file_path)
   client = storage.Client(project=project_id,
                                  credentials=credentials)
   bucket = client.bucket(bucket_name)
   
   latest_epa = latest_blobs(bucket, "epa")
   latest_noaa = latest_blobs(bucket, "noaa")
   latest_wiki = latest_blobs(bucket, "wiki")

   print("-------------------- LATEST RAW EPA ---------------")
   print(json.loads(latest_epa[0].download_as_text()))
   print("-------------------- LATEST RAW EPA ---------------")


   print("-------------------- LATEST RAW NOAA---------------")
   print(json.loads(latest_noaa[0].download_as_text()))
   print("-------------------- LATEST RAW NOAA---------------")

   print("-------------------- LATEST RAW WIKI---------------")
   print(json.loads(latest_wiki[0].download_as_text()))
   print("-------------------- LATEST RAW WIKI---------------")


   ### put the data together into one json/object etc

   combined_element = []
    
   ### call storage / store this combined document

   ## [ERIN CAN YOU REMOVE WHAT BITS WE DONT NEED IN THIS WHEN I SLEEP :D] example format of how it should look~~ (final json): 
   """
   {
  "festival_id": "slug(wiki.Name)",
  "name": "wiki.Name",
  "location": {
    "city": "wiki.city_name",
    "state": "wiki.state.replace('_', ' ')",
    "county_fips": "wiki.fips  <- JOIN KEY to EPA",
    "latitude": "wiki.latitude",
    "longitude": "wiki.longitude",
    "venue": "wiki.venue"
  },
  "festival_info": {
    "genre": "wiki.genre",
    "status": "wiki['is_active:']",
    "frequency": "wiki.frequency",
    "years_active": "wiki.years_active",
    "year_founded": "wiki.year_founded"
  },
  "air_quality_site": {
    "site_id": "epa['State Code'] + '-' + epa['County Code'] + '-' + epa['Site Num']",
    "county_fips": "epa['State Code'] + epa['County Code']",
    "site_name": "epa['Local Site Name']",
    "latitude": "float(epa['Latitude'])",
    "longitude": "float(epa['Longitude'])",
    "distance_km": "haversine(festival, site)"
  },
  "weather_station": {
    "station_id": "noaa['STATION']",
    "latitude": "station metadata (not in the raw NOAA file)",
    "longitude": "station metadata (not in the raw NOAA file)",
    "distance_km": "haversine(festival, station)"
  },
  "daily": [
    {
      "date": "epa['Date Local'] == noaa['DATE']  <- JOIN KEY between EPA and NOAA",
      "pm25_mean": "float(epa['Arithmetic Mean'])",
      "pm25_max": "float(epa['1st Max Value'])",
      "pm25_obs_pct": "float(epa['Observation Percent'])",
      "aqi": "int(epa['AQI']) if epa['AQI'] else null",
      "tmax_c": "int(noaa['TMAX'].strip()) / 10"
    }
  ],
  "sources": {
    "wiki": "raw/wiki/<date>/festival_details.json",
    "epa": "raw/epa/<date>/<file>.json",
    "noaa": "raw/noaa/<date>/<station>.json"
  }
}
   
   """


   pass



