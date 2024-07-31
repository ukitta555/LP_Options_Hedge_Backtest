from datetime import datetime


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