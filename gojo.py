import json
import re
import requests
from utils import Utilities
from typing import Optional, Tuple, Dict, Any
import cloudscraper 
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class GojoExtractor: 
    BASE_URL = "https://gojo.wtf"
    REFERER = "https://gojo.wtf/"
    ORIGIN = "https://gojo.wtf"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0";
    BACKEND_BASE_URL = "https://backend.gojo.wtf/api/anime"
    scraper = cloudscraper.create_scraper()

    def fetch_episodes(self,mal_id,ani_id):
        url = f"{self.BACKEND_BASE_URL}/episodes/{ani_id}"
        req = self.scraper.get(url, headers={"Referer": self.REFERER, "User-Agent": self.USER_AGENT})
        return json.loads(req.text)
    
    def fetch_streams(self,is_dub, provider, ani_id, episode_num, episode_id):
        url = self.createStreamURL(is_dub, provider, ani_id, episode_num, episode_id)
        req = self.scraper.get(url, headers={"Referer": self.REFERER, "User-Agent": self.USER_AGENT})
        response = json.loads(req.text)
        # x = {"sources":[{"quality":"1080p","url":"https://pahe.gojo.wtf/https://vault-14.kwikie.ru/stream/14/03/c373dc9d39a455a818c0c166a2a922f8121835d37342912d57ed06be4585e0f0/uwu.m3u8"},{"quality":"720p","url":"https://pahe.gojo.wtf/https://vault-14.kwikie.ru/stream/14/03/2a82dfd54affb78cce269e61367afaeb8249de05921c89b9d0773e1940e3d4b0/uwu.m3u8"},{"quality":"360p","url":"https://pahe.gojo.wtf/https://vault-14.kwikie.ru/stream/14/03/cba1e2850cba2a9d3fa98327ce239a563e0207c6739aa17c5c14ddc447fc88af/uwu.m3u8"}],"skips":{"op":{"startTime":103.375,"endTime":192.917},"ed":{"startTime":1325.633,"endTime":1419.375},"number":1}}
        headers = { 
            "referer": self.REFERER,
            "origin": self.ORIGIN
        }

        response = {
            "headers": headers,
            "sources": response["sources"],
            "intro": {
                "start": response["skips"]["op"]["startTime"],
                "end": response["skips"]["op"]["endTime"]
            },
            "outro": {
                "start": response["skips"]["ed"]["startTime"],
                "end": response["skips"]["ed"]["endTime"]
            },
            "tracks": []
        }
        return response

    def createStreamURL(self,is_dub, provider, ani_id, episode_num, episode_id):
        url = f"{self.BACKEND_BASE_URL}/tiddies"
        lang_state = "dub" if is_dub else "sub"

        # Create query parameters dictionary
        params = {
            "provider": provider,
            "id": ani_id,
            "num": episode_num,
            "subType": lang_state,
            "watchId": episode_id
        }
    #     }
    #     pub url: String,
    # pub quality: String,
    # pub is_m3u8: bool,
    #     pub headers: Headers,
    # pub sources: Vec<M3u8>,
    # pub intro: Option<AnimeSongRanges>,
    # pub outro: Option<AnimeSongRanges>,
    # pub tracks: Option<Vec<Subtitle>>,
        # Parse the URL and add query parameters
        url_parts = list(urlparse(url))
        query = dict(parse_qs(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query, doseq=True)
        return urlunparse(url_parts)