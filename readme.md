# HEAT AND SMOKE EXPOSURE AT MAJOR U.S. OUTDOOR MUSIC FESTIVALS
Add a brief description of your project, in a sentence or two.

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Maaz Ullah Arshad | maazarshad | EPA collector + transform.py |
| Swechchha Parajuli | swechchhaparajuli | Github setup, Wikipedia scraper + streamlit app |
| Erin Lukow | erinnalani | README content, contract finalization, NOAA + storage.py |
| Zhengyang Dong  | mechanic2718 | GCP Setup, Dockerfiles + gcloud_command.sh + Cloud Run & Cloud Scheduler setup|
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
| 1 | [NAME](https://exact-url) | API | rows, columns, time range, geography — in your own words | daily / monthly / static | free key, 100 req/day |
| 2 | [NAME](https://exact-url) | File | ... | ... | none |
| 3 | [NAME](https://exact-url) | Scraped | ... | ... | `robots.txt` checked DATE |

Note: If we need a key, say which environment variable holds it and make sure that variable also appears in the .env

### Integration Goal
- Follow the direction given in the 1st assignment

---

## Setup Instructions (Locally)

### Prerequisites
- Python 3.11+
- A GCP service account key with access to PROJECT/BUCKET/DATASET
- Any source API keys listed in the table below

### 1. Clone the repository
```bash
git clone https://github.com/swechchhaparajuli/festival_smoke_detectors.git
cd REPO
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
├──── requirements.txt
├──── api.py
├──── collectors/
├────── noaa_collector.py
├────── epa_collector.py
├────── wikipedia_scraper.py
├── streamlit/
├──── DOCKERFILE
├──── requirements.txt
├──── app.py
├── gcloud_command.sh
├── .env
├── LICENSE
└── README.md
```
