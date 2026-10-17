import json
from datetime import date
import re

from fastapi import FastAPI, HTTPException

## These are our collectors:
from collectors.epa_collector import collect_epa
from collectors.noaa_collector import collect_stations
from collectors.wikipedia_scraper import get_scraped_festivals

## the transform.py will transform the data into once document before we can store it into gcs
from transform import *

## storage - we can call the function inside storage.py
from storage import *


# from pydantic import BaseModel

# from user_definition import *


app = FastAPI(
    title="Festival Smoke Detectors API",
    description="Collects raw festival (Wikipedia), heat (NOAA) and smoke (EPA) data into the team GCS bucket.",
    version="1.0.0",
)

WIKI_URL = ("https://en.wikipedia.org/wiki/"
            "List_of_music_festivals_in_the_United_States")
PROCESSED_PATH = "processed/festival_weather.parquet"


@app.post("/collect/raw_epa")
def collect_raw_epa():

   try:
      return collect_epa()
   except Exception as e:
      raise HTTPException(status_code=502,
                          detail=f"EPA collection failed: {e}")



@app.post("/collect/raw_noaa")
def collect_noaa():
   try:
      return collect_stations()
   except Exception as e:
      raise HTTPException(status_code=502,
                          detail=f"NOAA collection failed: {e}")



@app.post("/collect/raw_festivals")
def collect_festivals():
   """Wikipedia: scrape the U.S. music festival list and store it in raw/festivals/."""
   try:
      wiki_scrape = get_scraped_festivals(WIKI_URL)
   except Exception as e:
      raise HTTPException(status_code=502,
                          detail=f"Wikipedia scrape failed: {e}")

   ## upload to gcs raw
   return {"source": "wiki", "festivals": len(wiki_scrape)}

def latest_blobs(source):
   # See what blobs were added recently
   paths = [p for p in list_blobs(f"raw/{source}/") if len(p.split("/"))== 4 and p.split("/")[3]]

   if not paths:
      return []
   newest = max(p.split("/")[2] for p in paths)
   return [p for p in paths if p.split("/")[2] == newest]


# On first start of the app -- the transform and storage functions are run so that all of the data is reloaded

@app.post("/extract_and_save")
def extract_and_save():
    """Read the latest raw files, clean and join them, write the processed table.
   """
    noaa_paths = latest_blobs("noaa")
    epa_paths = latest_blobs("epa")
    wiki_paths = latest_blobs("wiki")

    missing = [name for name, paths in
               [("noaa", noaa_paths), ("epa", epa_paths), ("wiki", wiki_paths)]
               if not paths]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"No raw data found for: {', '.join(missing)}. "
                   f"Run the collect routes first.",
        )

    noaa_records = []
    for path in noaa_paths:
        noaa_records.extend(json.loads(read_blob(path)))

    epa_zips = [read_blob(p) for p in epa_paths if p.endswith(".zip")]

    festival_records = []
    for path in wiki_paths:
        festival_records.extend(json.loads(read_blob(path)))

    noaa_df = clean_noaa(noaa_records)
    epa_df = clean_epa(epa_zips)
    festivals_df = clean_wiki(festival_records)

    final_df = join_data(noaa_df, epa_df, festivals_df)

    write_blob(PROCESSED_PATH, final_df.to_parquet(),
               content_type="application/octet-stream")

    return {
        "status": "ok",
        "path": PROCESSED_PATH,
        "rows": len(final_df),
        "festivals": int(final_df["festival_id"].nunique()),
        "date_range": [str(final_df["date"].min().date()),
                       str(final_df["date"].max().date())],
    }
