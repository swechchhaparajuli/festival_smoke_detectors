import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transform import clean_epa

HEADER = ('"State Code","County Code","Site Num","Parameter Code","POC","Latitude","Longitude",'
          '"Pollutant Standard","Date Local","Event Type","Arithmetic Mean","AQI",'
          '"State Name","County Name"\n')


def make_zip(year, rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"daily_88101_{year}.csv", HEADER + "".join(rows))
    return buf.getvalue()


def test_clean_epa():
    rows = [
        '"06","037","1103","88101","1",34.06,-118.22,"PM25 24-hour 2012","2020-09-10","None",40.0,112,"California","Los Angeles"\n',
        '"06","037","1103","88101","1",34.06,-118.22,"PM25 Annual 2012","2020-09-10","None",40.0,,"California","Los Angeles"\n',
        '"06","037","1103","88101","3",34.06,-118.22,"PM25 24-hour 2012","2020-09-10","None",44.0,121,"California","Los Angeles"\n',
        '"06","037","1103","88101","1",34.06,-118.22,"PM25 24-hour 2012","2020-09-11","Included",150.0,200,"California","Los Angeles"\n',
        '"06","037","1103","88101","1",34.06,-118.22,"PM25 24-hour 2012","2020-09-11","Excluded",8.0,33,"California","Los Angeles"\n',
        '"01","003","0010","88101","1",30.49,-87.88,"PM25 24-hour 2012","2020-09-10","None",7.5,31,"Alabama","Baldwin"\n',
    ]
    df = clean_epa(make_zip(2020, rows))

    assert len(df) == 3
    assert df["site_id"].tolist() == ["010030010", "060371103", "060371103"]
    assert df["county_fips"].tolist() == ["01003", "06037", "06037"]
    assert str(df["date"].dtype).startswith("datetime64")

    la = df[df["site_id"] == "060371103"]
    la = la.set_index(la["date"].dt.strftime("%Y-%m-%d"))
    assert abs(la.loc["2020-09-10", "pm25"] - 41.333) < 0.01
    assert la.loc["2020-09-10", "aqi"] == 121
    assert la.loc["2020-09-11", "pm25"] == 150.0


def test_clean_epa_combines_years_and_filters_dates():
    row = '"01","003","0010","88101","1",30.49,-87.88,"PM25 24-hour 2012","{d}","None",7.5,31,"Alabama","Baldwin"\n'
    files = [make_zip(1998, [row.format(d="1998-12-31")]),
             make_zip(1999, [row.format(d="1999-01-01")])]
    df = clean_epa(files)
    assert df["date"].dt.year.tolist() == [1999]
