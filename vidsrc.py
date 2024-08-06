import base64
# import os
# import argparse
import requests
import re
import json

import questionary
import cloudscraper
from urllib.parse import quote
from urllib.parse import urlparse
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import unquote
from typing import Optional, Tuple, Dict, List
import numpy as np

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

def get_keys():
    url = 'https://raw.githubusercontent.com/Ciarands/vidsrc-keys/main/keys.json'
    req = requests.get(url)
    if req.status_code != 200:
        error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
        raise VidSrcError(error_msg)

    encrypt = req.json().get("encrypt")
    decrypt = req.json().get("decrypt")
    print(encrypt)
    print(decrypt)


class VidSrcExtractor:
    BASE_URL = "https://vidsrc.pro"
    DEFAULT_KEY = "WXrUARXb1aDLaZjI"
    PROVIDER_URL = "https://vid2v11.site" # vidplay.site / vidplay.online / vidplay.lol
    TMDB_BASE_URL = "https://www.themoviedb.org"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    scraper = cloudscraper.create_scraper()
    #tt = get_keys()

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
        get_keys()
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

def rc4_version_two(key, inp):
    # Initialize the state array and variables
    arr = list(range(256))
    counter = 0
    i = 0
    decrypted = ''

    # Key Scheduling Algorithm (KSA)
    key_length = len(key)
    for i in range(256):
        counter = (counter + arr[i] + ord(key[i % key_length])) % 256
        arr[i], arr[counter] = arr[counter], arr[i]

    # Pseudo-Random Generation Algorithm (PRGA)
    i = 0
    counter = 0
    for char in inp:
        i = (i + 1) % 256
        counter = (counter + arr[i]) % 256
        arr[i], arr[counter] = arr[counter], arr[i]
        decrypted += chr(ord(char) ^ arr[(arr[i] + arr[counter]) % 256])

    return decrypted

def dec_two(inp):
    return general_dec('8z5Ag5wgagfsOuhz', inp)

def enc_two(inp):
    return general_enc('Ex3tc7qjUz7YlWpQ', inp)

def general_enc(key, inp):
        inp = quote(inp)
        e = rc4(key, inp)
        out = base64.b64encode(e.encode("latin-1")).decode()
        out = out.replace('/', '_').replace('+', '-')
        return out

def general_dec(key, inp):
    inp = inp.replace('_', '/').replace('-', '+')
    i = str(base64.b64decode(inp),"latin-1")
    e = rc4_version_two(key,i)
    e = urllib.parse.unquote(e)
    return e

class F2Cloud:
    @staticmethod
    def h_enc(inp):
        return general_enc('BgKVSrzpH2Enosgm',inp)

    @staticmethod
    def embed_enc(inp):
        return general_enc('8Qy3mlM2kod80XIK', inp)

    @staticmethod
    def embed_dec(inp):
        return general_dec('9jXDYBZUcTcTZveM', inp)

    def stream(self,url):
        scraper = cloudscraper.create_scraper()
        url = urlparse(url)
        embed_id = url.path.split('/')[2]

        h = self.h_enc(embed_id)

        mediainfo_url = f"https://{url.hostname}/mediainfo/{self.embed_enc(embed_id)}?{url.query}&ads=0&h={urllib.parse.quote(h)}"
        print(f"New URL {mediainfo_url}")
        req = scraper.get(mediainfo_url)

        if req.status_code != 200:
            print(f"Failed! {mediainfo_url}    {req.status_code}")

        req = req.json()
        playlist = json.loads(self.embed_dec(req['result']))
        sources = playlist.get('sources')
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

        return json_array

class WatchSeriesExtractor:
    BASE_URL = "watchseriesx.to"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    scraper = cloudscraper.create_scraper()

    @staticmethod
    def extract_info(array):
        json_array = []
        for media in array:
            # Used to get title and media_id
            info = media.find('div',class_="info")
            media_id = info.find('a',class_="title")['href']
            title = info.find('a',class_="title").text.strip()


            # Inner contains quality and image_uri
            inner = media.find('div',class_="inner")
            quality = inner.find('b').text.strip()
            image_uri = inner.find('a',class_="poster").find('img')['data-src']

             # Create a dictionary for the current match
            json_object = {
                "title": title,
                "image_uri": image_uri,
                "quality": quality,
                "show_type": media_id.split('/')[1],
                "media_id": media_id
            }

            # Append the dictionary to the JSON array
            json_array.append(json_object)

        return json_array

    def fetch_trending_info(self,result_set):
        return self.extract_info(result_set.find('div',class_="swiper-wrapper item-lg").find_all('div',class_="swiper-slide item"))

    def return_trending_json(self):
        url = f"https://{self.BASE_URL}/home"
        req = self.scraper.get(url)

        if req.status_code != 200:
            print(f"FAILED {url} {req.status_code}")

        soup = BeautifulSoup(req.content,"html.parser")
        trending_media = soup.find_all('section',class_ = "swiper-default") # Gets info for trending tv and movies
        trending_overrall = soup.find('div',attrs={"data-name":"trending"}).find_all('div',class_='item')
        # print(trending_overrall)
        if len(trending_media) <= 0:
            return {
                "top_trending_media": [],
                "trending_movies": [],
                "trending_tv": []
             }

        return {
            "top_trending_media": self.extract_info(trending_overrall),
            "trending_movies": self.fetch_trending_info(trending_media[0]),
            "trending_tv": self.fetch_trending_info(trending_media[1])
        }

    def fetch_media_details(self,media_id):
        genres = []
        season_episodes = {}
        url = f"https://{self.BASE_URL}{media_id}"
        req = self.scraper.get(url)

        if req.status_code != 200:
            print(f"FAILED {url} {req.status_code}")

        soup = BeautifulSoup(req.content,"html.parser")

        details_info = soup.find('div',class_="col-info")
        title = details_info.find('h3',attrs={"itemprop":"name"}).text.strip()
        score = details_info.find('span',class_="imdb").text.strip()
        rating = details_info.find('span',class_="rating").text.strip()
        quality = details_info.find('span',class_="quality").text.strip()
        description = details_info.find('div',class_="description").text.strip()
        image_uri = details_info.find('img',attrs={"itemprop":"image"})["src"]

        # Get Genres and Release Date
        other_info = details_info.find('div',class_="meta").find_all('div',class_=None)
        release_date = details_info.find('div',class_="meta").find('span',attrs={"itemprop": "dateCreated"}).text.strip().split(', ')[-1]

        for info in other_info:
            category = info.find('div')
            if category and category.text.strip() == "Genre:":
                for genre in info.find_all('a'):
                    genres.append(genre.text.strip())
                break

        recommendations = self.extract_info(soup.find('section',class_="swiper-default").find_all('div',class_="swiper-slide item"))

        # Get Episode List
        data_id = re.search(r'data-id="(.*?)"', req.text).group(1)
        encoded_data_id = enc_two(data_id)
        url = f"https://{self.BASE_URL}/ajax/episode/list/{data_id}?vrf={urllib.parse.unquote(encoded_data_id)}"
        req = self.scraper.get(url)

        if req.status_code != 200:
            print(f"FAILED {url} {req.status_code}")
        soup = BeautifulSoup(req.json().get('result'),'html.parser')

        episodes = soup.find_all('ul',class_="range episodes")
        for season_episode in episodes:
            season_num = season_episode['data-season']
            episode_array = []
            for episode in season_episode.find_all('li'):
                episode_array.append({
                    "name":episode.find('a').find('span').text.strip(),
                    "id": episode.find('a')['data-id'],
                    "url":episode.find('a')['href'],
                    "episode_num":episode.find('a').find('p').text.strip()
                })
            season_episodes[season_num] = episode_array

        return {
            "title": title,
            "id": media_id,
            "banner_image_uri": "",
            "synopsis": description,
            "rating": rating,
            "score": score,
            "release_date": release_date,
            "image_uri": image_uri,
            "country": "",
            "quality": quality,
            "tmdb_id": "",
            "trailer_uri": "",
            "show_type": media_id.split('/')[1],
            "episodes": season_episodes,
            "genres": genres,
            "cast": [],
            "production_company": [],
            "recommendations": recommendations
        }

    def fetch_episode(self,data_id):
        # print(f"asdasdasd {data_id}")
        url = f"https://{self.BASE_URL}/ajax/server/list/{data_id}?vrf={urllib.parse.unquote(enc_two(data_id))}"
        req = self.scraper.get(url)
        if req.status_code != 200:
            print(f"FAILED {url} {req.status_code}")

        req = req.json()
        # print(req['result'])
        f2_cloud_id = re.search(r'data-id="41" data-link-id="(.*?)"', req['result']).group(1)

        url = f"https://{self.BASE_URL}/ajax/server/{f2_cloud_id}?vrf={urllib.parse.quote(enc_two(f2_cloud_id))}"

        req = self.scraper.get(url)

        if req.status_code != 200:
            print(f"FAILED {url} {req.status_code}")

        # print(req.json()['result']['url'])
        f2cloud_url_dec = dec_two(req.json()['result']['url'])
        return F2Cloud().stream(f2cloud_url_dec)



    def get_streams(self, media_id: str, season: Optional[str], episode: Optional[str]):
        url = f"https://{self.BASE_URL}/tv/{media_id}/{season}-{episode}"
        print(url)
        req = self.scraper.get(url)
        print(f"[>] Requesting {url}...")
        if req.status_code != 200:
            print(f"FAILED {url}! {req.status_code}")

        data_id = re.search(r'data-id="(.*?)"', req.text).group(1)

        if not data_id:
            print("[VidSrcExtractor] Could not fetch data-id, this could be due to an invalid imdb/tmdb code...")
            return None, None, None

        #sources_code = sources_code.get("data-id")
        # print(f"Data_ID: {data_id}")
        encoded_data_id = enc_two(data_id)
        url = f"https://{self.BASE_URL}/ajax/episode/list/{data_id}?vrf={urllib.parse.unquote(encoded_data_id)}"
        # print(url)

        # Hard code for now
        req = self.scraper.get(url)
        if req.status_code != 200:
            print(f"FAILED {url}! {req.status_code}")

        req = req.json()
        data_id = re.search(f'{season}-{episode}" data-id="(.*?)"', req['result']).group(1)
        return self.fetch_episode(data_id)






if __name__ == '__main__':
    vs =  WatchSeriesExtractor()
    #vs.get_streams("kingdom-of-the-planet-of-the-apes-yk536","1","1")
    # vs.fetch_trending_info()
    vs.fetch_media_details("/tv/naked-and-afraid-last-one-standing-q6kpw")
    # vse = VidSrcExtractor(
    #     source_name = "F2Cloud",
    #     fetch_subtitles = True,
    # )
    # vse.get_streams("tv","48891","1","1")
#    tt = dec_two("VfxvGYo3N8o-U0vTPLDxAq3NGemQvvNqZjK5NAMn3idupGR-U-XSRMuXTSRTjTOQq2xil9ypE3nPHXCPUd1737t4nrCAQolUdOer9FwOHNnQpEmfLAUykZ-xz1bIO1EjV9YYR02CLZqgy24azDXCygsf36IFplyjI8sjgK2Dac-woBlXvM6ZI3h64PUHoWfheUttJ_6Mu0dGWuVx_c1kS0artUYm_bHBqP0efcOVdg==")
#    v = F2Cloud().stream(tt)