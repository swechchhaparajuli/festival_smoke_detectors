import importlib
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound
from google.auth.exceptions import DefaultCredentialsError
from pydantic import BaseModel, Field, model_validator

from user_definition import bucket_name, project_id

THIS_YEAR = date.today().year

app = FastAPI(title="Festival Smoke Detectors API")


def load_collector(name):
    try:
        return importlib.import_module(f"collectors.{name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load collectors/{name}.py: {e}")


def run_collector(func, **kwargs):
    if not project_id or not bucket_name:
        raise HTTPException(status_code=503, detail="GCP_PROJECT_ID and GCP_BUCKET_NAME must be set in .env")
    try:
        return func(**kwargs)
    except DefaultCredentialsError:
        raise HTTPException(status_code=503, detail="No Google credentials found, run: gcloud auth application-default login")
    except Forbidden:
        raise HTTPException(status_code=403, detail="This Google account cannot write to the bucket")
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    except GoogleAPIError as e:
        raise HTTPException(status_code=502, detail=f"Cloud Storage error: {e}")


class YearRange(BaseModel):
    start_year: int = Field(1999, ge=1999, le=THIS_YEAR)
    end_year: int = Field(2025, ge=1999, le=THIS_YEAR)
    overwrite: bool = False

    @model_validator(mode="after")
    def check_order(self):
        if self.start_year > self.end_year:
            raise ValueError("start_year must be <= end_year")
        return self


@app.get("/health")
def health():
    return {"status": "ok", "project_id": project_id, "bucket": bucket_name}


@app.post("/collect/epa")
def collect_epa(req: YearRange = YearRange()):
    epa = load_collector("epa_collector")
    result = run_collector(epa.collect_epa, start_year=req.start_year,
                           end_year=req.end_year, overwrite=req.overwrite)
    return {"source": "epa", **result}


@app.post("/collect/noaa")
def collect_noaa():
    noaa = load_collector("noaa_collector")
    result = run_collector(noaa.collect_stations)
    return {"source": "noaa", **result}


@app.post("/collect/festivals")
def collect_festivals():
    wiki = load_collector("wikipedia_scraper")
    func = getattr(wiki, "get_scraped_festivals", None)
    if func is None:
        raise HTTPException(status_code=501, detail="get_scraped_festivals() is not in wikipedia_scraper.py yet")
    result = run_collector(func, url=wiki.url)
    if isinstance(result, dict):
        return {"source": "festivals", **result}
    return {"source": "festivals", "result": result}
