## DASHBOARD
import json
import re

from google.oauth2 import service_account
from google.cloud import storage
import streamlit as st
import pandas as pd

import io

from user_definition import (bucket_name, file_name_prefix, project_id,
                             service_account_file_path)

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter",
           3: "Spring", 4: "Spring", 5: "Spring",
           6: "Summer", 7: "Summer", 8: "Summer",
           9: "Fall", 10: "Fall", 11: "Fall"}

# One row per festival (these columns repeat on every day in the joined table)
FESTIVAL_COLS = ["festival_id", "name", "city_name", "venue", "genre",
                 "status", "frequency", "year_founded", "years_active",
                 "latitude", "longitude", "fips", "station_id",
                 "station_distance_km", "station_far"]

# One row per festival per day
DAILY_COLS = ["date", "season", "tmax_c", "tmax_f", "pm25"]


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
    blobs = bucket.list_blobs(prefix=file_name_prefix)
    frames = [
        pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
        for blob in bucket.list_blobs(prefix=file_name_prefix)
        if blob.name.endswith(".parquet")
    ]
    if not frames:
        raise FileNotFoundError(
            f"No .parquet files found at gs://{bucket_name}/{file_name_prefix}")

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["date"].dt.month.map(SEASONS)

    festivals = (df.drop_duplicates("festival_id")[FESTIVAL_COLS]
                 .sort_values("name")
                 .reset_index(drop=True))

    # Festivals with no NOAA match have no date (left join), so drop those rows
    daily = df.dropna(subset=["date"])
    noaa_dict = {
        name: group[DAILY_COLS].reset_index(drop=True)
        for name, group in daily.groupby("name")
    }

    return {"df": df,
            "festivals": festivals,
            "festival_names": festivals["name"].dropna().tolist(),
            "noaa_dict": noaa_dict}



if __name__ == '__main__':
    gcs_data = retrieve_data_from_gcs(service_account_file_path,
                                      project_id,
                                      bucket_name,
                                      file_name_prefix)
    festival_names = ", ".join(gcs_data["festival_names"])
    noaa_dictionary = gcs_data["noaa_dict"]

    st.title(f"Music Festivals")
    with st.sidebar:
        season = st.selectbox("Filter by Season",
                          ["All", "Winter", "Spring", "Summer", "Fall"])
        festival = st.selectbox("Festival", gcs_data["festival_names"])
        
    st.dataframe(gcs_data["festivals"], hide_index=True)

    daily = noaa_dictionary[festival]
    if season != "All":
        daily = daily[daily["season"] == season]

    st.line_chart(daily, x="date", y=["tmax_f", "pm25"])
    

    # st.dataframe(filtered_df,
    #              hide_index=True,
    #              column_config={
    #                  "link": st.column_config.LinkColumn()})