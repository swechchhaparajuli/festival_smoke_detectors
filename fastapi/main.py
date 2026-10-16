"""Festival Smoke Detectors - data collection API.

One POST route per data source; each route calls that source's collector and the
collector saves raw files to the team bucket under raw/<source>/<YYYY-MM-DD>/...

    POST /collect/epa        EPA PM2.5 yearly zips          (collectors/epa_collector.py, Maaz)
    POST /collect/noaa       NOAA daily TMAX per station    (collectors/noaa_collector.py, Erin)
    POST /collect/festivals  Wikipedia festival list        (collectors/wikipedia_scraper.py, Swechchha)

Run locally (from the fastapi/ folder):
    python -m uvicorn main:app --reload
    then open http://127.0.0.1:8000/docs

Adding/changing a source: edit only your collector file. Its route below just calls
your function, so you shouldn't need to touch this file.
"""
import importlib
import sys
from datetime import date
from pathlib import Path

# Make imports work no matter where uvicorn is started from:
#   fastapi/ -> storage.py, transform.py, collectors/
#   repo root -> user_definition.py
HERE = Path(__file__).resolve().parent
for folder in (HERE.parent, HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from fastapi import FastAPI, HTTPException  # noqa: E402
from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound  # noqa: E402
from google.auth.exceptions import DefaultCredentialsError  # noqa: E402
from pydantic import BaseModel, Field, model_validator  # noqa: E402

from user_definition import bucket_name, project_id  # noqa: E402

THIS_YEAR = date.today().year

app = FastAPI(
    title="Festival Smoke Detectors API",
    description="Collects raw festival (Wikipedia), heat (NOAA) and smoke (EPA) data into the team GCS bucket.",
    version="1.0.0",
)


# ---------- helpers ----------

def load_collector(module_name):
    """Import a collector only when its route is called.

    If one teammate's collector has a bug, only that route fails;
    the rest of the app (and /docs) keeps working.
    """
    try:
        return importlib.import_module(f"collectors.{module_name}")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"collectors/{module_name}.py could not be loaded: {e}")


def run_collector(func, **kwargs):
    """Run a collector and turn common GCP problems into readable errors."""
    if not project_id or not bucket_name:
        raise HTTPException(status_code=503,
                            detail="Set GCP_PROJECT_ID and GCP_BUCKET_NAME in .env (see .env_template).")
    try:
        return func(**kwargs)
    except DefaultCredentialsError:
        raise HTTPException(status_code=503,
                            detail="No Google credentials. Run: gcloud auth application-default login")
    except Forbidden:
        raise HTTPException(status_code=403,
                            detail="Your Google account cannot write to the bucket. Ask for Storage Object Admin.")
    except NotFound:
        raise HTTPException(status_code=404,
                            detail=f"Bucket '{bucket_name}' not found. Check GCP_BUCKET_NAME in .env.")
    except GoogleAPIError as e:
        raise HTTPException(status_code=502, detail=f"Cloud Storage error: {e}")


# ---------- request bodies ----------

class YearRange(BaseModel):
    start_year: int = Field(1999, ge=1999, le=THIS_YEAR, description="First year to collect (team range: 1999-present)")
    end_year: int = Field(2025, ge=1999, le=THIS_YEAR, description="Last year to collect")
    overwrite: bool = Field(False, description="Re-download years already in the bucket")

    @model_validator(mode="after")
    def check_order(self):
        if self.start_year > self.end_year:
            raise ValueError("start_year must be <= end_year")
        return self


# ---------- routes ----------

@app.get("/health", tags=["Health"])
def health():
    """Check the API is running and which project/bucket it will write to."""
    return {"status": "ok", "project_id": project_id, "bucket": bucket_name}


@app.post("/collect/epa", tags=["Collectors"])
def collect_epa(req: YearRange = YearRange()):
    """EPA AQS daily PM2.5: download one zip per year and store it in raw/epa/.

    Tip: each year is ~8 MB and takes a few seconds; request about 5-10 years at a time.
    """
    epa = load_collector("epa_collector")
    result = run_collector(epa.collect_epa, start_year=req.start_year,
                           end_year=req.end_year, overwrite=req.overwrite)
    return {"source": "epa", **result}


@app.post("/collect/noaa", tags=["Collectors"])
def collect_noaa():
    """NOAA NCEI daily summaries: fetch TMAX for each station in STATIONS and store in raw/noaa/."""
    noaa = load_collector("noaa_collector")
    result = run_collector(noaa.collect_stations)
    return {"source": "noaa", **result}


@app.post("/collect/festivals", tags=["Collectors"])
def collect_festivals():
    """Wikipedia: scrape the U.S. music festival list and store it in raw/festivals/."""
    wiki = load_collector("wikipedia_scraper")
    func = getattr(wiki, "collect_festivals", None)
    if func is None:
        raise HTTPException(status_code=501,
                            detail="Not implemented yet: add collect_festivals() to collectors/wikipedia_scraper.py")
    result = run_collector(func)
    return {"source": "festivals", **result} if isinstance(result, dict) else {"source": "festivals", "result": result}
