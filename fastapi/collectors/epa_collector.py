import io
import zipfile
from datetime import date

import requests

from storage import list_blobs, write_blob

BASE_URL = "https://aqs.epa.gov/aqsweb/airdata"
PARAMETER_CODE = "88101"
START_YEAR = 1999
END_YEAR = 2025
REQUIRED_COLUMNS = {"State Code", "County Code", "Site Num", "Date Local", "Arithmetic Mean"}
HEADERS = {"User-Agent": "USF-course-project festival_smoke_detectors"}


def file_name(year):
    return f"daily_{PARAMETER_CODE}_{year}.zip"


def find_existing(year):
    for name in list_blobs("raw/epa/"):
        if name.endswith("/" + file_name(year)):
            return name
    return None


def download_year(year):
    url = f"{BASE_URL}/{file_name(year)}"
    r = requests.get(url, headers=HEADERS, timeout=(10, 300))
    r.raise_for_status()

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            with archive.open(f"daily_{PARAMETER_CODE}_{year}.csv") as f:
                header = f.readline().decode("utf-8-sig").strip()
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"{url} is not the expected zip file: {e}")

    columns = {c.strip('"') for c in header.split(",")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"{url} is missing columns {sorted(missing)}")
    return r.content


def collect_epa(start_year=START_YEAR, end_year=END_YEAR, overwrite=False, fetch_date=None):
    fetch_date = fetch_date or date.today()
    saved, skipped, failed = [], [], []

    for year in range(start_year, end_year + 1):
        if not overwrite:
            existing = find_existing(year)
            if existing:
                skipped.append({"year": year, "path": existing})
                continue
        try:
            content = download_year(year)
            path = f"raw/epa/{fetch_date}/{file_name(year)}"
            uri = write_blob(path, content, content_type="application/zip")
            saved.append({"year": year, "gcs_uri": uri, "bytes": len(content)})
        except Exception as e:
            failed.append({"year": year, "error": str(e)})

    return {"saved": saved, "skipped_existing": skipped, "failed": failed}


if __name__ == "__main__":
    print(collect_epa(2024, 2024))
