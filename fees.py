from datetime import datetime, timedelta
from pprint import pprint
from dateutil import rrule
from dune_client.client import DuneClient
import calendar
import os
from api import PriceStats, fetch_price_statistics
from consts import DUNE_API_KEY, ETH_CC_ID, QUERY_ID_FEE_0, QUERY_ID_FEE_1, QUERY_ID_LIQUIDITY, USD_CC_ID
import math

from utils import format_cached_dune_response, format_dune_fee_query

dune = DuneClient(DUNE_API_KEY)

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
    # print(type(L), type(P))

    total_usd_token0 = ((L / P - L / P_h) * P_0) / (10 ** decimals_token0)
    total_usd_token1 = ((L * P - L * P_l) * P_1) / (10 ** decimals_token1)
    
    return total_usd_token0 + total_usd_token1  

def convert_real_price_to_uniswap_price(
    real_price: float,
    decimals: int, 
) -> int:
    return int(math.sqrt(real_price * (10 ** decimals)))


# assuming first data points differ by a couple of months
def trim_fee_results(fee_0_result, fee_1_result):
    
    # trim left side
    if fee_1_result[0]["call_block_time"] < fee_0_result[0]["call_block_time"] and fee_1_result[0]["call_block_time"].month != fee_0_result[0]["call_block_time"].month:
        fee_1_result = list(
            filter(
                lambda x: x["call_block_time"] >= fee_0_result[0]["call_block_time"], 
                fee_1_result
            )
        )
    elif fee_1_result[0]["call_block_time"] > fee_0_result[0]["call_block_time"] and fee_1_result[0]["call_block_time"].month != fee_0_result[0]["call_block_time"].month:
        fee_0_result = list(
            filter(
                lambda x: x["call_block_time"] >= fee_1_result[0]["call_block_time"], 
                fee_0_result
            )
        )

    # trim right side
    if fee_0_result[-1]["call_block_time"] < fee_1_result[-1]["call_block_time"] and fee_0_result[-1]["call_block_time"].month != fee_1_result[-1]["call_block_time"].month:
        fee_1_result = list(
            filter(
                lambda x: x["call_block_time"] <= fee_0_result[-1]["call_block_time"], 
                fee_1_result
            )
        )
    elif fee_1_result[-1]["call_block_time"] < fee_0_result[-1]["call_block_time"] and fee_0_result[-1]["call_block_time"].month != fee_1_result[-1]["call_block_time"].month:
        fee_0_result = list(
            filter(
                lambda x: x["call_block_time"] <= fee_1_result[-1]["call_block_time"], 
                fee_0_result
            )
        )
    
    return fee_0_result, fee_1_result

def fetch_dune_fee_data(query_id: int, pool_address: str, filename: str):
    formatted_response = []
    try:
        with open(filename, "r+") as f:
            line_no = 0
            lines = f.readlines()
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
        formatted_response = list(map(format_dune_fee_query, raw_fee_query_result.result.rows))
        with open(filename, "a+") as f:
            for entry in formatted_response:
                f.write(f"{entry["call_block_time"]} \n")
                f.write(f"{entry["fee"]} \n")
    return formatted_response


def fetch_liquidity_from_dune(query_id, filename):
    formatted_response = []
    try:
        with open(filename, "r+") as f:
            line_no = 0
            lines = f.readlines()
            while line_no < len(lines):
                entry = dict()
                entry["call_block_time"] = lines[line_no].strip()
                line_no += 1
                entry["liquidity"] = lines[line_no].strip()
                line_no += 1
                formatted_response.append(entry)
            formatted_response = list(map(format_cached_dune_response, formatted_response))
    except FileNotFoundError:
        print("Liquidity data file not found, fetching from Dune Analytics...")
        raw_liquidity_query_result = dune.get_latest_result(query_id)
        formatted_response = list(map(format_dune_fee_query, raw_liquidity_query_result.result.rows))
        with open(filename, "a+") as f:
            for entry in formatted_response:
                f.write(f"{entry["call_block_time"]} \n")
                f.write(f"{entry["liquidity"]} \n")
    return formatted_response


def find_closest_entry_to_end_of_window(
    formatted_fee_response, 
    window_end_date, 
    row_pointer_fee_results
):
    while True:
        date = formatted_fee_response[row_pointer_fee_results].get("call_block_time")
        if date < window_end_date:
            closest_to_end_of_month_window = formatted_fee_response[row_pointer_fee_results]
            row_pointer_fee_results += 1
        else:    
            break
    return closest_to_end_of_month_window, row_pointer_fee_results


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
    print(f"Time difference between fees: {time_diff_between_fees}, scaled difference between fees: {scaled_fee_diff}")
    return scaled_fee_diff


def calculate_stats(
    formatted_fee_0_response,
    formatted_fee_1_response,
):
    earliest_fee_0_date, latest_fee_0_date = formatted_fee_0_response[0]["call_block_time"], formatted_fee_0_response[-1]["call_block_time"]
    
    earliest_fee_0_month_start = earliest_fee_0_date.replace(day=1, hour=0, minute=0, second=0)

    _, end_of_month_day_latest_fee_0 = calendar.monthrange(latest_fee_0_date.year, latest_fee_0_date.month) # fetch last day of the month for the last fee
    latest_fee_0_month_end = latest_fee_0_date.replace(day=end_of_month_day_latest_fee_0)

    print(f"Earliest timestamp: {earliest_fee_0_date}")
    print(f"Latest timestamp: {latest_fee_0_date}")
    print("----------------------------")
    print(f"Earliest fee month start: {earliest_fee_0_month_start}")
    print(f"Latest fee month end: {latest_fee_0_month_end}")
    print("----------------------------")
   
    closest_fee_0_entry_to_beginning_of_window = None
    closest_fee_0_entry_to_end_of_window = None
    closest_fee_1_entry_to_beginning_of_window = None
    closest_fee_1_entry_to_end_of_window = None

    price_window_start = earliest_fee_0_month_start
    price_window_end = None
    

    # pprint(f"Earliest matching liquidity entry: {formatted_liquidity_response[row_pointer_liquidity_results]}")

    result = []
    row_pointer_fee_0_results = 0
    row_pointer_fee_1_results = 0

    # assuming that fee0 and fee1 data points both have the same starting and ending months, can use the date range of fee_0
    for window_end_date in list(rrule.rrule(rrule.MONTHLY, dtstart=earliest_fee_0_month_start, until=latest_fee_0_month_end))[1:]:
        print("!!!!!!!!!!!!!!!!!!!!!")
        print(f"Window end date: {window_end_date}")
        price_window_end = window_end_date

        closest_fee_0_entry_to_beginning_of_window = formatted_fee_0_response[row_pointer_fee_0_results]
        closest_fee_1_entry_to_beginning_of_window = formatted_fee_1_response[row_pointer_fee_1_results]
        
        closest_fee_0_entry_to_end_of_window, row_pointer_fee_0_results = find_closest_entry_to_end_of_window(
            formatted_fee_0_response, 
            window_end_date, 
            row_pointer_fee_0_results
        ) 

        closest_fee_1_entry_to_end_of_window, row_pointer_fee_1_results = find_closest_entry_to_end_of_window(
            formatted_fee_1_response,
            window_end_date,
            row_pointer_fee_1_results
        )


        
        stats: PriceStats = fetch_price_statistics(USD_CC_ID, ETH_CC_ID, price_window_start, price_window_end)

        stats.fee_0_diff_month_window = get_scaled_fee_diff(
            closest_fee_0_entry_to_beginning_of_window,
            closest_fee_0_entry_to_end_of_window,
            price_window_start,
            price_window_end
        )

        stats.fee_1_diff_month_window = get_scaled_fee_diff(
            closest_fee_1_entry_to_beginning_of_window,
            closest_fee_1_entry_to_end_of_window,
            price_window_start,
            price_window_end
        )
        
        print(stats)      
        
        result.append(stats)

        price_window_start = price_window_end

        
    print("-------------------------------")
    return result



if __name__ == "__main__":
    ticker_0_id = USD_CC_ID
    ticker_1_id = ETH_CC_ID

    fee_0_result = fetch_dune_fee_data(
        query_id=QUERY_ID_FEE_0,
        pool_address="",
        ticker=ticker_0_id,
        filename=f"./data/{ticker_0_id}_{ticker_1_id}_univ3/fee0_{ticker_0_id}_{ticker_1_id}.txt"
    )
    fee_1_result = fetch_dune_fee_data(
        query_id=QUERY_ID_FEE_1,
        pool_address="",
        ticker=ticker_1_id,
        filename=f"./data/{ticker_0_id}_{ticker_1_id}_univ3/fee1_{ticker_0_id}_{ticker_1_id}.txt"
    )
    fee_0_result, fee_1_result = trim_fee_results(fee_0_result, fee_1_result)
    
    # if these assertions fail, need a more complex trimming mechanism because of sparse data
    assert (fee_0_result[0]["call_block_time"].month == fee_1_result[0]["call_block_time"].month)
    assert (fee_0_result[-1]["call_block_time"].month == fee_1_result[-1]["call_block_time"].month)  
    print(fee_0_result[0]["call_block_time"], fee_1_result[0]["call_block_time"])
    print(fee_0_result[-1]["call_block_time"], fee_1_result[-1]["call_block_time"])

    statistics: list[PriceStats] = calculate_stats(fee_0_result, fee_1_result)

    # (?)TODO: change the dune_fee_data function so that the CC API fetches the price relative to the USD/<TOKEN> pair

    # for each month, calculate how much liquidity (in USD) we should put as an LP
    print ("required liquidity:")
    for monthly_entry in statistics:
        print("\\\\\\\\")
        liquidity_needed_in_usd_equivalent = calculate_required_liquidity_usd(
            token0_price_usd=1,
            token1_price_usd=1 / monthly_entry.spot_price_window_start,
            price_range_lower_bound=convert_real_price_to_uniswap_price(monthly_entry.min_price, 12),
            price_range_upper_bound=convert_real_price_to_uniswap_price(monthly_entry.max_price, 12),
            uniswap_price=convert_real_price_to_uniswap_price(monthly_entry.spot_price_window_start, 12),
            decimals_token0=6,
            decimals_token1=18
        )
        print(f"USD liquidity:{liquidity_needed_in_usd_equivalent}")

        monthly_fees_0_scaled = monthly_entry.fee_0_diff_month_window / ((10 ** 6) * (2 ** 128))
        monthly_fees_1_scaled = monthly_entry.fee_1_diff_month_window / ((10 ** 18) * (2 ** 128))

        print(f"Fees per unit of liquidity token0: {monthly_fees_0_scaled}")
        print(f"Fees per unit of liquidity token1: {monthly_fees_1_scaled}")
        
        total_fees_earned_usd_equivalent = monthly_fees_0_scaled * 1 + monthly_fees_1_scaled * (1 / monthly_entry.spot_price_window_start)
        
        print(f"Fee ratio: {monthly_fees_0_scaled / monthly_fees_1_scaled}")
        print(f"Total fees earned in USD: {total_fees_earned_usd_equivalent}")
        print(f"Ratio (fee profits/liquidity): {total_fees_earned_usd_equivalent / liquidity_needed_in_usd_equivalent}")
        print("\\\\\\\\")

    # TODO: calculate option price

    