
# ETH - USDT
from collections import deque
import csv
from datetime import datetime, timedelta
import json
import math
from pprint import pprint
import sys
import numpy as np
import pandas as pd

import pytz
import requests

from consts import CRYPTOCOMPARE_API_KEY

def parse_implied_volatility_data_btc():
    df = pd.read_csv(f"./options_data/bitvol.csv", sep=";")
    df['Date'] = pd.to_datetime(df['Date'])
    df['Date'] = df['Date'].transform(lambda x: pytz.timezone('UTC').localize(x))
    return df

def parse_implied_volatility_data_eth():
    df = pd.read_csv(f"./options_data/ethvol.csv", sep=";")
    df['Date'] = pd.to_datetime(df['Date'])
    df['Date'] = df['Date'].transform(lambda x: pytz.timezone('UTC').localize(x))
    return df

def fetch_data(base_token: str, quote_token: str, offset: timedelta, length_of_dataset: int):
    try: 
        with open(f"./options_data/{base_token}_{quote_token}.csv", "r") as csv_file:
            pass
    except Exception:
        now = datetime.now()
        last_data_point_for_std = now - offset

        url = f"https://min-api.cryptocompare.com/data/v2/histohour"
        
        ONE_HOUR = timedelta(hours=1)

        counter = 0 
        whole_dataset = []
        with open(f"./options_data/{base_token}_{quote_token}.csv", "w+") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=",")
            while counter < length_of_dataset:
                print(type(last_data_point_for_std - counter * ONE_HOUR))
                params = {
                    "fsym": base_token,
                    "tsym": quote_token,
                    "limit": min(length_of_dataset - counter, 2000),
                    "toTs": int((last_data_point_for_std - counter * ONE_HOUR).timestamp()),
                    "api_key": CRYPTOCOMPARE_API_KEY
                }
 
                response = requests.get(
                    url,
                    params=params
                )
                deserialized = json.loads(response.text)

                pprint(deserialized["Data"]["Data"])

                counter += min(length_of_dataset - counter, 2000) + 1
                print(f"Counter: {counter}")
                print(len(deserialized))
                
                important_data = list(map(lambda x: (x["time"], x["close"]), deserialized["Data"]["Data"]))
                reversed_important_data = list(reversed(important_data))
                whole_dataset.extend(reversed_important_data)

            whole_dataset = list(reversed(whole_dataset))
            
            previous = None
            # row = (time, price)
            for idx, row in enumerate(whole_dataset):
                if previous is None:
                    csv_writer.writerow((row[0], 0))
                else:
                    csv_writer.writerow((row[0], math.log(row[1] / previous)))
                previous = row[1]
            

def read_from_file(base_token: str, quote_token: str) -> pd.DataFrame:
    df = pd.read_csv(f"./options_data/{base_token}_{quote_token}.csv")
    df.columns = ["time", "log"]
    df["datetime"] = df["time"].transform(lambda x: datetime.fromtimestamp(x, tz=pytz.UTC))
    return df


def filter_by_time_window(df: pd.DataFrame, start_date: datetime, end_date: datetime):
    result = df[(int(start_date.timestamp()) <= df["time"]) & (df["time"] <= int(end_date.timestamp()))]
    return result


if __name__ == "__main__":
    base_token = "ETH"
    # base_token = "BTC"
    quote_token = "USD"
    fetch_data(
        base_token=base_token,
        quote_token=quote_token,
        offset=timedelta(days=0), 
        length_of_dataset=27000
    )
    log_of_ratios = read_from_file(
        base_token=base_token,
        quote_token=quote_token
    )   
    
    implied_volatility_data = parse_implied_volatility_data_eth() if base_token == "ETH" else parse_implied_volatility_data_btc()
    implied_volatility_data_dict: dict = dict()
    for row in implied_volatility_data.iterrows():
        implied_volatility_data_dict[row[1]["Date"]] = row[1]["Ethereum Volatility Index"] if base_token == "ETH" else row[1]["BitVol® Bitcoin Volatility Index"] 
    
    pprint(implied_volatility_data_dict)

    print(log_of_ratios)

    bruteforce_range_left = 60
    bruteforce_range_right = 15
    
    buffer_size = max(bruteforce_range_left, bruteforce_range_right) * 24

    min_error = (-1, -1, sys.maxsize * 2 + 1) # days_left, days_right, error itself
    for days_left_side in range(1, bruteforce_range_left):
        for days_right_side in range(1, bruteforce_range_right):
            if days_left_side == 59 and days_right_side == 7:
                realized_volatility_list = []
                print(days_left_side, days_right_side)
                current_error = 0
                rolling_window_deque = deque(maxlen=(days_left_side+days_right_side) * 24)
                counter = 0
                # pre-fill
                for idx in range(buffer_size - days_left_side * 24, buffer_size + days_right_side * 24):
                    counter += 1
                    rolling_window_deque.append(log_of_ratios.loc[idx, "log"])
                
                current_time = pd.to_datetime(log_of_ratios.loc[buffer_size, "datetime"])
                assert(counter == (days_left_side+days_right_side) * 24)
                
                # TODO: calculate this only for the first hours of the day
                for idx in range(buffer_size, len(log_of_ratios) - buffer_size):
                    if current_time.hour == 0 and \
                        (
                            current_time <= datetime(year=2023, month=9, day=14, tzinfo=pytz.UTC) or \
                            datetime(year=2023, month=9, day=24, tzinfo=pytz.UTC) <= current_time
                        ):
                            realized_volatility = np.std(rolling_window_deque) * math.sqrt(24) * math.sqrt(365)
                            realized_volatility_list.append((f"{current_time.year}-{current_time.month}-{current_time.day}", float(realized_volatility)))
                            implied_volatility = implied_volatility_data_dict[current_time] / 100 
                            # print(f"Realized: {realized_volatility}, implied: {implied_volatility}")
                            current_error += (realized_volatility - implied_volatility) ** 2
                    current_time += timedelta(hours=1)
                    rolling_window_deque.popleft()
                    rolling_window_deque.append(log_of_ratios.loc[idx + days_right_side * 24, "log"])
                if min_error[2] > current_error:
                    min_error = (days_left_side, days_right_side, current_error)
    
    print(min_error)
    pprint(realized_volatility_list)