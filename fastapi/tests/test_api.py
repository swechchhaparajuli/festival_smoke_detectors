import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from fastapi.testclient import TestClient


def make_epa_zip(year):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"daily_88101_{year}.csv",
                   '"State Code","County Code","Site Num","Date Local","Arithmetic Mean"\n'
                   '"06","037","1103","2024-07-01",12.3\n')
    return buf.getvalue()


class FakeResponse:
    def __init__(self, content=b"", status=200, json_data=None):
        self.content = content
        self.status_code = status
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


@pytest.fixture
def client(monkeypatch):
    bucket = {}

    def fake_write(path, data, content_type="application/json"):
        bucket[path] = data
        return f"gs://test-bucket/{path}"

    def fake_list(prefix):
        return [p for p in bucket if p.startswith(prefix)]

    def fake_get(url, params=None, headers=None, timeout=None):
        if "airdata" in url:
            if url.endswith("2024.zip"):
                return FakeResponse(make_epa_zip(2024))
            if url.endswith("2023.zip"):
                return FakeResponse(b"<html>maintenance</html>")
            return FakeResponse(status=404)
        if "ncei" in url:
            return FakeResponse(json_data=[{"DATE": "2025-07-01", "STATION": params["stations"], "TMAX": "206"}])
        raise AssertionError(url)

    epa = main.load_collector("epa_collector")
    noaa = main.load_collector("noaa_collector")
    monkeypatch.setattr(epa, "write_blob", fake_write)
    monkeypatch.setattr(epa, "list_blobs", fake_list)
    monkeypatch.setattr(noaa, "write_blob", fake_write)
    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(main, "project_id", "test-project")
    monkeypatch.setattr(main, "bucket_name", "test-bucket")
    return TestClient(main.app), bucket


def test_health(client):
    c, _ = client
    assert c.get("/health").json()["status"] == "ok"


def test_all_three_routes_exist(client):
    c, _ = client
    paths = c.get("/openapi.json").json()["paths"]
    assert {"/collect/epa", "/collect/noaa", "/collect/festivals"} <= set(paths)


def test_epa_saves_zip_then_skips_on_rerun(client):
    c, bucket = client
    r = c.post("/collect/epa", json={"start_year": 2024, "end_year": 2024}).json()
    assert len(r["saved"]) == 1 and not r["failed"]
    path = next(iter(bucket))
    assert path.startswith("raw/epa/") and path.endswith("/daily_88101_2024.zip")

    r2 = c.post("/collect/epa", json={"start_year": 2024, "end_year": 2024}).json()
    assert r2["skipped_existing"][0]["path"] == path and not r2["saved"]


def test_epa_rejects_html_and_missing_years(client):
    c, bucket = client
    r = c.post("/collect/epa", json={"start_year": 2022, "end_year": 2023}).json()
    assert {f["year"] for f in r["failed"]} == {2022, 2023}
    assert not bucket


def test_epa_rejects_bad_year_range(client):
    c, _ = client
    assert c.post("/collect/epa", json={"start_year": 2025, "end_year": 2020}).status_code == 422
    assert c.post("/collect/epa", json={"start_year": 1995, "end_year": 2000}).status_code == 422


def test_noaa_route(client):
    c, bucket = client
    r = c.post("/collect/noaa").json()
    assert r["source"] == "noaa" and len(r["successful"]) == 1
    assert any(p.startswith("raw/noaa/") for p in bucket)


def test_festivals_route_not_ready_yet(client):
    c, _ = client
    r = c.post("/collect/festivals")
    assert r.status_code == 501


def test_festivals_route_calls_scraper(client, monkeypatch):
    c, _ = client
    wiki = main.load_collector("wikipedia_scraper")
    calls = []

    def fake_scraper(url):
        calls.append(url)
        return [{"Name": "Hangout Music Fest", "state": "Alabama"}]

    monkeypatch.setattr(wiki, "url", "https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States", raising=False)
    monkeypatch.setattr(wiki, "get_scraped_festivals", fake_scraper, raising=False)
    r = c.post("/collect/festivals").json()
    assert calls == [wiki.url]
    assert r["result"][0]["Name"] == "Hangout Music Fest"
