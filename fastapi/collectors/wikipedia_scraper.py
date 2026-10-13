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


def each_festival(link):
    response = requests.get(link, headers=headers, timeout=30)
    f_html_text = response.text
    f_soup = BeautifulSoup(f_html_text, "html.parser")
    lat, lon = None, None
    info = {}

    geo = f_soup.select_one("span.geo")
    if geo: 
        lat, lon = geo.get_text().split(";")

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
               "venue": info.get("Venue"),
               "year_founded": info.get("Founded"),
               "genre": info.get("Genre"),
               "status": info.get("Status"),
               "frequency": info.get("Frequency"),
               "years_active": info.get("Years active")
               }
    # need to fix this so it doesnt crash and timeout 
    # if details["city_name"] is None: 
    #     location = geolocator.reverse((lat, lon))
    #     print(location)

    ## add extra info to retrieve city names that are missing :) 
    
    return details

geolocator = Nominatim(user_agent="festival_smoke_detectors", timeout=10)

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
        festival_detail = each_festival(festival['href'])
        festival_details.append({"Name": festival.string, "longitude": festival_detail["longitude"], "latitude": festival_detail[
                                "latitude"], "city_name": festival_detail["city_name"], "venue": festival_detail["venue"],
                                "year_founded": festival_detail["year_founded"], "genre": festival_detail["genre"], "is_active:": festival_detail["status"],
                                "frequency": festival_detail["frequency"], "years_active": festival_detail["years_active"]})


    print(festival['href'])


    print(festival_details)

# for test
if __name__=="__main__":
    get_scraped_festivals(url)