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


if __name__=="__main__":
    sample = [
        {"DATE": "1999-01-01", "STATION": "USW00023234", "TMAX": "  128"},
        {"DATE": "1999-01-02", "STATION": "USW00023234", "TMAX": "  156"},
        {"DATE": "1999-01-05", "STATION": "USW00023234", "TMAX": "  206"},
    ]

    final = clean_noaa(sample, '1999-01-01', '1999-01-06')