import bisect
from typing import List
import pymongo
from dotenv import load_dotenv
import os

load_dotenv()
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")


def get_mongodb_db():
    database_name = "arcadiasim"
    client = pymongo.MongoClient(MONGODB_CONNECTION_STRING, uuidRepresentation='standard')
    collections = [
        "PARAMS",
        "ACCOUNTS",
        "BID",
        "STATE",
        "ORCHESTRATOR",
        "METRICS",
    ]  # Pre-initialize ORCHESTRATOR key
    db = client[database_name]
    for collection_name in collections:
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
    return db


def get_closest_key(sorted_list_of_keys: List[int], target: int):
    idx = bisect.bisect_left(sorted_list_of_keys, target)

    if idx > 0 and abs(sorted_list_of_keys[idx] - target) > abs(
        sorted_list_of_keys[idx - 1] - target
    ):
        idx -= 1

    return idx


def filter_dict_in_range(data: dict, start: int, end: int) -> dict:
    """
    Filter a dictionary by a given range
    """
    return {k: v for k, v in data.items() if start <= int(k) <= end}
