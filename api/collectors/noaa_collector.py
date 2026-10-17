import requests
from datetime import date
import json

from user_definition import *

from storage import write_blob


header = {"User-Agent": "USF-course-project (enlukow@usfca.edu)"}
url = "https://www.ncei.noaa.gov/access/services/data/v1"

STATIONS = ["USC00012172", "USC00044259", "USC00046399", "USC00087826", "USC00080236",
            "USW00013873", "USW00053819", "USW00014933", "USC00148259", "USC00155694",
            "USW00012930", "USC00186350", "USC00205567", "USC00200032", "USC00218450",
            "USW00013893", "USW00013897", "USW00014920"]
START_DATE = "1999-01-01"
END_DATE = "2025-12-31"

def get_station_data(station_id: str, start_date=START_DATE, end_date=END_DATE):
    """Access NOAA data via API and fetch daily TMAX for
    indicated dates.

    Returns: A list of dicts, one per day per station.
    e.g.
    [{'DATE': '2025-07-01', 'STATION': 'USW00023234', 'TMAX': '  206'},
    {'DATE': '2025-07-02', 'STATION': 'USW00023234', 'TMAX': '  206'}]
    """

    # Access NOAA API
    r = requests.get(
        url,
        params={
            "dataset": "daily-summaries",
            "dataTypes": "TMAX",
            "stations": station_id,
            "startDate": start_date,
            "endDate": end_date,
            "format": "json",
            },
        headers=header,
    )
    # Handle error from NOAA
    r.raise_for_status()
    records = r.json()

    # print(r.json()[:3])

    # Handle missing days: NOAA omits days that don't have data
    # rather than showing "null"
    if not records:
        raise ValueError(
            f"No records found for station {station_id}.\
            Verify station id against ghcnd-inventory.txt.\
            to ensure there's a TMAX listed for this station."
        )
    return records

def collect_stations(fetch_date=None):
    """Fetch all station data and upload to GCS /raw.

    Failed fetches are recorded and skipped, so the
    pipeline isn't interrupted. Scheduled job will
    return data it could find and report fetch
    attempts that failed.

    Returns: dict containing list of "successful"
    and "failed" calls. """

    failed = []
    successful = []

    fetch_date = fetch_date or date.today()

    for station_id in STATIONS:
        try:
            records = get_station_data(station_id)

        # If failure, record failure and skip station
        except Exception as e:
            print(f"{station_id}: FAILED - {e}")
            failed.append({"station": station_id, "error": str(e)})
            continue

        # Upload to GCS
        gcs_path = f"raw/noaa/{fetch_date}/{station_id}.json"
        write_blob(gcs_path, json.dumps(records))

        # Record success
        successful.append(
            {"station": station_id, "path": gcs_path, "records": len(records)}
        )

    return {"successful": successful, "failed": failed}

# Test
if __name__=="__main__":
    records = get_station_data(STATIONS[0])
    print(f"Num of records: {len(records)}\
          Expected # or records for 1999-2025: ~ 9,800")
    print(f"First: {records[0]}\nLast: {records[-1]}")
