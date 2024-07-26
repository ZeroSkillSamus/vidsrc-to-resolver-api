import base64
import os
import argparse
import requests
import re
import json

import questionary
import cloudscraper
from urllib.parse import quote
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import unquote
from typing import Optional, Tuple, Dict, List

from sources.vidplay import VidplayExtractor
from sources.filemoon import FilemoonExtractor
from utils import Utilities, VidSrcError, NoSourcesFound

SUPPORTED_SOURCES = ["Vidplay", "Filemoon"]
keys = [
  'bZSQ97kGOREZeGik',
  'NeBk5CElH19ucfBU',
  'Z7YMUOoLEjfNqPAt',
  'wnRQe3OZ1vMcD1ML',
  'eO74cTKZayUWH8x5'
]

class VidSrcExtractor:
    BASE_URL = "https://vidsrc.to"
    DEFAULT_KEY = "WXrUARXb1aDLaZjI"
    PROVIDER_URL = "https://vid2v11.site" # vidplay.site / vidplay.online / vidplay.lol
    TMDB_BASE_URL = "https://www.themoviedb.org"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    scraper = cloudscraper.create_scraper()

    def __init__(self, **kwargs) -> None:
        self.source_name = kwargs.get("source_name")
        self.fetch_subtitles = kwargs.get("fetch_subtitles")

    def decrypt_source_url(self, source_url: str) -> str:
        encoded = Utilities.decode_base64_url_safe(source_url)
        decoded = Utilities.decode_data(VidSrcExtractor.DEFAULT_KEY, encoded)
        decoded_text = decoded.decode('utf-8')

        return unquote(decoded_text)

    def get_source_url(self, source_id: str) -> str:
        #req = requests.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/source/{source_id}")
        print(source_id)
        req = self.scraper.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/source/{source_id}?token={quote(enc(source_id))}")
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        data = req.json()
        enc_url = data.get("result").get("url")
        return dec(enc_url)
        #encrypted_source_url = data.get("result", {}).get("url")
        #return self.decrypt_source_url(encrypted_source_url)

    def get_sources(self, data_id: str) -> Dict:
        scraper = cloudscraper.create_scraper()
        req = scraper.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/episode/{data_id}/sources?token={quote(enc(data_id))}")

        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        data = req.json()
        return {video.get("title"): video.get("id") for video in data.get("result")}

    def get_streams(self, media_type: str, media_id: str, season: Optional[str], episode: Optional[str]) -> Tuple[Optional[List], Optional[Dict], Optional[str]]:
        url = f"{VidSrcExtractor.BASE_URL}/embed/{media_type}/{media_id}"
        scraper = cloudscraper.create_scraper()
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
        print(f"Data_ID: {sources_code}")
        sources = self.get_sources(sources_code)
        source = sources.get(self.source_name)
        if not source:
            available_sources = ", ".join(list(sources.keys()))
            print(f"[VidSrcExtractor] No source found for \"{self.source_name}\"\nAvailable Sources: {available_sources}")
            return None, None, None

        source_url = self.get_source_url(source)
        query_params = source_url.split('?')[1]
        subtitles = get_vidplay_subtitles(query_params)
        print(subtitles)
        embed_id = source_url.split('?')[0].split('/')[4]
        print(embed_id)

        h = h_enc(embed_id)
        media_info_url = f"{self.PROVIDER_URL}/mediainfo/{embed_enc(embed_id)}?{query_params}&ads=0&h={quote(h)}"
        # print(h)
        req = scraper.get(media_info_url)
        if req.status_code != 200:
            print(f"[VidSrcExtractor] Couldnt fetch \"{req.url}\", status code: {req.status_code}\n[VidSrcExtractor] \"{self.source_name}\" likely doesnt have the requested media...")
            return None, None, None

        sources = json.loads(embed_dec(req.json().get("result")))
        json_array = []

        sources = sources.get('sources')
        json_array = []

        # Need to request the m3u8 file to get other qualities
        sources = [value.get("file") for value in sources]
        req = requests.get(sources[0])
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        pattern = re.compile(r"(RESOLUTION=)(.*)(\s*?)(\s*.*)")
        index_to_start = sources[0].index("list;")
        for match in pattern.finditer(req.text):
            quality = match.group(2).split("x")[-1]
            url = sources[0][:index_to_start] + match.group(4).strip()

            # Create a dictionary for the current match
            json_object = {
                "quality": quality,
                "url": url,
                "is_m3u8": ".m3u8" in url
            }

            # Append the dictionary to the JSON array
            json_array.append(json_object)

        #json_output = json.dumps(json_array)

        return json_array, subtitles


def get_vidplay_subtitles(url_data: str) -> Dict:
        scraper = cloudscraper.create_scraper()
        subtitles_url = re.search(r"info=([^&]+)", url_data)
        if not subtitles_url:
            return []

        subtitles_url_formatted = unquote(subtitles_url.group(1))
        # req = requests.get(subtitles_url_formatted)
        req = scraper.get(subtitles_url_formatted)

        # if req.status_code == 200:
        #     return {subtitle.get("label"): subtitle.get("file") for subtitle in req.json()}
        if req.status_code == 200:
            json_output = [
                {"label": subtitle.get("label"), "file": subtitle.get("file")}
                for subtitle in req.json()
            ]
            return json_output

        return []

def embed_dec(inp):
    inp = inp.replace('_', '/').replace('-', '+')
    i = str(base64.b64decode(inp),"latin-1")
    e = rc4(keys[4], i)
    e = urllib.parse.unquote(e)
    return e

def embed_enc(inp):
    inp = quote(inp)
    e = rc4(keys[1], inp)
    out = base64.b64encode(e.encode("latin-1")).decode()
    return out

def h_enc(inp):
    inp = quote(inp)
    e = rc4(keys[2], inp)
    out = base64.b64encode(e.encode("latin-1")).decode()
    out = out.replace('/', '_').replace('+', '-')
    return out

def enc(inp):
    inp = quote(inp)
    e = rc4(keys[0], inp)
    b64_encoded = base64.b64encode(e.encode("latin-1")).decode()
    modified_output = b64_encoded.replace('/', '_').replace('+', '-')
    return modified_output

def dec(inp):
    inp = inp.replace('_', '/').replace('-', '+')
    i = str(base64.b64decode(inp),"latin-1")
    e = rc4(keys[3], i)
    e = urllib.parse.unquote(e)
    return e

def rc4(key, inp):
    e = [[]] * 9
    e[4] = []
    e[3] = 0

    e[8] = ''
    for i in range (256):
        e[4].append(i)

    for i in range (256):
        e[3] = (e[3] + e[4][i] + ord(key[i % len(key)])) % 256
        e[2] = e[4][i]
        e[4][i] = e[4][e[3]]
        e[4][e[3]] = e[2]

    i = 0
    e[3] = 0

    for j in range(len(inp)):
        i = (i + 1) % 256
        e[3] = (e[3] + e[4][i]) % 256
        e[2] = e[4][i]
        e[4][i] = e[4][e[3]]
        e[4][e[3]] = e[2]
        e[8] += chr(ord(inp[j]) ^ e[4][(e[4][i] + e[4][e[3]]) % 256])
    return e[8]




