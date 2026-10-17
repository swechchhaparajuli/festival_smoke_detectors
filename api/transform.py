import pandas as pd
import io
import re
from datetime import date


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

WIKI_COLIMNS = {
    "name":"festival name",
    "longitude": "longitude", 
    "latitude": "latitude", 
    "city_name": "City name | can be empty",
    "fips": "FIPS -- join key",
    "venue": "Venue name | Empty",
    "year_founded": "Year | Empty",
    "genre": "Genre | Empty",
    "status": "Active or Not",
    "frequency": "When it happens",
    "years_active": "[List of years calculated] | Empty"
}

def clean_status():
    pass

# Matches: "1999" | "2001–2019" | "2011–19" | "2022–" | "1988 to present" | "2013- current"
# AI for REGEXP
YEAR_RANGE = re.compile(
    r"(\d{4})(\s*(?:–|—|-|to)\s*(\d{4}|\d{2}(?!\d)|present|current|now)?)?"
)

CURRENT_YEAR = date.today().year

def parse_years_active(text):
    if not text:
        return []
    text = str(text).lower()


    cancelled = set()
    if "cancel" in text:
        text, _, tail = text.partition("cancel")
        cancelled = {int(y) for y in re.findall(r"\d{4}", tail)}
 
    years = set()
    for start, dash, end in YEAR_RANGE.findall(text):
        start = int(start)
        if not dash:
            end = start
        elif not end or not end.isdigit():
            end = CURRENT_YEAR
        elif len(end) == 2:
            end = start // 100 * 100 + int(end)
        else:
            end = int(end)
        years.update(range(start, min(end, CURRENT_YEAR) + 1))
 
    return sorted(years - cancelled)


def clean_wiki(records):
    """
    Cleans Wiki data -- adds proper years active in list format if possible or leaves empty
    Removes if FIPS not in data
    """
    cleaned = []
    for r in records:
        fips = r.get("fips")
        if not fips:
            continue
 
        years = parse_years_active(r.get("years_active"))
        founded = r.get("year_founded")
 
        cleaned.append({
            "name":r.get("Name"),
            "longitude": r.get("longitude"),
            "latitude": r.get("latitude"),
            "city_name": r.get("city_name"),
            "fips": fips.zfill(5),
            "venue": r.get("venue"),
            "year_founded": int(founded) if founded and founded.isdigit()
                            else (years[0] if years else None),
            "genre": r.get("genre"),
            "status": r.get("is_active:"),
            "frequency": r.get("frequency"),
            "years_active": years or None,
        })

    return cleaned




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
    data_df = data_df.merge(epa, left_on=["fips", "date"],
                        right_on=["county_fips", "date"], how="left")

    return data_df