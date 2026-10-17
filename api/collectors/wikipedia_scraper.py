# SWECHCHHA'S CODE HERE

# URL for wiki major music festivals: 
# https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States

# pseudocode: 
#     for each item in the list extract url 
#         enter wikipedia site per url async ?? 
#             load required info like city name, dates, years only if some required fields exist else ignore


from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import addfips
from datetime import date
import json

from storage import *


fetch_date = date.today()


af = addfips.AddFIPS()

# had a problem with rate limiting on this 
def _call(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def each_festival(link, us_state):
    response = requests.get(link, headers=headers, timeout=30)
    f_html_text = response.text
    f_soup = BeautifulSoup(f_html_text, "html.parser")
    lat, lon = None, None
    info = {}

    geo = f_soup.select_one("span.geo")
    if geo:
        lat, lon = (float(x) for x in geo.get_text().split(";"))


    if len(f_soup.select(".infobox"))>0:
        info_box = f_soup.select(".infobox")[0]
        for row in info_box.select("tr"):
            label = row.select_one(".infobox-label")
            data = row.select_one(".infobox-data")
            if label and data: 
                info[" ".join(label.get_text().split())] = data.string


    details = {"longitude": lon, 
               "latitude": lat, 
               "city_name": info.get("City") or info.get("Location") or info.get("Locations"),
               "fips": None,
               "venue": info.get("Venue"),
               "year_founded": info.get("Founded"),
               "genre": info.get("Genre"),
               "status": info.get("Status"),
               "frequency": info.get("Frequency"),
               "years_active": info.get("Years active")
               }
    # need to fix this so it doesnt crash and timeout 
    if details["city_name"] is None and lat is not None and lon is not None: 
        location = nominatim(geolocator.reverse, (lat, lon), language="en", addressdetails=True)
        # location = geolocator.reverse((lat, lon), language="en")
        if location:
            address = location.raw.get("address", {})
            details["city_name"] = (address.get("city") or address.get("town")
                                    or address.get("village") or address.get("hamlet"))
            details["county"] = address.get("county")
            if details["county"] and us_state:
                details["fips"] = af.get_county_fips(state=us_state, county=details["county"])
    elif (lat is None or lon is None) and details["city_name"] is not None:
        location = nominatim(geolocator.geocode, f'{details["city_name"]}, {us_state}',
                     country_codes="us", addressdetails=True, language="en")
        # location = geocode(f'{details["city_name"]}, {us_state}', country_codes="us")
        if location:
            address = location.raw.get("address", {})
            print(location)
            details["county"] = address.get("county")
            if details["county"] and us_state:
                details["fips"] = af.get_county_fips(state=us_state, county=details["county"])
            details["latitude"], details["longitude"] = location.latitude, location.longitude

    

    ## add extra info to retrieve city names that are missing :) 
    
    return details

geolocator = Nominatim(user_agent="Festival_Smoke_Detectors/1.0 (swechchha@gmail.com)", timeout=10)
reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)
nominatim = RateLimiter(_call, min_delay_seconds=1.1, max_retries=3,
                        error_wait_seconds=10, swallow_exceptions=True)


headers = {
    "User-Agent": "Festival_Smoke_Detectors/1.0 (https://github.com/swechchhaparajuli/festival_smoke_detectors; swechchha@gmail.com) python-requests/2.32"
}

url = "https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States"



def get_scraped_festivals(url):
    response = requests.get(
        url, headers=headers, timeout=30)
    html_text = response.text
    soup = BeautifulSoup(html_text, "html.parser")

    festival_links_list = soup.select('ul>li a.mw-redirect')

    festival_details = []
    

    for festival in festival_links_list:
        section = festival.find_parent("section")
        state = section["aria-labelledby"] if section else None
        festival_detail = each_festival(festival['href'], state)
        if festival_detail is not None:
            festival_details.append({"Name": festival.string, "longitude": festival_detail["longitude"], "latitude": festival_detail[
                                    "latitude"], "city_name": festival_detail["city_name"], "state": state, "venue": festival_detail["venue"],
                                    "year_founded": festival_detail["year_founded"], "genre": festival_detail["genre"], "is_active:": festival_detail["status"],
                                    "frequency": festival_detail["frequency"], "years_active": festival_detail["years_active"], "fips": festival_detail["fips"]})

    # Upload to GCS
    gcs_path = f"raw/wiki/{date.today()}/festival_details.json"
    response = write_blob(gcs_path, json.dumps(festival_details))
    print(f"write to blob response: {response}")
    return response