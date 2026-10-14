# HEAT AND SMOKE EXPOSURE AT MAJOR U.S. OUTDOOR MUSIC FESTIVALS
We're looking at heat and smoke exposure levels at outdoor music festivals held annually at around the same time in the U.S. We want to see which festivals are in the riskiest areas, and if that risk has been rising over the past few decades.

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Maaz Ullah Arshad | maazarshad | EPA data collector  + EPA data cleaning |
| Swechchha Parajuli | swechchhaparajuli | Github setup, Wikipedia scraper + streamlit app |
| ZHENGYANG DONG | mechanic2718 | GCP setup, initial FastAPI collector, shared storage, and deployment|
| ERIN LUKOW | erinnalani | NOAA data collector + NOAA data cleaning |
---

## Problem Statement

We want to explore heat and smoke exposure at major U.S. music festivals to assess the riskiness of the locations where outdoor festivals are regularly held. We combine an inventory of major U.S. music festivals scraped from Wikipedia (including name, city, and recurring annual date) with NOAA NCEI daily weather summaries via API and EPA AirData daily PM2.5 concentration files to make a heat-smoke exposure profile for each festival's location and time of year. Because each festival recurs at roughly the same week each year, they can be associated with a specific location-date combo, which we can use to ask:

1. which combos historically have the riskiest weather conditions and
2. whether the conditions have shifted in the last 30 years.

---

## Data Sources and Integration Goal
- Follow the direction given in the 1st assignment

### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [WIKIPEDIA](https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States) | Scraped | Index page organized by state, then festival name. Fields extracted: festival_name, city, state, venue_name, recurring month, day_window, year_founded, genre, is_active Geography: 50 U.S. states | ~ monthly | None |
| 2 | [NOAA NCEI DAILY SUMMARIES](https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&dataTypes=TMAX,TMIN,PRCP&stations=USW00023234&startDate=2025-01-01&endDate=2025-01-05&format=json) | API | GHCN daily-summaries dataset, 1 record per station per day. Fields to extract: station, date, tmax/tmin (t=temperature), PRCP (int), TAVG, AWND (int) | daily with ~ 1 day lag | None |
| 3 | [EPA AQS Pre-Generated Daily Data Files](https://aqs.epa.gov/aqsweb/airdata/download_files.html) | File-based | One row per monitor per day. Fields to extract: State/Country code, site number, latitude/longitude, local date, arithmetic mean (24 hour PM2.5 mean), AQI, state name, county name | Biannual | None|

Note: If we need a key, say which environment variable holds it and make sure that variable also appears in the .env_template

### Integration Goal
1. Wikipedia supplies a festival index. It tells us which festivals exist, where they occur, and when. No measurements are taken from here.
2. NOAA NCEI supplies heat measurements (daily maximum temperature) at the festival locations
3. EPA AQS supplies the smoke and particulate measurements at the festival locations. We’re using PM2.5 because we’re interested in smoke particulates. There are no monitors inside venues to measure larger particulates like dust kicked up by festival goers.
---

## Setup Instructions (Locally)

### Prerequisites
- Python 3.11+
- Git.
- Google Cloud CLI (`gcloud`).
- A Google account with access to the team project and permission to upload objects to the bucket.

Project ID: `festival-smoke-detector`  
Bucket name: `festival_smoke_detector`

The application uses Application Default Credentials (ADC). A service account JSON key is not required for local development.

### 1. Clone the repository
```bash
git clone https://github.com/swechchhaparajuli/festival_smoke_detectors.git
cd festival_smoke_detectors
```

### 2. Create a virtual environment and install dependencies

The following commands are for macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the template:

```bash
cp .env_template .env
```

Open `.env` and fill in:

```dotenv
GCP_PROJECT_ID=festival-smoke-detector
GCP_BUCKET_NAME=festival_smoke_detector
```

| Variable | Description |
| --- | --- |
| `GCP_PROJECT_ID` | The exact Google Cloud project ID, not its display name. |
| `GCP_BUCKET_NAME` | The Cloud Storage bucket name,without `gs://` |

### 4. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project festival-smoke-detector
```

Use the account that has been granted access to the team project and bucket. The Python application uses Application Default Credentials, so a shared service account key file is not required.

### 5. Start FastAPI

From the `fastapi/` folder:

```bash
cd fastapi
fastapi dev main.py
```

`fastapi dev` restarts the server when code changes. Use `fastapi run main.py` to run it without auto-reload (this is what the Dockerfile uses).

Open http://127.0.0.1:8000/docs to test the endpoints. http://127.0.0.1:8000/health should show the project ID and bucket name from `.env`.

### 6. Collect data

| Route | Source | Body | Saves to |
| --- | --- | --- | --- |
| `POST /collect/epa` | EPA AQS daily PM2.5 (yearly zip files) | `{"start_year": 1999, "end_year": 2025, "overwrite": false}`, all optional | `raw/epa/<collection date>/daily_88101_<year>.zip` |
| `POST /collect/noaa` | NOAA NCEI daily TMAX (API) | none, stations are set in `collectors/noaa_collector.py` | `raw/noaa/<collection date>/<station_id>.json` |
| `POST /collect/festivals` | Wikipedia festival list (scraping) | none | `raw/festivals/...`, returns 501 until `get_scraped_festivals()` exists |

Each route returns what was saved, skipped and failed.

#### EPA
- Each year's zip is stored as downloaded (all U.S. monitors, every day, about 8 MB per year).
- We keep the zip instead of JSON because one year is about 740k rows, which would be hundreds of MB as JSON.
- Years already in the bucket are skipped unless `"overwrite": true`.
- 1999-2025 has already been collected to `raw/epa/2026-10-13/`.

`clean_epa()` in `transform.py` turns the zips into one row per monitoring site per day:

```python
from storage import list_blobs, read_blob
from transform import clean_epa

paths = [p for p in list_blobs("raw/epa/") if p.endswith(".zip")]
epa_df = clean_epa([read_blob(p) for p in paths])
```

Columns: `site_id`, `county_fips`, `state_name`, `county_name`, `latitude`, `longitude`, `date`, `pm25` (µg/m³), `aqi`. `site_id` and `county_fips` are strings so leading zeros are kept.

### 7. Run the tests

No internet or GCP access needed:

```bash
cd fastapi
python -m pytest -q
```

### Adding or changing a collector
`main.py` has a route for each source that calls:
- `epa_collector.collect_epa(start_year, end_year, overwrite)`
- `noaa_collector.collect_stations()`
- `wikipedia_scraper.get_scraped_festivals(url)`

Keep those function names, save files with `write_blob(path, data)` from `storage.py`, and return a dict. The route then works without changing `main.py`.

## Repository Structure

```text
.
├── fastapi/
├──── DOCKERFILE
├──── compose.yml ##this is so we can build/run containers to test by just one command idt if we've gone over it in class
├──── requirements.txt
├──── main.py
├──── tests/
├──── collectors/
├────── noaa_collector.py
├────── epa_collector.py
├────── wikipedia_scraper.py
├──── transform.py 
├──── storage.py 
├── streamlit/
├──── DOCKERFILE
├──── compose.yml ##this is so we can build/run containers to test by just one command idt if we've gone over it in class
├──── requirements.txt
├──── app.py
├── gcloud_command.sh
├── .env
├── LICENSE
└── README.md
```

Local `.env` and `.venv/` files are excluded from Git.
