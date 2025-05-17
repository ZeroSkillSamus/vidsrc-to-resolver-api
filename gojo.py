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
        print(url)
        req = self.scraper.get(url, headers={"Referer": self.REFERER, "User-Agent": self.USER_AGENT})
        response = json.loads(req.text)
        # print(response)
        headers = { 
            "referer": self.REFERER,
            "origin": self.ORIGIN
        }
        if response["skips"] == None:
            return {
                "headers": headers,
                "sources": response.get("sources", []),
                "tracks": []
            }
        # print(response["skips"] == "None")
        return {
            "headers": headers,
            "sources": response.get("sources",[]),
            "intro": {
                "start": response.get("skips",{})["op"]["startTime"],
                "end": response.get("skips",{})["op"]["endTime"]
            },
            "outro": {
                "start": response.get("skips",{}).get("ed",{}).get("startTime"),
                "end": response.get("skips",{}).get("ed",{}).get("endTime")
            },
            "tracks": []
        }

    def createStreamURL(self,is_dub: bool, provider, ani_id, episode_num, episode_id):
        url = f"{self.BACKEND_BASE_URL}/tiddies"
        lang_state = "dub" if is_dub else "sub"
        print(lang_state)
        # Create query parameters dictionary
        params = {
            "provider": provider,
            "id": ani_id,
            "num": episode_num,
            "subType": lang_state,
            "watchId": episode_id
        }

        # Parse the URL and add query parameters
        url_parts = list(urlparse(url))
        query = dict(parse_qs(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query, doseq=True)
        return urlunparse(url_parts)