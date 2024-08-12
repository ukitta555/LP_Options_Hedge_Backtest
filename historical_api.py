from datetime import datetime
import json
import os
from pprint import pprint
import requests
import pytz
import time

from consts import CRYPTOCOMPARE_API_KEY, USD_CC_ID

class PriceStats:
    t0_to_t1_min_price: float
    t0_to_t1_max_price: float
    t0_to_t1_price_window_start: float
    spot_price_window_start_token_0: float
    spot_price_window_start_token_1: float
    spot_price_window_end_token_0: float
    spot_price_window_end_token_1: float
    fee_0_diff_window: float | None
    fee_1_diff_window: float | None
    window_start: datetime
    window_end: datetime
    

    def __init__(
        self, 
        t0_to_t1_min_price, 
        t0_to_t1_max_price, 
        t0_to_t1_price_window_start, 
        spot_price_window_start_token_0, 
        spot_price_window_start_token_1, 
        spot_price_window_end_token_0,
        spot_price_window_end_token_1,
        window_start, 
        window_end
    ):
        self.t0_to_t1_min_price = t0_to_t1_min_price
        self.t0_to_t1_max_price = t0_to_t1_max_price
        self.t0_to_t1_price_window_start = t0_to_t1_price_window_start
        self.spot_price_window_start_token_0 = spot_price_window_start_token_0
        self.spot_price_window_start_token_1 = spot_price_window_start_token_1
        self.spot_price_window_end_token_0 = spot_price_window_end_token_0
        self.spot_price_window_end_token_1 = spot_price_window_end_token_1
        self.fee_0_diff_window = None
        self.fee_1_diff_window = None
        self.window_start = window_start
        self.window_end = window_end

    # def __str__(self):
    #     return (""
    #         f"------------------------------------- \n"
    #         f"Min window price (token0 to token1): {self.t0_to_t1_min_price} \n"
    #         f"Max window price (token0 to token1): {self.t0_to_t1_max_price} \n"
    #         f"Token0/Token1 spot price for the window start: {self.t0_to_t1_price_window_start} \n"
    #         f"Spot price for the token 0 for window start: {self.spot_price_window_start_token_0} \n"
    #         f"Spot price for the token 1 for window start:: {self.spot_price_window_start_token_1} \n"      
    #         f"Scaled fee 0 diff: {self.fee_0_diff_window} \n"
    #         f"Scaled fee 1 diff: {self.fee_1_diff_window} \n"
    #         f"Window: {self.window_start} - {self.window_end} \n"
    #         f"-------------------------------------"
    #     )


def fetch_price_statistics(token0_id: str, token1_id: str, window_start: datetime, window_end: datetime):
    window_start = window_start.replace(tzinfo=pytz.UTC)
    window_end = window_end.replace(tzinfo=pytz.UTC)

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

    opening_prices_token0_to_token_1 = list(map(lambda x: x["open"], deserialized["Data"]["Data"]))
    
    if min(opening_prices_token0_to_token_1) == 0:
        raise Exception("Bad CC API data")
    
    url_token_0_in_USD = (
        f"https://min-api.cryptocompare.com/data/v2/histoday"
        f"?fsym={token0_id}"
        f"&tsym={USD_CC_ID}"
        f"&toTs={int(window_start.timestamp())}"
        f"&limit={(window_end - window_start).days}"
        f"&api_key={CRYPTOCOMPARE_API_KEY}"
    )

    url_token_1_in_USD = (
        f"https://min-api.cryptocompare.com/data/v2/histoday"
        f"?fsym={token1_id}"
        f"&tsym={USD_CC_ID}"
        f"&toTs={int(window_start.timestamp())}"
        f"&limit={(window_end - window_start).days}"
        f"&api_key={CRYPTOCOMPARE_API_KEY}"
    )

    response = requests.get(url_token_0_in_USD, headers=headers)
    deserialized = json.loads(response.text)
    spot_price_token_0_in_USD = list(map(lambda x: x["open"], deserialized["Data"]["Data"]))
    spot_price_token_0_in_USD_start, spot_price_token_0_in_USD_end  = spot_price_token_0_in_USD[0], spot_price_token_0_in_USD[-1]

 
    response = requests.get(url_token_1_in_USD, headers=headers)
    deserialized = json.loads(response.text)
    spot_price_token_1_in_USD = list(map(lambda x: x["open"], deserialized["Data"]["Data"]))
    spot_price_token_1_in_USD_start, spot_price_token_1_in_USD_end  = spot_price_token_1_in_USD[0], spot_price_token_1_in_USD[-1]


    stats = PriceStats(
        t0_to_t1_max_price=max(opening_prices_token0_to_token_1),
        t0_to_t1_min_price=min(opening_prices_token0_to_token_1),
        t0_to_t1_price_window_start=opening_prices_token0_to_token_1[0],
        spot_price_window_start_token_0=spot_price_token_0_in_USD_start,
        spot_price_window_start_token_1=spot_price_token_1_in_USD_start,
        spot_price_window_end_token_0=spot_price_token_0_in_USD_end,
        spot_price_window_end_token_1=spot_price_token_1_in_USD_end,
        window_start=window_start,
        window_end=window_end
    )

 
    return stats 
