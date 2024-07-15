import os
import argparse
import requests
import questionary
import cloudscraper

from bs4 import BeautifulSoup
from urllib.parse import unquote
from typing import Optional, Tuple, Dict, List

from sources.vidplay import VidplayExtractor
from sources.filemoon import FilemoonExtractor
from utils import Utilities, VidSrcError, NoSourcesFound

SUPPORTED_SOURCES = ["Vidplay", "Filemoon"]

class VidSrcExtractor:
    BASE_URL = "https://vidsrc.to"
    DEFAULT_KEY = "WXrUARXb1aDLaZjI"
    PROVIDER_URL = "https://vid2v11.site" # vidplay.site / vidplay.online / vidplay.lol
    TMDB_BASE_URL = "https://www.themoviedb.org"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"

    def __init__(self, **kwargs) -> None:
        self.source_name = kwargs.get("source_name")
        self.fetch_subtitles = kwargs.get("fetch_subtitles")

    def decrypt_source_url(self, source_url: str) -> str:
        encoded = Utilities.decode_base64_url_safe(source_url)
        decoded = Utilities.decode_data(VidSrcExtractor.DEFAULT_KEY, encoded)
        decoded_text = decoded.decode('utf-8')

        return unquote(decoded_text)

    def get_source_url(self, source_id: str) -> str:
        scraper = cloudscraper.create_scraper()
        #req = requests.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/source/{source_id}")
        req = scraper.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/source/{source_id}")
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        data = req.json()
        encrypted_source_url = data.get("result", {}).get("url")
        return self.decrypt_source_url(encrypted_source_url)

    def get_sources(self, data_id: str) -> Dict:
        scraper = cloudscraper.create_scraper()
        #req = requests.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/episode/{data_id}/sources")
        req = scraper.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/episode/{data_id}/sources")
        print(f"GET SOURCES URL {VidSrcExtractor.BASE_URL}/ajax/embed/episode/{data_id}/sources")
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        data = req.json()
        return {video.get("title"): video.get("id") for video in data.get("result")}

    def get_streams(self, media_type: str, media_id: str, season: Optional[str], episode: Optional[str]) -> Tuple[Optional[List], Optional[Dict], Optional[str]]:
        url = f"{VidSrcExtractor.BASE_URL}/embed/{media_type}/{media_id}"
        #print(f"Start URL  {url}")
        scraper = cloudscraper.create_scraper()
        #
        if season and episode:
            url += f"/{season}/{episode}"

        print(f"[>] Requesting {url}...")
        #req = requests.get(url)
        req = scraper.get(url)
        if req.status_code != 200:
            print(f"[VidSrcExtractor] Couldnt fetch \"{req.url}\", status code: {req.status_code}\n[VidSrcExtractor] \"{self.source_name}\" likely doesnt have the requested media...")
            return None, None, None


        soup = BeautifulSoup(req.text, "html.parser")
        sources_code = soup.find('a', {'data-id': True})
        if not sources_code:
            print("[VidSrcExtractor] Could not fetch data-id, this could be due to an invalid imdb/tmdb code...")
            return None, None, None

        sources_code = sources_code.get("data-id")
        print(f"Data_ID {sources_code}")
        sources = self.get_sources(sources_code)
        source = sources.get(self.source_name)
        print(f"SOURCE {source}")
        if not source:
            available_sources = ", ".join(list(sources.keys()))
            print(f"[VidSrcExtractor] No source found for \"{self.source_name}\"\nAvailable Sources: {available_sources}")
            return None, None, None

        source_url = self.get_source_url(source)
        print(f"sourceURL {source_url}")
        if self.source_name == "Vidplay" or self.source_name == "F2Cloud":
            print(f"[>] Fetching source for \"{self.source_name}\"...")

            extractor = VidplayExtractor()
            return extractor.resolve_source(url=source_url, fetch_subtitles=self.fetch_subtitles, provider_url=VidSrcExtractor.PROVIDER_URL)

        elif self.source_name == "Filemoon":
            print(f"[>] Fetching source for \"{self.source_name}\"...")

            if self.fetch_subtitles:
                print(f"[VidSrcExtractor] \"{self.source_name}\" doesnt provide subtitles...")

            extractor = FilemoonExtractor()
            return extractor.resolve_source(url=source_url, fetch_subtitles=self.fetch_subtitles, provider_url=VidSrcExtractor.PROVIDER_URL)

        else:
            print(f"[VidSrcExtractor] Sorry, this doesnt currently support \"{self.source_name}\" :(\n[VidSrcExtractor] (if you create an issue and ask really nicely ill maybe look into reversing it though)...")
            return None, None, None

    def query_tmdb(self, query: str) -> Dict:
        req = requests.get(f"{VidSrcExtractor.TMDB_BASE_URL}/search", params={'query': query.replace(" ", "+").lower()}, headers={'user-agent': VidSrcExtractor.USER_AGENT})
        soup = BeautifulSoup(req.text, "html.parser")
        results = {}

        for index, data in enumerate(soup.find_all("div", {"class": "details"}), start=1):
            result = data.find("a", {"class": "result"})
            title = result.find()

            if not title:
                continue

            title = title.text
            release_date = data.find("span", {"class": "release_date"})
            release_date = release_date.text if release_date else "1 January, 1970"
            url = result.get("href")

            if not url:
                continue

            result_type, result_id = url[1:].split("/")
            if "-" in result_id:
                result_id = result_id.partition("-")[0]
            results.update({f"{index}. {title} ({release_date})": {"media_type": result_type, "tmdb_id": result_id}})

        return results