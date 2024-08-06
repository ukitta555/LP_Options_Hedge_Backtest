import os
from dotenv import load_dotenv

load_dotenv()

QUERY_ID_FEE_0_ETH = 3932547
QUERY_ID_FEE_1_ETH = 3935322

QUERY_ID_FEE_0_ARB = 3966931
QUERY_ID_FEE_1_ARB = 3966924

QUERY_ID_FEE_0_OPT = 3967063
QUERY_ID_FEE_1_OPT = 3967064

QUERY_ID_FEE_0_POLY = 3967108
QUERY_ID_FEE_1_POLY = 3967109


QUERY_ID_LIQUIDITY = 3945498

ETH_CC_ID = "ETH"
USD_CC_ID = "USD"

DUNE_API_KEY = os.getenv("DUNE_API_KEY")
assert DUNE_API_KEY is not None

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
assert CRYPTOCOMPARE_API_KEY is not None

ALCHEMY_WEB3_KEY = os.getenv("ALCHEMY_WEB3_KEY")
assert ALCHEMY_WEB3_KEY is not None



WEB3_ETH_URL = f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_WEB3_KEY}'
WEB3_ARB_URL = f'https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_WEB3_KEY}'
WEB3_OPT_URL = f'https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_WEB3_KEY}'
WEB3_POLYGON_URL = f'https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_WEB3_KEY}'
