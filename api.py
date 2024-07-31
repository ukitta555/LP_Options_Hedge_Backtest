from datetime import datetime
import json
import os
from pprint import pprint
import requests
import pytz
import time

from consts import CRYPTOCOMPARE_API_KEY

class PriceStats:
    min_price: float
    max_price: float
    spot_price_window_start: float
    fee_0_diff_month_window: float | None
    fee_1_diff_month_window: float | None

    def __init__(self, min_price, max_price, spot_price_window_start):
        self.min_price = min_price
        self.max_price = max_price
        self.spot_price_window_start = spot_price_window_start
        self.fee_0_diff_month_window = None
        self.fee_1_diff_month_window = None

    def __str__(self):
        return (
            f"------------------------------------- \n"
            f"Min window price: {self.min_price} \n"
            f"Max window price: {self.max_price} \n"
            f"Spot price for the window start: {self.spot_price_window_start} \n"
            f"Scaled fee 0 diff: {self.fee_0_diff_month_window} \n"
            f"Scaled fee 1 diff: {self.fee_1_diff_month_window} \n"
            f"-------------------------------------"
        )

# ETH id = ethereum 
def fetch_price_statistics(token0_id: str, token1_id: str, window_start: datetime, window_end: datetime):
    window_start = window_start.replace(tzinfo=pytz.UTC)
    window_end = window_end.replace(tzinfo=pytz.UTC)

    #  TODO: fetch prices for the whole month!
    url = (
        f"https://min-api.cryptocompare.com/data/v2/histoday"
        f"?fsym={token0_id}"
        f"&tsym={token1_id}"
        f"&toTs={int(window_end.timestamp())}"
        f"&limit={(window_end - window_start).days}"
        f"&api_key={CRYPTOCOMPARE_API_KEY}"
    )

    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers)

    deserialized = json.loads(response.text)

    opening_prices = list(map(lambda x: x["open"], deserialized["Data"]["Data"]))
    
    stats = PriceStats(
        max_price=max(opening_prices),
        min_price=min(opening_prices),
        spot_price_window_start=opening_prices[0]
    )
    return stats 
