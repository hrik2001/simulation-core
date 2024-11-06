import logging
from datetime import datetime, timedelta, timezone

import requests
from celery import shared_task
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from core.models import Chain
from curve.models import DebtCeiling


logger = logging.getLogger(__name__)

BASE_URL = "https://prices.curve.fi"

retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[403, 429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


def curve_batch_api_call(path):
    url = f"{BASE_URL}{path}"
    items = []
    page = 1
    per_page = 100

    while True:
        response = session.get(url, params={"per_page": per_page, "page": page})
        response.raise_for_status()
        data = response.json()
        items.extend(data["data"])
        if per_page * page > data["count"]:
            break
        page += 1

    return items


def curve_api_call(path):
    url = f"{BASE_URL}{path}"
    response = session.get(url)
    response.raise_for_status()
    return response.json()


@shared_task
def task_curve__update_debt_ceiling():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    timestamp = datetime.now(tz=timezone.utc)
    cutoff_time = timestamp - timedelta(hours=6)

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain}")
    available_markets = [market for market in markets if market["borrowable"] > 0]

    for market in available_markets:
        controller = market["address"]
        all_users = curve_batch_api_call(f"/v1/crvusd/users/{chain}/{controller}/users")

        active_users = []
        for user in all_users:
            last_time = datetime.fromisoformat(user["last"])
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            if last_time > cutoff_time:
                active_users.append(user)

        user_data = []
        for user in active_users:
            user_address = user["user"]
            try:
                response = curve_api_call(f"/v1/crvusd/users/{chain}/{user_address}/{controller}/stats")
                user_data.append(response)
            except Exception as e:
                logger.error("Failed to retrieve user positions: User: %s, Controller: %s, Error: %s",
                             user_address, controller, e, exc_info=True)

        market["users"] = user_data

        DebtCeiling(timestamp=timestamp, chain=chain, controller=controller, data=market).save()
