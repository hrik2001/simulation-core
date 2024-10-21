import hashlib
import json
import os
from functools import lru_cache
from typing import TextIO

import requests
from django.conf import settings

# Assuming 'filter_dict_in_range' is defined in 'arcadiasim.utils'
from ..utils import filter_dict_in_range


@lru_cache(maxsize=None)
class Caching:
    def __init__(self):
        # Find the project root directory in a cross-platform way
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        project_root = settings.MEDIA_ROOT
        # Construct the base path for caching
        self.base_path = os.path.join(project_root, ".cache")
        self.file_mappings = {}
        # Ensure the cache directory exists
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
        # Create or open the .gitignore file to ignore cache files
        with open(os.path.join(self.base_path, ".gitignore"), "w") as f:
            f.write("*")
        # Load or initialize the file mappings
        mapping_file_path = os.path.join(self.base_path, "file_mappings.json")
        if os.path.exists(mapping_file_path):
            with open(mapping_file_path, "r") as f:
                self.file_mappings = json.load(f)
        else:
            with open(mapping_file_path, "w") as f:
                f.write("{}")

    def _path(self, path: str) -> str:
        # Normalize the path for the current operating system
        return os.path.join(self.base_path, *path.strip("/").split("/"))

    def open_read_file(self, path: str) -> TextIO:
        file_path = self._path(path)
        if os.path.exists(file_path):
            return open(file_path, "r")
        else:
            raise FileNotFoundError(f"File {file_path} not found")

    def add_to_mapping(self, path: str, file_path: str):
        self.file_mappings[path] = file_path
        with open(os.path.join(self.base_path, "file_mappings.json"), "w") as f:
            json.dump(self.file_mappings, f)

    def open_write_file(self, path: str) -> TextIO:
        file_path = self._path(path)
        # Ensure the directory exists before creating the file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return open(file_path, "w")

    def save_json_file(self, path: str, data: dict) -> None:
        with self.open_write_file(path) as f:
            json.dump(data, f)

    def update_json_file(self, path: str, data: dict) -> None:
        os.remove(self._path(path))
        self.save_json_file(path, data)

    def get_cached_response(self, path: str):
        try:
            with self.open_read_file(path) as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def get_cached_chainlink(
        self,
        asset: str,
        chain: "Chain",
        numeraire: str,
        start_timestamp: int,
        end_timestamp: int,
    ):
        try:
            response = self.get_cached_response(
                f"chainlink/{chain.name.lower()}/{asset}_{numeraire}.json"
            )
        except FileNotFoundError as e:
            print(e)
            print(
                "Be sure to run `python scripts/chainlink/main.py oracle` and `python scripts/chainlink/main.py generate`"
            )
            quit(1)
        if start_timestamp > end_timestamp:
            raise ValueError("Start timestamp is greater than end timestamp")
        response["data"] = {int(k): int(v) for k, v in response["data"].items()}
        keys = list(response["data"].keys())
        if start_timestamp < keys[0] or end_timestamp > keys[-1]:
            raise ValueError("Timestamps not in range")

        filtered_data = filter_dict_in_range(
            response["data"], start_timestamp, end_timestamp
        )
        denom = 10 ** int(response["decimals"])
        resp = {key: round(filtered_data[key] / denom, 6) for key in filtered_data}
        return resp

    def cached_request_get(self, url: str, **kwargs):
        # Sanitize the URL to create a valid directory name
        folder = url.split("://")[1].split("/")[0].replace(".", "_")
        # Use a hash of the entire URL to ensure uniqueness
        if not kwargs:
            kwargs_str = ""
        else:
            kwargs_str = json.dumps(kwargs)
        name = hashlib.sha256((url + kwargs_str).encode("utf-8")).hexdigest()[:10]
        # Construct the full path with folder and name
        full_path = os.path.join(folder, name)
        response = self.get_cached_response(full_path)
        if response is not None:
            response["is_internally_cached"] = True
            return response

        # Fetch and cache if not found
        response = requests.get(url, **kwargs)
        if response.status_code == 200:
            self.save_json_file(full_path, response.json())
            self.add_to_mapping(full_path, url)
            response = response.json()
            response["is_internally_cached"] = False
            return response
        else:
            print(
                f"Failed to retrieve data from the API. Status code: {response.status_code} : {url}\nTried to query {url}"
            )


cache = Caching()
