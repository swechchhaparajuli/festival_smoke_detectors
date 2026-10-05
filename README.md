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

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs to view and test the endpoints. Keep the server running while making requests.

### 6. Collect EPA data

In the API documentation, select `POST /collect/epa`, click **Try it out**, and submit:

```json
{
  "year": 2025,
  "state_code": "06",
  "max_records": 1000
}
```

Alternatively, run this in a second terminal:

```bash
curl -X POST http://127.0.0.1:8000/collect/epa \
  -H "Content-Type: application/json" \
  -d '{"year":2025,"state_code":"06","max_records":1000}'
```

This request downloads the EPA annual PM2.5 file and saves up to 1,000 California records. `"06"` is California's state FIPS code.

The response includes the number of saved records and a `gcs_uri` pointing to the uploaded JSON:

```text
gs://festival_smoke_detector/raw/epa/<UTC collection date>/<filename>.json
```

The JSON contains the original record values and collection metadata. If `truncated` is `true`, additional matching records exist beyond the requested limit.

The folder date is the UTC collection date, not the data year. Open the returned object in Cloud Storage to verify its contents.

This workflow was tested locally using the request above. The API returned HTTP 200, and the uploaded JSON data was inspected in the team bucket.

## Repository Structure

```text
.
├── main.py             # FastAPI application and EPA collector
├── requirements.txt    # Python dependencies
├── .env_template       # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

Local `.env` and `.venv/` files are excluded from Git.
