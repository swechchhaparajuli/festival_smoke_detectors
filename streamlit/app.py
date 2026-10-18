import io
 
import pandas as pd
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account
 
from user_definition import (bucket_name, file_name_prefix, project_id,
                             service_account_file_path)


 
LABELS = {"name": "Festival",
          "pct_hot": "% hot days",
          "pct_smoky": "% smoky days",
          "pct_both": "% hot & smoky",
          "tmax_f": "Avg high (°F)",
          "pm25": "Avg PM2.5"}
 
@st.cache_data
def retrieve_data_from_gcs(service_account_key: str,
                           project_id: str,
                           bucket_name: str,
                           file_name_prefix: str
                           ) -> dict:
    """
    Read the joined festival/NOAA/EPA parquet file(s) under
    'file_name_prefix' and return:
        "festival_names": festival names
        "daily": daily weather at each festival's location, 1999-2025
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id, credentials=credentials)
    blobs = client.bucket(bucket_name).list_blobs(prefix=file_name_prefix)
    df = pd.concat([pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
                    for blob in blobs if blob.name.endswith(".parquet")],
                   ignore_index=True)
    # Festivals with no NOAA match have no date (left join), so drop them
    df = df.dropna(subset=["date"])
    df["year"] = pd.to_datetime(df["date"]).dt.year
 
    return {"festival_names": sorted(df["name"].unique()),
            "daily": df[["name", "year", "tmax_f", "pm25", "station_far"]]}

def summarize(daily, hot_f, smoky_pm, by):
    """% of days that were hot / smoky / both, plus averages.
    Days with missing data are skipped, not counted as safe."""
    hot = (daily["tmax_f"] >= hot_f).astype(float).where(
        daily["tmax_f"].notna())
    smoky = (daily["pm25"] >= smoky_pm).astype(float).where(
        daily["pm25"].notna())
    return (daily.assign(pct_hot=hot * 100, pct_smoky=smoky * 100,
                         pct_both=hot * smoky * 100)
            .groupby(by)[["pct_hot", "pct_smoky", "pct_both",
                          "tmax_f", "pm25"]]
            .mean().round(1).reset_index())

if __name__ == '__main__':
    gcs_data = retrieve_data_from_gcs(service_account_file_path,
                                      project_id,
                                      bucket_name,
                                      file_name_prefix)
    daily = gcs_data["daily"]
 
    st.title("Heat & Smoke Risk at U.S. Music Festivals")
    st.caption("NOAA daily highs and EPA PM2.5 at each festival's location, "
               "1999-2025.")
 
    with st.sidebar:
        hot_f = st.slider("Hot day: high of at least (°F)", 80, 105, 90)
        smoky_pm = st.slider("Smoky day: PM2.5 of at least (µg/m³)",
                             10, 100, 35)
        if st.checkbox("Hide festivals with a weather station "
                       "over 25 km away"):
            daily = daily[~daily["station_far"].astype(bool)]
        metric = st.radio("Measure",
                          ["pct_hot", "pct_smoky", "tmax_f", "pm25"],
                          format_func=LABELS.get)
 
    if daily.empty:
        st.info("No weather data to show.")
        st.stop()
 
    # ---- Q1: which locations are riskiest? ----
    st.header("1. Which festival locations are riskiest?")
    st.caption(f"{LABELS[metric]} at each festival's location, "
               "using every day from 1999-2025.")
    risk = summarize(daily, hot_f, smoky_pm, "name")
 
    st.bar_chart(risk, x="name", y=metric, horizontal=True)
    st.dataframe(risk.sort_values(metric, ascending=False)
                 .rename(columns=LABELS), hide_index=True)
 
    # ---- Q2: how have conditions changed? ----
    st.header("2. How have conditions changed since 1999?")
    st.caption(f"Change in {LABELS[metric]}: the 2016-2025 average minus "
               "the 1999-2008 average. Positive = riskier now.")
    yearly = summarize(daily, hot_f, smoky_pm, ["name", "year"])
 
    early = yearly[yearly["year"] <= 2008].groupby("name")[metric].mean()
    recent = yearly[yearly["year"] >= 2016].groupby("name")[metric].mean()
    change = (pd.DataFrame({"1999-2008": early,
                            "2016-2025": recent,
                            "Change": recent - early})
              .round(1).reset_index())
 
    st.bar_chart(change, x="name", y="Change", horizontal=True)
    st.dataframe(change.sort_values("Change", ascending=False)
                 .rename(columns=LABELS), hide_index=True)



