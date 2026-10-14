import io

import pandas as pd

START_DATE = '1999-01-01'
END_DATE = '2025-12-31'

def clean_noaa(records, start_date=START_DATE, end_date=END_DATE):
    """
    Cleans NOAA data pulled using noaa.py. Missing
    days are omitted by NOAA, which upsets the
    percentages of hot days. clean_noaa adds them
    back in and fills value with NaN.

    Returns: Dataframe with columns: station_id,
        date, tmax_c, and tmax_f. Each row represents
        one station on one calendar day.
    """
    # Init df
    raw_df = pd.DataFrame(records)
    converted_tmax = pd.to_numeric(raw_df["TMAX"]) / 10.0

    # Build final df
    noaa_df = pd.DataFrame({
        "station_id": raw_df["STATION"],
        "date": pd.to_datetime(raw_df["DATE"]),
        "tmax_c": converted_tmax,
        "tmax_f": converted_tmax * (9 / 5) + 32,
    })

    # Reindex : missing days are omitted by NOAA
    all_calendar_dates = pd.date_range(start_date, end_date)

    station_tables = []
    for station_id, rows in noaa_df.groupby("station_id"):
        # Add all calendar dates to df
        filled_df = rows.set_index("date").reindex(all_calendar_dates)
        filled_df["station_id"] = station_id

        # Fix column labels
        filled_df.index.name = "date"
        station_tables.append(filled_df.reset_index())

    # Stack station tables back into 1 df
    final_df = pd.concat(station_tables, ignore_index=True)

    return final_df


EPA_COLUMNS = {
    "State Code": "state_code",
    "County Code": "county_code",
    "Site Num": "site_num",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Date Local": "date",
    "Event Type": "event_type",
    "Arithmetic Mean": "pm25",
    "AQI": "aqi",
    "State Name": "state_name",
    "County Name": "county_name",
}


def clean_epa(zip_files, start_date=START_DATE, end_date=END_DATE):
    if isinstance(zip_files, bytes):
        zip_files = [zip_files]

    yearly_tables = []
    for content in zip_files:
        raw_df = pd.read_csv(
            io.BytesIO(content),
            compression="zip",
            usecols=list(EPA_COLUMNS),
            dtype={"State Code": str, "County Code": str,
                   "Site Num": str, "Event Type": str},
        )
        df = raw_df.rename(columns=EPA_COLUMNS)
        df = df[df["event_type"] != "Excluded"].copy()

        df["state_code"] = df["state_code"].str.zfill(2)
        df["county_code"] = df["county_code"].str.zfill(3)
        df["site_num"] = df["site_num"].str.zfill(4)
        df["county_fips"] = df["state_code"] + df["county_code"]
        df["site_id"] = df["county_fips"] + df["site_num"]
        df["date"] = pd.to_datetime(df["date"])

        daily = (
            df.groupby(["site_id", "date"], as_index=False)
            .agg(county_fips=("county_fips", "first"),
                 state_name=("state_name", "first"),
                 county_name=("county_name", "first"),
                 latitude=("latitude", "first"),
                 longitude=("longitude", "first"),
                 pm25=("pm25", "mean"),
                 aqi=("aqi", "max"))
        )
        yearly_tables.append(daily)

    epa_df = pd.concat(yearly_tables, ignore_index=True)
    in_range = epa_df["date"].between(start_date, end_date)
    epa_df = epa_df[in_range].sort_values(["site_id", "date"])

    return epa_df.reset_index(drop=True)[
        ["site_id", "county_fips", "state_name", "county_name",
         "latitude", "longitude", "date", "pm25", "aqi"]
    ]


if __name__=="__main__":
    sample = [
        {"DATE": "1999-01-01", "STATION": "USW00023234", "TMAX": "  128"},
        {"DATE": "1999-01-02", "STATION": "USW00023234", "TMAX": "  156"},
        {"DATE": "1999-01-05", "STATION": "USW00023234", "TMAX": "  206"},
    ]

    final = clean_noaa(sample, '1999-01-01', '1999-01-06')