import json
from datetime import date
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

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

   ## upload to gcs raw
   return {"source": "success"}


@app.post("/collect/raw_noaa")
def collect_noaa():
   noaa = collect_stations()

   ## upload to gcs raw
   
   return {"source": "success"}
    


@app.post("/collect/raw_festivals")
def collect_festivals():
   """Wikipedia: scrape the U.S. music festival list and store it in raw/festivals/."""
   wiki_scrape = get_scraped_festivals("https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States")

   ## upload to gcs raw
   return {"source": "success"}



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

   ## transform the necessary data 

   ### put the cleaned data together into one json/object etc
   noaa_records = collect_stations()

   print(join_data(clean_noaa(noaa_records), clean_epa(), clean_wiki(get_scraped_festivals("https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States"))))

   combined_element = []
    
   ### call storage / store this combined document


   pass



