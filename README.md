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

We want to explore heat and smoke exposure at major U.S. music festivals to assess the riskiness of the locations where outdoor festivals are regularly held. We combine an inventory of major U.S. music festivals scraped from Wikipedia (including name, city) with NOAA NCEI daily weather summaries via API and EPA AirData daily PM2.5 concentration files to make a heat-smoke exposure profile for each festival's host city's full-year environmental data from 1999 to 2025. Which we can use to ask:

1. which combos historically have the riskiest weather conditions and
2. whether the conditions have shifted between the 1999-2008 and 2016-2025 periods.

---

## Data Sources and Integration Goal


### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [WIKIPEDIA](https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States) | Scraped | Index page organized by state, then festival name. Fields extracted: festival_name, city, state, venue_name, year_founded, genre, is_active Geography: 50 U.S. states | ~ monthly | None |
| 2 | [NOAA NCEI DAILY SUMMARIES](https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&dataTypes=TMAX&stations=USW00023234&startDate=2025-01-01&endDate=2025-01-05&format=json) | API | GHCN daily-summaries dataset, 1 record per station per day. Fields to extract: station, date, tmax | daily with ~ 1 day lag | None |
| 3 | [EPA AQS Pre-Generated Daily Data Files](https://aqs.epa.gov/aqsweb/airdata/download_files.html) | File-based | One row per monitor per day. Fields to extract: State/Country code, site number, latitude/longitude, local date, arithmetic mean (24 hour PM2.5 mean), AQI, state name, county name | Biannual | None|



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

The API uses Application Default Credentials (ADC). Streamlit uses a service account JSON key file, path is set via `GCP_SERVICE_ACCOUNT_KEY`

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
python -m pip install -r api/requirements.txt -r streamlit/requirements.txt
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
GCP_SERVICE_ACCOUNT_KEY=/absolute/path/to/service-account-key.json
```

| Variable | Description |
| --- | --- |
| `GCP_PROJECT_ID` | The exact Google Cloud project ID, not its display name. |
| `GCP_BUCKET_NAME` | The Cloud Storage bucket name,without `gs://` |
| `GCP_SERVICE_ACCOUNT_KEY` | Frontend read |

### 4. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project festival-smoke-detector
```

The API uses Application Default Credentials (ADC). Streamlit uses a service account JSON key file, path is set via `GCP_SERVICE_ACCOUNT_KEY`

### 5. Start FastAPI

Run from the `api/` folder:

```bash
cd api
fastapi dev main.py
```

Open http://127.0.0.1:8000/docs to view and test the endpoints.

### 6. Collect data

| Route | Source | Body | Saves to |
| --- | --- | --- | --- |
| `POST /collect/raw_epa` | EPA AQS daily PM2.5 (yearly zip files) | none | `raw/epa/<collection date>/daily_88101_<year>.zip` |
| `POST /collect/raw_noaa` | NOAA NCEI daily TMAX (API) | none, stations are set in `collectors/noaa_collector.py` | `raw/noaa/<collection date>/<station_id>.json` |
| `POST /collect/raw_festivals` | Wikipedia festival list (scraping) | none | `raw/wiki/<collection date>/festival_details.json` |
| `POST /extract_and_save` | NOAA, EPA, Wikipedia | none | `processed/festival_weather.parquet` |


#### EPA details
- Each year's zip is stored **as downloaded**: every U.S. monitor, every day, ~8 MB per year. Filtering to festival locations happens in `clean_epa()`.
- We store the zip rather than JSON because one year is ~740k rows (hundreds of MB as JSON). Read it back with `pd.read_csv(io.BytesIO(read_blob(path)), compression="zip", dtype={"State Code": str, "County Code": str})` to keep leading zeros in FIPS codes.


```bash
curl -X POST http://127.0.0.1:8000/collect/raw_epa
```

### 7. Start Streamlit

Open a new terminal in the project root and run:

```bash
source .venv/bin/activate
cd streamlit
streamlit run app.py
```

- Local app: http://localhost:8501
- Deployed app: https://webapp-1006870438808.us-west1.run.app
- Deployed API docs: https://api-server-1006870438808.us-west1.run.app/docs

### Adding or changing a collector
Only edit your own file in `api/collectors/`. `main.py` already has a route for each source that calls:
- `epa_collector.collect_epa()`
- `noaa_collector.collect_stations()`
- `wikipedia_scraper.get_scraped_festivals(WIKI_URL)`

Keep those function names, save files with `write_blob(path, data)` from `storage.py`, and return a dict (e.g. saved / failed lists). Then the route works with no change to `main.py`.

## Repository Structure

```text
.
├── api/
├──── Dockerfile
├──── requirements.txt
├──── main.py
├──── user_definition.py
├──── collectors/
├────── noaa_collector.py
├────── epa_collector.py
├────── wikipedia_scraper.py
├──── transform.py
├──── storage.py
├── streamlit/
├──── DOCKERFILE
├──── user_definition.py
├──── requirements.txt
├──── app.py
├── gcloud_command.sh
├── .env_template
├── LICENSE
└── README.md
```

Local `.env` and `.venv/` files are excluded from Git.

## Cloud Deployment and Data Pipeline

### GCP Configuration

- Project ID: `festival-smoke-detector`
- GCS bucket: `festival_smoke_detector`
- Region: `us-west1`
- API service: `api-server`
- Streamlit service: `webapp`

The API stores raw and processed data in GCS. The Streamlit service reads the processed data to display the charts.

### Deployment and Scheduled Jobs

Before deployment, configure the project, region, bucket and service account settings. The project must have billing enabled, and the service accounts must have the required permissions for deployment and GCS access.

Configure the local `.env` file and provide the path to a service account JSON key. Do not commit the key or `.env` to Git.

The deployment script supports these commands:

```bash
export LOCAL_KEY_FILE="/absolute/path/to/service-account-key.json"

./gcloud_command.sh bootstrap
./gcloud_command.sh api
./gcloud_command.sh web
./gcloud_command.sh scheduler
```

The four Cloud Scheduler jobs use the `America/Los_Angeles` time zone:

| Job | Schedule | API endpoint |
| --- | --- | --- |
| collect-epa | Daily at 00:00 | `/collect/raw_epa` |
| collect-noaa | Daily at 00:00 | `/collect/raw_noaa` |
| collect-festivals | Daily at 00:00 | `/collect/raw_festivals` |
| extract-and-save | Daily at 02:00 | `/extract_and_save` |

The processing job runs later to allow time for collection. The schedules do not automatically check whether all collection jobs succeeded.

### Data Processing and Current Limitations

The collection endpoints save raw EPA, NOAA and Wikipedia data to GCS. The `/extract_and_save` endpoint reads the latest collection folder for each source and calls the cleaning and joining functions.

Festival locations are mapped to NOAA stations using a predefined county FIPS-to-station mapping. The festival and NOAA tables are joined by station ID, then joined with EPA data by county FIPS and date.

The combined table is saved to:

`gs://festival_smoke_detector/processed/festival_weather.parquet`

Streamlit reads this file directly from GCS.

During testing on October 17, 2026, direct requests to the NOAA API returned HTTP 503, and NOAA collection could not be verified as successful at that time. Previously collected data remained available for the dashboard.
