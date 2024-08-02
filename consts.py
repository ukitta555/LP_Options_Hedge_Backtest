import os
from dotenv import load_dotenv

load_dotenv()

QUERY_ID_FEE_0 = 3932547
QUERY_ID_FEE_1 = 3935322
QUERY_ID_LIQUIDITY = 3945498

ETH_CC_ID = "ETH"
USD_CC_ID = "USD"

DUNE_API_KEY = os.getenv("DUNE_API_KEY")
assert DUNE_API_KEY is not None

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
assert CRYPTOCOMPARE_API_KEY is not None

ALCHEMY_WEB3_KEY = os.getenv("ALCHEMY_WEB3_KEY")
assert ALCHEMY_WEB3_KEY is not None

