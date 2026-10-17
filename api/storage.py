from google.cloud import storage
from user_definition import project_id, bucket_name

def write_blob(path, data):
    client = storage.Client(project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type="application/json")