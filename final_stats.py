import numpy as np
from tabulate import tabulate

if __name__ == "__main__":    
    table_rows = None
    with open(f"./fee_to_option_price_data/data_4_weeks.txt", "r") as f:
        table_rows = len(f.readlines()) + 1
    table_cols = 4
   
    table = []
    for _ in range(table_rows):
        table.append([" "] * table_cols)
     
     
    for idx, number_of_weeks in enumerate([4, 6, 8]):
        print(f"Number of weeks: {number_of_weeks}")
        row = 1
        col = idx + 1
        table[0][col] = f"{number_of_weeks} weeks"
        with open(f"./fee_to_option_price_data/data_{number_of_weeks}_weeks.txt", "r") as f:
            lines = f.readlines()
            current_key = None
            for line in lines:
                tokens = line.strip().split(" ")
                current_key, fee_to_option_price_ratios = tokens[0], tokens[1:]
                fee_to_option_price_ratios = list(filter(lambda x: x != ' ' and x != '', fee_to_option_price_ratios))
                fee_to_option_price_ratios = list(filter(lambda x: x > 1, list(map(lambda x: float(x), fee_to_option_price_ratios))))
                
                min_fee = round(min(fee_to_option_price_ratios), 2) if len(fee_to_option_price_ratios) > 0 else "-"
                max_fee = round(max(fee_to_option_price_ratios), 2) if len(fee_to_option_price_ratios) > 0 else "
                
                print(f"Current pair: {current_key}")
                print(f"Min: {min_fee}")
                print(f"Max: {max_fee}")
                print(f"Windows that are profitable: {len(fee_to_option_price_ratios)}")
        
                table[row][0] = current_key
                table[row][col] = (min_fee, max_fee, len(fee_to_option_price_ratios))
                row += 1
        

    print(tabulate(table, tablefmt="latex"))