import numpy as np


if __name__ == "__main__":
    for number_of_weeks in [4, 6, 8]:
        print(f"Number of weeks: {number_of_weeks}")
        with open(f"./fee_to_option_price_data/data_{number_of_weeks}_weeks.txt", "r") as f:
            lines = f.readlines()
            current_key = None
            for line in lines:
                tokens = line.strip().split(" ")
                current_key, fee_to_option_price_ratios = tokens[0], tokens[1:]
                fee_to_option_price_ratios = list(filter(lambda x: x != ' ' and x != '', fee_to_option_price_ratios))
                fee_to_option_price_ratios = list(map(lambda x: float(x), fee_to_option_price_ratios))
                print(f"Current pair: {current_key}")
                print(f"Min: {min(fee_to_option_price_ratios)}")
                print(f"Max: {max(fee_to_option_price_ratios)}")
                print(f"Windows that are profitable: {len(list(filter(lambda x: x > 1, fee_to_option_price_ratios)))}")
