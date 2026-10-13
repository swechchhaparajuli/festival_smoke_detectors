import csv
import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.api_core.exceptions import Forbidden, GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Festival Smoke Detectors")


class EPARequest(BaseModel):
    year: int = Field(
        default=2025,
        ge=1999,
        le=datetime.now(timezone.utc).year,
    )
    state_code: str = Field(default="06", pattern=r"^\d{2}$")
    max_records: int = Field(default=1000, ge=1, le=10000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/collect/epa")
def collect_epa(options: EPARequest):
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    bucket_name = os.getenv("GCP_BUCKET_NAME", "").strip()

    if not project_id or not bucket_name:
        raise HTTPException(
            status_code=503,
            detail="Set GCP_PROJECT_ID and GCP_BUCKET_NAME in .env.",
        )

    source_url = (
        "https://aqs.epa.gov/aqsweb/airdata/"
        f"daily_88101_{options.year}.zip"
    )

    # EPA publishes annual ZIP archives containing daily PM2.5 CSV data.
    try:
        with requests.get(source_url, timeout=(10, 120)) as response:
            response.raise_for_status()
            archive_bytes = response.content
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not download the requested EPA annual file.",
        ) from exc

    records = []
    truncated = False
    csv_name = f"daily_88101_{options.year}.csv"

    # Keep original string values, including leading zeros in FIPS codes.
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            with archive.open(csv_name) as csv_file:
                reader = csv.DictReader(
                    io.TextIOWrapper(csv_file, encoding="utf-8-sig")
                )

                required_columns = {
                    "State Code",
                    "Date Local",
                    "Arithmetic Mean",
                }
                if not required_columns.issubset(reader.fieldnames or []):
                    raise ValueError("Required EPA columns are missing.")

                for row in reader:
                    if row["State Code"] != options.state_code:
                        continue

                    if len(records) == options.max_records:
                        truncated = True
                        break

                    records.append(row)

    except (
        zipfile.BadZipFile,
        KeyError,
        UnicodeError,
        csv.Error,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=502,
            detail="The EPA download was not in the expected CSV format.",
        ) from exc

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No EPA records matched the requested year and state.",
        )

    collected_at = datetime.now(timezone.utc)
    object_name = (
        f"raw/epa/{collected_at:%Y-%m-%d}/"
        f"daily_88101_{options.year}_{options.state_code}_"
        f"{uuid.uuid4().hex}.json"
    )

    document = {
        "source_url": source_url,
        "collected_at": collected_at.isoformat(),
        "year": options.year,
        "state_code": options.state_code,
        "max_records": options.max_records,
        "record_count": len(records),
        "truncated": truncated,
        "records": records,
    }

    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Create a new object; do not overwrite an existing object.
        blob.upload_from_string(
            json.dumps(document, ensure_ascii=False),
            content_type="application/json",
            if_generation_match=0,
            timeout=120,
        )
    except DefaultCredentialsError as exc:
        raise HTTPException(
            status_code=503,
            detail="Run gcloud auth application-default login.",
        ) from exc
    except Forbidden as exc:
        raise HTTPException(
            status_code=403,
            detail="Your Google account cannot write to the configured bucket.",
        ) from exc
    except GoogleAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail="Cloud Storage upload failed. Check the project and bucket.",
        ) from exc

    return {
        "status": "uploaded",
        "year": options.year,
        "state_code": options.state_code,
        "record_count": len(records),
        "truncated": truncated,
        "gcs_uri": f"gs://{bucket_name}/{object_name}",
        "source_url": source_url,
    }