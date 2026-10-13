## DASHBOARD
import json
import re

from google.oauth2 import service_account
from google.cloud import storage
import streamlit as st
import pandas as pd

from user_definition import (bucket_name, file_name_prefix, project_id,
                             service_account_file_path)


def retrieve_data_from_gcs(service_account_key: str,
                           project_id: str,
                           bucket_name: str,
                           file_name_prefix: str
                           ) -> dict:
    """
    Retrieve file (.json) contents from all files starting with
    'file_name_prefix' in "bucket_name" and return a dictionary
    including "results", "job_titles", and "company_dict".

    Args:
        service_account_key (str): path of service account key file (.json)
        project_id (str): GCP Project ID where the bucket is located
        bucket_name (str): bucket name
        file_name_prefix (str): prefix of files to retrieve data from
                                (Ex. "job_search")

    Returns:
        dict: {"results": combined "results" from every matching file,
               "job_titles": sorted unique "job_title"s across those files,
               "company_dict": combined "company_dict" across those files}
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id,
                            credentials=credentials)
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    #figure out what to do w/our data once it is out of GCS --------



    ### -------------------

    pass


if __name__ == '__main__':
    gcs_data = retrieve_data_from_gcs(service_account_file_path,
                                      project_id,
                                      bucket_name,
                                      file_name_prefix)
    festival_names = ", ".join(gcs_data["job_titles"])
    noaa_dictionary = gcs_data["company_dict"]
    epa_dictionary = gcs_data["company_dict"]
    data = pd.DataFrame(gcs_data["results"])

    st.title(f"Music Festivals")
    with st.sidebar:
        st.write("Filter by Season")

    # st.dataframe(filtered_df,
    #              hide_index=True,
    #              column_config={
    #                  "link": st.column_config.LinkColumn()})
