import pandas as pd
import io

from storage import read_blob, list_blobs, write_blob


START_DATE = '1999-01-01'
END_DATE = '2025-12-31'

EPA_COLUMNS = {
    "State Code": "state_code",
    "County Code": "county_code",
    "Date Local": "date",
    "Sample Duration": "sample_duration",
    "Arithmetic Mean": "pm25",
    "State Name": "state_name",
    "County Name": "county_name",
}

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

def clean_epa():
    """"
    Cleans epa zip files pulled using epa.py.

    Aggregates all values for one site to one row per county per day,
    allowing join with festival table. Counties with several monitor
    readings are averaged.

    Returns: df with the columns: [county_fips, date, pm25, state_name,
    county_name]. Each row = 1 county on 1 day.

    """
    if isinstance(zip_files, bytes):
        zip_files = [zip_files]

    yearly_tables = []
    for content in zip_files:
        raw_df = pd.read_csv(
            io.BytesIO(content),
            compression="zip",
            usecols=list(EPA_COLUMNS),
            dtype={"State Code": str, "County Code": str},
        )
        df = raw_df.rename(columns=EPA_COLUMNS)

        # Create county fips code: 2 digit state code + 3 digit county code
        df["county_fips"] = (df["state_code"].str.zfill(2)
                              + df["county_code"].str.zfill(3))

        df["date"] = pd.to_datetime(df["date"])

        # Average across every monitor for that day
        daily = (
            df.groupby(["county_fips", "date"], as_index=False)
            .agg(pm25=("pm25", "mean"),
                 state_name=("state_name", "first"),
                 county_name=("county_name", "first"))
        )
        yearly_tables.append(daily)

    epa_df = pd.concat(yearly_tables, ignore_index=True)
    in_range = epa_df["date"].between(start_date, end_date)
    epa_df = epa_df[in_range].sort_values(["county_fips", "date"])

    return epa_df.reset_index(drop=True)[
        ["county_fips", "date", "pm25", "state_name", "county_name"]
    ]

def join_data(noaa, epa, festivals):
    # Join all cleaned data together into one dataframe
    data_df = festivals.merge(noaa, on=["station_id", "date"], how="left")
    data_df = df.merge(epa, left_on=["fips", "date"],
                        right_on=["county_fips", "date"], how="left")

    return data_df

