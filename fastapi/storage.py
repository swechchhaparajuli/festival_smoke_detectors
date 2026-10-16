"""Shared Cloud Storage helpers (agreed in the team contract).

write_blob(path, data)   # save to bucket
read_blob(path)          # read back
list_blobs(prefix)       # find everything under e.g. raw/noaa/

Credentials come from Application Default Credentials
(`gcloud auth application-default login` locally, the service account on Cloud Run).
"""
from functools import lru_cache

from google.cloud import storage
from user_definition import project_id, bucket_name


@lru_cache
def _bucket():
    client = storage.Client(project_id)
    return client.bucket(bucket_name)


def write_blob(path, data, content_type="application/json"):
    """Upload text or bytes to `path` in the bucket. Returns the gs:// URI."""
    blob = _bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket_name}/{path}"


def read_blob(path):
    """Download the object at `path` and return its contents as bytes."""
    return _bucket().blob(path).download_as_bytes()


def list_blobs(prefix):
    """Return the names of every object whose path starts with `prefix`."""
    return [blob.name for blob in _bucket().client.list_blobs(bucket_name, prefix=prefix)]
