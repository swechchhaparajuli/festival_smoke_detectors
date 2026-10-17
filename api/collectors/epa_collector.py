"""EPA AQS daily PM2.5 collector (Maaz).

Source: EPA AirData pre-generated files, one zip per year
        https://aqs.epa.gov/aqsweb/airdata/daily_88101_<YEAR>.zip
Method: file download from a stable URL (no API key, public data)

Each year's zip is stored exactly as downloaded (all US monitors, every day):
        raw/epa/<collection date YYYY-MM-DD>/daily_88101_<YEAR>.zip

Why the zip and not JSON: one year is ~740k rows. As JSON that is hundreds of MB per year;
the zip is ~8 MB, and pandas reads it directly (pd.read_csv(io.BytesIO(read_blob(path)))).
Filtering to festival locations happens later in clean_epa().
"""
import io
import zipfile
from datetime import date

import requests

from storage import list_blobs, write_blob

EPA_BASE_URL = "https://aqs.epa.gov/aqsweb/airdata"
PARAMETER_CODE = "88101"  # PM2.5 FRM/FEM mass
START_YEAR = 1999          # team decision: 1999-present (PM2.5 network starts 1999)
END_YEAR = 2025
REQUIRED_COLUMNS = {"State Code", "County Code", "Site Num", "Date Local", "Arithmetic Mean"}
HEADERS = {"User-Agent": "USF-course-project festival_smoke_detectors (EPA collector)"}


def file_name(year):
    return f"daily_{PARAMETER_CODE}_{year}.zip"


def find_existing(year):
    """Return the bucket path if this year's zip was collected on any earlier date, else None."""
    suffix = "/" + file_name(year)
    for name in list_blobs("raw/epa/"):
        if name.endswith(suffix):
            return name
    return None


def download_year(year):
    """Download one year's zip and check it really is the EPA CSV we expect. Returns bytes."""
    url = f"{EPA_BASE_URL}/{file_name(year)}"
    r = requests.get(url, headers=HEADERS, timeout=(10, 300))
    r.raise_for_status()
    content = r.content

    # EPA sometimes answers 200 with an HTML page (maintenance / missing year): reject it.
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            csv_name = f"daily_{PARAMETER_CODE}_{year}.csv"
            with archive.open(csv_name) as f:
                header = f.readline().decode("utf-8-sig").strip()
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"{url} did not return the expected zip/CSV ({e})") from e

    columns = {c.strip('"') for c in header.split(",")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"{url} is missing columns: {sorted(missing)}")
    return content


def collect_epa(start_year=START_YEAR, end_year=END_YEAR, overwrite=False, fetch_date=None):
    """Download each year's zip and upload it to GCS under raw/epa/.

    Years already in the bucket are skipped unless overwrite=True.
    A failed year is recorded and skipped so one bad year doesn't stop the rest.

    Returns: dict with "saved", "skipped_existing" and "failed" lists.
    """
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
            print(f"EPA {year}: FAILED - {e}")
            failed.append({"year": year, "error": str(e)})

    return {"saved": saved, "skipped_existing": skipped, "failed": failed}


if __name__ == "__main__":
    # Quick manual check without the API: python collectors/epa_collector.py (from fastapi/)
    print(collect_epa(2024, 2024))