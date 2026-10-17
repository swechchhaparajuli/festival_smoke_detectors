from google.cloud import storage
from user_definition import project_id, bucket_name
from functools import lru_cache

@lru_cache # Looked this up to know how to cache credentials
def get_bucket():
    client = storage.Client(project_id)
    return client.bucket(bucket_name)

def write_blob(path, data):
    client = storage.Client(project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type="application/json")

def read_blob(path):
    return get_bucket().blob(path).download_as_bytes()

def list_blobs(prefix):
    return [blob.name for blob in get_bucket().client.list_blobs(bucket_name, prefix=prefix)]