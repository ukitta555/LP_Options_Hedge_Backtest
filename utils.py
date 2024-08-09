import csv
from datetime import datetime, timedelta
import json
import math
import pandas as pd

from matplotlib import pyplot as plt
import pytz
import requests

from consts import CRYPTOCOMPARE_API_KEY


def format_cached_dune_response(raw_row):
    raw_row["call_block_time"] = datetime.strptime(
        raw_row["call_block_time"], 
        "%Y-%m-%d %H:%M:%S"
    )
    processed_row = raw_row
    return processed_row
   
def format_dune_fee_query(raw_row):
    raw_row["call_block_time"] = datetime.strptime(
        raw_row["call_block_time"], 
        "%Y-%m-%d %H:%M:%S.%f %Z"
    )
    processed_row = raw_row
    return processed_row

def visualize_token_groups(fee_data, time_window: timedelta):
    fig = plt.figure(figsize =(10, 7))
    i = 0
    for key, value in fee_data.items():
        plot = plt.scatter(
            x=[i]*len(value), 
            y=value,
            alpha=0.5,
            label=key,
            marker='x'
        )
        i += 1

    plt.xticks([_ for _ in range(len(fee_data))], fee_data.keys())
    plt.xticks(rotation=45) 
    plt.subplots_adjust(bottom=0.16)
    
    profitability_line = plt.axhline(y=1, color='r', linestyle='--', label='Profitability threshold')
    plt.ylabel("LP fees / Option price")
    plt.legend(handles=[profitability_line])
    plt.title(f"LP fees / Option price ({int(time_window.days / 7)} weeks period)")
    plt.show()
    

def fetch_hourly_logarithmic_ratios(base_token: str, quote_token: str, bips: int, chain: str, offset: timedelta, length_of_dataset: int):
    try: 
        with open(f"./options_data/{base_token}_{quote_token}_{bips}_{chain}.csv", "r") as csv_file:
            pass
    except Exception:
        now = datetime.now()
        last_data_point_for_std = now - offset

        url = f"https://min-api.cryptocompare.com/data/v2/histohour"
        
        ONE_HOUR = timedelta(hours=1)

        counter = 0 
        whole_dataset = []
        print("Start fetching data from CC hourly API...")
        with open(f"./options_data/{base_token}_{quote_token}_{bips}_{chain}.csv", "w+") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=",")
            while counter < length_of_dataset:
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

                # pprint(deserialized["Data"]["Data"])

                counter += min(length_of_dataset - counter, 2000) + 1
                
                important_data = list(map(lambda x: (x["time"], x["close"]), deserialized["Data"]["Data"]))
                reversed_important_data = list(reversed(important_data))
                whole_dataset.extend(reversed_important_data)

            whole_dataset = list(reversed(whole_dataset))
            
            previous = None
            # row = (time, price)
            for idx, row in enumerate(whole_dataset):
                if previous is None:
                    csv_writer.writerow((row[0], 0))
                elif previous == 0 or row[1] == 0:
                    csv_writer.writerow((row[0], 0))
                else:
                    csv_writer.writerow((row[0], math.log(row[1] / previous)))
                previous = row[1]            
        print("Finish fetching data from CC hourly API!")

def read_from_file(base_token: str, quote_token: str, bips: int, chain: str) -> pd.DataFrame:
    df = pd.read_csv(f"./options_data/{base_token}_{quote_token}_{bips}_{chain}.csv")
    df.columns = ["time", "log"]
    df["datetime"] = df["time"].transform(lambda x: datetime.fromtimestamp(x, tz=pytz.UTC))
    return df