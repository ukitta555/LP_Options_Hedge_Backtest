from collections import deque
from datetime import datetime, timedelta
from pprint import pprint
import sys
from matplotlib import pyplot as plt    
import pandas as pd
from dune_client.client import DuneClient
from pathlib import Path
from dune_client.types import QueryParameter
from dune_client.query import QueryBase
import numpy as np
import pytz
from historical_api import PriceStats, fetch_price_statistics
from consts import DUNE_API_KEY, QUERY_ID_FEE_0_ARB, QUERY_ID_FEE_0_ETH, QUERY_ID_FEE_0_OPT, QUERY_ID_FEE_0_POLY, QUERY_ID_FEE_1_ARB, QUERY_ID_FEE_1_ETH, QUERY_ID_FEE_1_OPT, QUERY_ID_FEE_1_POLY, WEB3_ARB_URL, WEB3_ETH_URL, WEB3_OPT_URL, WEB3_POLYGON_URL
import math

from utils import fetch_hourly_logarithmic_ratios, format_cached_dune_response, format_dune_fee_query, read_from_file, visualize_token_groups
from web3_api import fetch_pool_address, fetch_token_decimals

dune = DuneClient(DUNE_API_KEY)

# calculate the closest realized volatility for the liquidity_provision_time 
def calculate_realized_volatility(liquidity_provision_time: datetime, log_of_ratios: pd.DataFrame):
    # bruteforced "optimal" hyperparameters 
    days_left_side = 22
    days_right_side = 21
    
    buffer_size = max(days_left_side, days_right_side) * 24
    
    if liquidity_provision_time < log_of_ratios.loc[buffer_size, "datetime"] or log_of_ratios.loc[len(log_of_ratios) - buffer_size - 1, "datetime"] < liquidity_provision_time:
        raise Exception("Can't calculate for this liquidity provision time due to using historical/future data, skipping window..")
    else:
        window = deque(maxlen=(days_left_side+days_right_side) * 24)
        counter = 0

        earliest_usable_time = log_of_ratios.loc[buffer_size, "datetime"]
        liquidity_provision_time_trimmed: datetime = liquidity_provision_time.replace(minute=0, second=0, tzinfo=pytz.UTC)
        
        # print(f"Liquidity provided at: {liquidity_provision_time_trimmed}, earliest time to calculate volatility: {earliest_usable_time}")
        # hour_difference = int((liquidity_provision_time_trimmed - earliest_usable_time).total_seconds() // 3600)
        # assert((liquidity_provision_time_trimmed - earliest_usable_time).total_seconds() % 3600 == 0)

        # closest_hour_entry = buffer_size + hour_difference 
        # print(f"Hour difference for volatility: {hour_difference}, index of the entry used for calculating the volatility {closest_hour_entry}, entry itself: \n {log_of_ratios.loc[closest_hour_entry]}")

        i = 0
        while log_of_ratios.loc[buffer_size + i, "datetime"] < liquidity_provision_time_trimmed:
            i += 1
        closest_hour_entry = buffer_size + i
        # print(f"Index of the entry used for calculating the volatility {closest_hour_entry}, entry itself: \n {log_of_ratios.loc[closest_hour_entry]}")

        for idx in range(closest_hour_entry - days_left_side * 24, closest_hour_entry + days_right_side * 24):
            counter += 1
            window.append(log_of_ratios.loc[idx, "log"])
    
        assert(counter == (days_left_side+days_right_side) * 24)
        realized_volatility = np.std(window) * math.sqrt(24) * math.sqrt(365)
        return realized_volatility

# (token0 - token1)
# USDC - WETH 

def calculate_required_liquidity_usd(
    token0_price_usd: float, 
    token1_price_usd: float,
    price_range_lower_bound: int,
    price_range_upper_bound: int,
    uniswap_price: int, 
    decimals_token0: int,
    decimals_token1: int
):
    L = 1
    P_l = price_range_lower_bound
    P_h = price_range_upper_bound
    P_0 = token0_price_usd
    P_1 = token1_price_usd
    P = uniswap_price

    # print(f"L: {L}, P_l: {P_l}, P_h: {P_h}, P_0: {P_0}, P_1: {P_1}, P:{P}, dec_token_0: {decimals_token0}, dec_token_1: {decimals_token1}")
    # print(f"P_0: {P_0}, P_1: {P_1}, dec_token_0: {decimals_token0}, dec_token_1: {decimals_token1}")
    # print(type(L), type(P))

    total_usd_token0 = (((L * (2 ** 96)) / P - (L * (2 ** 96)) / P_h) * P_0) / ((10 ** decimals_token0)) 
    total_usd_token1 = (((L * P) / (2 ** 96) - (L * P_l) / (2 ** 96)) * P_1) / ((10 ** decimals_token1))
    
    return total_usd_token0 + total_usd_token1  

def convert_real_price_to_uniswap_price(
    real_price: float,
    decimals: int, 
) -> int:
    return int(math.sqrt(real_price * (10 ** decimals)) * (2 ** 96))


def fetch_dune_fee_data(
    query_id: int, 
    pool_address: str,
    filename: str,
    dir_name: str
):
    formatted_response = []
    try:
        with open(filename, "r+") as f:
            line_no = 0
            lines = f.readlines()
            if len(lines) == 0:
                print("No data in file - skipping this token pair...")
                raise Exception("No data in file - skipping this token pair...")
            while line_no < len(lines):
                entry = dict()
                entry["call_block_time"] = lines[line_no].strip()
                line_no += 1
                entry["fee"] = lines[line_no].strip()
                line_no += 1
                formatted_response.append(entry)
            formatted_response = list(map(format_cached_dune_response, formatted_response))
    except FileNotFoundError:
        print("One of the fee files not found, fetching from Dune Analytics...")
        raw_fee_query_result = dune.get_latest_result(query_id)    
        query = QueryBase(
            query_id=query_id,
            params=[
                QueryParameter.text_type(name="pool_address", value=pool_address)
            ]
        )
        raw_fee_query_result = dune.run_query(query=query)
        formatted_response = list(map(format_dune_fee_query, raw_fee_query_result.result.rows))
        if len(formatted_response) == 0:
            print("No data in Dune - skipping this token pair...")
            raise Exception("No data in Dune - skipping this token pair...")
        else:
            Path(f"./data/{dir_name}").mkdir(parents=True, exist_ok=True)
            with open(filename, "a+") as f:
                for entry in formatted_response:
                    f.write(f"{entry["call_block_time"]} \n")
                    f.write(f"{entry["fee"]} \n")
    return formatted_response


# invariant: after execution, ptr points to the date that is out of the current window
def find_datapoints_inside_window(
    formatted_fee_response, 
    window_start_date: datetime,
    window_end_date: datetime, 
    # ptr: int = None
):
    ptr = 0
    closest_to_beginning_of_window = None
    closest_to_end_of_window = None

    closest_to_beginning_is_not_found = True
    closest_to_end_is_not_found = True
    

    while closest_to_beginning_is_not_found and ptr < len(formatted_fee_response):
        date = formatted_fee_response[ptr].get("call_block_time")
        if window_start_date <= date < window_end_date:
            closest_to_beginning_of_window = formatted_fee_response[ptr]
            closest_to_beginning_is_not_found = False
            ptr += 1
        elif date < window_start_date: 
            ptr += 1
        elif date >= window_end_date:
            return False, -1, -1, ptr  # skip window
    
    if ptr >= len(formatted_fee_response):
        return False, -1, -1, ptr  # it's ovah Anakin
    
    # invariant: closest to beginning of window from above is found 
    while closest_to_end_is_not_found and ptr < len(formatted_fee_response):
        date = formatted_fee_response[ptr].get("call_block_time")
        if window_start_date <= date < window_end_date:
            closest_to_end_of_window = formatted_fee_response[ptr]
            ptr += 1
        elif date >= window_end_date:   
            if closest_to_end_of_window is None:
                return False, -1, -1, ptr  # skip window
            else:
                closest_to_end_is_not_found = False
    
    if ptr >= len(formatted_fee_response):
        return False, -1, -1, ptr  # it's ovah Anakin x2
    
    if closest_to_beginning_of_window.get("call_block_time") == closest_to_end_of_window.get("call_block_time"):
        print(f"Window {window_start_date} - {window_end_date} has a degenerate case of same sampling time -- skipping..")
        return False, -1, -1, ptr # degenerate case -> when two different data points have same sampling time
    
    if closest_to_beginning_of_window.get("fee") == closest_to_end_of_window.get("fee"):
        print(f"Window {window_start_date} - {window_end_date} has a degenerate case of having the same fee (no useful txs in between two data points) -- skipping..")
        return False, -1, -1, ptr # degenerate case -> when there were no transactions in between two samples

    return True, closest_to_beginning_of_window, closest_to_end_of_window, ptr


def get_scaled_fee_diff(
    closest_entry_to_beginning_of_window,
    closest_entry_to_end_of_window,
    price_window_start: datetime,
    price_window_end: datetime    
):
    time_diff_between_fees: timedelta = closest_entry_to_end_of_window.get("call_block_time") - closest_entry_to_beginning_of_window.get("call_block_time")
    fee_diff = int(closest_entry_to_end_of_window.get("fee")) - int(closest_entry_to_beginning_of_window.get("fee")) 
  
    scaled_fee_diff = int(fee_diff * ((price_window_end - price_window_start).total_seconds()) / time_diff_between_fees.total_seconds())

    assert (scaled_fee_diff >= fee_diff)
    # print(f"Data points used: {closest_entry_to_beginning_of_window.get("call_block_time")} - {closest_entry_to_end_of_window.get("call_block_time")}")
    # print(f"Time difference between fees: {time_diff_between_fees}, scaled difference between fees: {scaled_fee_diff}")
    return scaled_fee_diff


def calculate_stats(
    formatted_fee_0_response,
    formatted_fee_1_response,
    ticker_0: str,
    ticker_1: str,
    window_period: timedelta
):
    def get_earliest_and_latest_fee_datapoints(formatted_fee_api_response):
        return formatted_fee_api_response[0]["call_block_time"], formatted_fee_api_response[-1]["call_block_time"]
    
    earliest_fee_0_date, latest_fee_0_date = get_earliest_and_latest_fee_datapoints(formatted_fee_0_response)
    earliest_fee_1_date, latest_fee_1_date = get_earliest_and_latest_fee_datapoints(formatted_fee_1_response)
    
    earliest_fee_datapoint_overall = min(earliest_fee_0_date, earliest_fee_1_date)
    stopping_time = min(latest_fee_0_date, latest_fee_1_date) # not perfect, but good enough


    # print(f"Earliest timestamp fee_0: {earliest_fee_good
    price_window_start = earliest_fee_datapoint_overall
    price_window_end = None
    

    # pprint(f"Earliest matching liquidity entry: {formatted_liquidity_response[row_pointer_liquidity_results]}")

    result = []
    fee_0_results_ptr = 0
    fee_1_results_ptr = 0
    
    while price_window_start < stopping_time: 
        price_window_end = price_window_start + window_period
        # print("-------------------------------")
        # print(f"Window: {price_window_start} - {price_window_end}")

        
        success_fee_0, closest_fee_0_entry_to_beginning_of_window, closest_fee_0_entry_to_end_of_window, fee_0_results_ptr = \
            find_datapoints_inside_window(
                formatted_fee_0_response,
                price_window_start, 
                price_window_end, 
                # fee_0_results_ptr
            )
        
        # not mutually exclusive events (in my understanding rn, might be wrong)
        assert(success_fee_0 == False or price_window_end <= formatted_fee_0_response[fee_0_results_ptr].get("call_block_time"))

        success_fee_1, closest_fee_1_entry_to_beginning_of_window, closest_fee_1_entry_to_end_of_window, fee_1_results_ptr = \
            find_datapoints_inside_window(
                formatted_fee_1_response,
                price_window_start,
                price_window_end,
                # fee_1_results_ptr
            )
        
        # not mutually exclusive events (in my understanding rn, might be wrong)
        assert (success_fee_1 == False or price_window_end <= formatted_fee_1_response[fee_1_results_ptr].get("call_block_time"))
        
        
        if success_fee_0 and success_fee_1:
            assert (price_window_start <= closest_fee_0_entry_to_beginning_of_window.get("call_block_time") < closest_fee_0_entry_to_end_of_window.get("call_block_time") < price_window_end)
            assert (price_window_start <= closest_fee_1_entry_to_beginning_of_window.get("call_block_time") < closest_fee_1_entry_to_end_of_window.get("call_block_time") < price_window_end)
            
            try:
                stats: PriceStats = fetch_price_statistics(ticker_0, ticker_1, price_window_start, price_window_end)
            except Exception:
                print(f"Skipping window {price_window_start}-{price_window_end} since CC API returns a price of 0.")
                price_window_start = price_window_start + timedelta(weeks=1)
                continue

            stats.fee_0_diff_window = get_scaled_fee_diff(
                closest_fee_0_entry_to_beginning_of_window,
                closest_fee_0_entry_to_end_of_window,
                price_window_start,
                price_window_end
            )

            stats.fee_1_diff_window = get_scaled_fee_diff(
                closest_fee_1_entry_to_beginning_of_window,
                closest_fee_1_entry_to_end_of_window,
                price_window_start,
                price_window_end
            )
            
            # print(stats)      
            
            result.append(stats)
        else:
            print(f"Window {price_window_start} - {price_window_end} skipped since not all stats can be collected!")

        price_window_start = price_window_start + timedelta(weeks=1)

        
    # print("-------------------------------")
    return result



if __name__ == "__main__":
    fees_to_liquidity: dict[timedelta, dict[str, list[float]]] = dict()
    fees_to_option_price: dict[timedelta, dict[str, list[float]]] = dict()
    for window_period in [
        timedelta(weeks=4),
        timedelta(weeks=6),
        timedelta(weeks=8),
    ]:
        with open("./data/tokens.cs", "r") as f: 
            fees_to_liquidity[window_period] = dict()
            fees_to_option_price[window_period] = dict()
            for line in f.readlines():
                text_tokens = line.strip().split(" ")
                if len(text_tokens) == 0 or text_tokens[0] == "//":
                    continue
                else:
                    ticker_0_id = text_tokens[0]
                    ticker_1_id = text_tokens[1]
                    ticker_0_contract_address = text_tokens[2] 
                    ticker_1_contract_address = text_tokens[3] 
                    bips = int(text_tokens[4])
                    chain = text_tokens[5]

                    print(f"Working on {ticker_0_id}/{ticker_1_id} ({bips} bips, {chain} chain) pair...")

                    fees_to_liquidity[window_period][f"{ticker_0_id}_{ticker_1_id}_{bips/10000}%_{chain}"] = []
                    fees_to_option_price[window_period][f"{ticker_0_id}_{ticker_1_id}_{bips/10000}%_{chain}"] = []


                    decimals_token_0 = None
                    decimals_token_1 = None
                    pool_address = None
                    query_fee_0 = None
                    query_fee_1 = None
                    #  TODO: strategy pattern
                    if chain == "ETH":
                        query_fee_0 = QUERY_ID_FEE_0_ETH
                        query_fee_1 = QUERY_ID_FEE_1_ETH
                        pool_address = fetch_pool_address(ticker_0_contract_address, ticker_1_contract_address, bips, WEB3_ETH_URL)
                        decimals_token_0 = fetch_token_decimals(ticker_0_contract_address, WEB3_ETH_URL)
                        decimals_token_1 = fetch_token_decimals(ticker_1_contract_address, WEB3_ETH_URL)
                    elif chain == "ARB":
                        query_fee_0 = QUERY_ID_FEE_0_ARB
                        query_fee_1 = QUERY_ID_FEE_1_ARB 
                        pool_address = fetch_pool_address(ticker_0_contract_address, ticker_1_contract_address, bips, WEB3_ARB_URL)
                        decimals_token_0 = fetch_token_decimals(ticker_0_contract_address, WEB3_ARB_URL)
                        decimals_token_1 = fetch_token_decimals(ticker_1_contract_address, WEB3_ARB_URL)
                    elif chain == "OPT":
                        query_fee_0 = QUERY_ID_FEE_0_OPT
                        query_fee_1 = QUERY_ID_FEE_1_OPT 
                        pool_address = fetch_pool_address(ticker_0_contract_address, ticker_1_contract_address, bips, WEB3_OPT_URL)
                        decimals_token_0 = fetch_token_decimals(ticker_0_contract_address, WEB3_OPT_URL)
                        decimals_token_1 = fetch_token_decimals(ticker_1_contract_address, WEB3_OPT_URL)
                    elif chain == "POLY":
                        query_fee_0 = QUERY_ID_FEE_0_POLY
                        query_fee_1 = QUERY_ID_FEE_1_POLY
                        pool_address = fetch_pool_address(ticker_0_contract_address, ticker_1_contract_address, bips, WEB3_POLYGON_URL)
                        decimals_token_0 = fetch_token_decimals(ticker_0_contract_address, WEB3_POLYGON_URL)
                        decimals_token_1 = fetch_token_decimals(ticker_1_contract_address, WEB3_POLYGON_URL)

                    try:
                        fee_0_result = fetch_dune_fee_data(
                            query_id=query_fee_0,
                            pool_address=pool_address,
                            filename=f"./data/{ticker_0_id}_{ticker_1_id}_{bips}_{chain}_univ3/fee0_{ticker_0_id}_{ticker_1_id}_{bips}_{chain}.txt",
                            dir_name=f"{ticker_0_id}_{ticker_1_id}_{bips}_{chain}_univ3"
                        )
                        fee_1_result = fetch_dune_fee_data(
                            query_id=query_fee_1,
                            pool_address=pool_address,
                            filename=f"./data/{ticker_0_id}_{ticker_1_id}_{bips}_{chain}_univ3/fee1_{ticker_0_id}_{ticker_1_id}_{bips}_{chain}.txt",
                            dir_name=f"{ticker_0_id}_{ticker_1_id}_{bips}_{chain}_univ3"
                        )
                    except Exception:
                        continue

                    statistics: list[PriceStats] = calculate_stats(
                        fee_0_result, 
                        fee_1_result,
                        ticker_0=ticker_0_id,
                        ticker_1=ticker_1_id,
                        window_period=window_period
                    )

                    print ("Required liquidity:")
                    for entry in statistics:
                        print((
                            f"Window start price:{entry.t0_to_t1_price_window_start} \n" 
                            f"Window min price: {entry.t0_to_t1_min_price} \n" 
                            f"Windows max price: {entry.t0_to_t1_max_price}"
                        ))
                        liquidity_needed_in_usd_equivalent = calculate_required_liquidity_usd(
                            token0_price_usd=entry.spot_price_window_start_token_0,
                            token1_price_usd=entry.spot_price_window_start_token_1,
                            price_range_lower_bound=convert_real_price_to_uniswap_price(entry.t0_to_t1_min_price, decimals_token_1 - decimals_token_0),
                            price_range_upper_bound=convert_real_price_to_uniswap_price(entry.t0_to_t1_max_price, decimals_token_1 - decimals_token_0),
                            uniswap_price=convert_real_price_to_uniswap_price(entry.t0_to_t1_price_window_start, decimals_token_1 - decimals_token_0),
                            decimals_token0=decimals_token_0,
                            decimals_token1=decimals_token_1
                        )
                        print(f"Window: {entry.window_start} - {entry.window_end}")
                        # print(f"USD liquidity:{liquidity_needed_in_usd_equivalent}")

                        fees_0_scaled = entry.fee_0_diff_window / ((10 ** decimals_token_0) * (2 ** 128))
                        fees_1_scaled = entry.fee_1_diff_window / ((10 ** decimals_token_1) * (2 ** 128))
    
                        # print(f"Fees per unit of liquidity token0: {fees_0_scaled}")
                        # print(f"Fees per unit of liquidity token1: {fees_1_scaled}")
                        
                        total_fees_earned_usd_equivalent = \
                            fees_0_scaled * entry.spot_price_window_end_token_0 + \
                            fees_1_scaled * entry.spot_price_window_end_token_1
                        
                        if fees_1_scaled > 0:
                            print(f"Fee ratio: {fees_0_scaled / fees_1_scaled}")
                        else:
                            raise Exception("Scaled fees for token 1 is 0!")
                        print(f"Total fees earned in USD: {total_fees_earned_usd_equivalent}")
                        print(f"Ratio (fee profits/liquidity): {total_fees_earned_usd_equivalent / liquidity_needed_in_usd_equivalent}")
                        if total_fees_earned_usd_equivalent / liquidity_needed_in_usd_equivalent <= 1: # don't insert outliers; technically possible but they break the graph flow
                            fees_to_liquidity[window_period][f"{ticker_0_id}_{ticker_1_id}_{bips/10000}%_{chain}"].append(total_fees_earned_usd_equivalent / liquidity_needed_in_usd_equivalent)


                        fetch_hourly_logarithmic_ratios(
                            base_token=ticker_0_id,
                            quote_token=ticker_1_id,
                            offset=timedelta(days=0), 
                            length_of_dataset=27000,
                            bips=bips,
                            chain=chain
                        )
                        log_of_ratios = read_from_file(
                            base_token=ticker_0_id,
                            quote_token=ticker_1_id,
                            bips=bips,
                            chain=chain
                        )                      
                        # pprint(log_of_ratios)
                        try:
                            realized_volatility = calculate_realized_volatility(
                                liquidity_provision_time=entry.window_start, 
                                log_of_ratios=log_of_ratios
                            )
                        except Exception as e:
                            print(e)
                            continue

                        print("Realized volatility:", realized_volatility)

                        # realized volatility vs implied volatility has max error of 30%; assume worst case for option price 
                        error_margin = 1.3  

                        option_price_usd = 0.4 * \
                                entry.spot_price_window_start_token_0 * \
                                    (((2 ** 96) / convert_real_price_to_uniswap_price(entry.t0_to_t1_min_price, decimals_token_1 - decimals_token_0)) - \
                                        ((2 ** 96) / convert_real_price_to_uniswap_price(entry.t0_to_t1_max_price, decimals_token_1 - decimals_token_0))) * \
                                            math.sqrt((entry.window_end - entry.window_start) / timedelta(days=365)) * \
                                                realized_volatility * error_margin / \
                                                    (10 ** decimals_token_0)
                        
                        #((2 ** 96) / convert_real_price_to_uniswap_price(entry.t0_to_t1_min_price, decimals_token_1 - decimals_token_0)) = 1 / P_l
                        # ((2 ** 96) / convert_real_price_to_uniswap_price(entry.t0_to_t1_max_price, decimals_token_1 - decimals_token_0)) = 1 / P_h
                        

                        option_price_usd_1_token = 0.4 * \
                            realized_volatility * \
                                entry.spot_price_window_start_token_0 * \
                                    math.sqrt((entry.window_end - entry.window_start) / timedelta(days=365))

                        print(f"Option price in USD for 1 liquidity: {option_price_usd}")
                        print(f"Option price in USD for 1 token: {option_price_usd_1_token}")
                        fees_to_option_ratio = total_fees_earned_usd_equivalent / option_price_usd 
                        if fees_to_option_ratio <= 7:
                            fees_to_option_price[window_period][f"{ticker_0_id}_{ticker_1_id}_{bips/10000}%_{chain}"].append(fees_to_option_ratio)
                        print(f"Fees to option ratio: {fees_to_option_ratio}")
                        print("-------------------------------")

            # visualize_token_groups(fees_to_option_price[window_period])

    # for window_period, entries in fees_to_liquidity.items(): 
    #     visualize_token_groups(fees_to_liquidity[window_period])
    
    for window_period, entries in fees_to_option_price.items():
        print(window_period)
        visualize_token_groups(fees_to_option_price[window_period], time_window=window_period)
        for key in fees_to_option_price[window_period].keys():
            print(key)
            print([float(x) for x in fees_to_option_price[window_period][key]])