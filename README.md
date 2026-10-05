# HEAT AND SMOKE EXPOSURE AT MAJOR U.S. OUTDOOR MUSIC FESTIVALS
We're looking at heat and smoke exposure levels at outdoor music festivals held annually at around the same time in the U.S. We want to see which festivals are in the riskiest areas, and if that risk has been rising over the past few decades.

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Maaz Ullah Arshad | maazarshad | EPA data collector  + EPA data cleaning |
| Swechchha Parajuli | swechchhaparajuli | Github setup, Wikipedia scraper + streamlit app |
| ZHENGYANG DONG | id | storage.py + Cloud deployment |
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
- A GCP service account key with access to PROJECT/BUCKET/DATASET
- Any source API keys listed in the table below

### 1. Clone the repository
```bash
git clone https://github.com/swechchhaparajuli/festival_smoke_detectors.git
cd festival_smoke_detectors
```

### 2. Configure environment variables
Copy the example file and fill in your own values:

```bash
cp .env_template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_SERVICE_ACCOUNT_KEY` | Absolute path to your service account JSON | `/Users/you/.ssh/key.json` |
| `SOURCE_API_KEY` | Key for SOURCE NAME (free tier) | `abc123...` |
| `API_SERVICE_URL` | Where the web app reaches the API | `http://api-server:8000` |

### 4. How to call your endpoint
To start the API server,
```python
fastapi run mycode.py
```

```python
requests.post("http://localhost:8000/something", json=something)
```
Make sure it writes the data in the bucket.

---
## Repository Structure
```
.
├── fastapi/
├──── DOCKERFILE
├──── compose.yml ##this is so we can build/run containers to test by just one command idt if we've gone over it in class
├──── requirements.txt
├──── api.py
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
