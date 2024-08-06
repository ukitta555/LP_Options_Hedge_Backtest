import json
import requests
from web3 import Web3
from consts import ALCHEMY_WEB3_KEY
from abi import uniswap_v3_factory_abi




def fetch_token_decimals(token_address: str, web3_api_url: str):
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "alchemy_getTokenMetadata",
        "params": [token_address]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    response = requests.post(
        url=web3_api_url, 
        json=payload, 
        headers=headers
    )
    if response.status_code == 200:
        deserialized_response = json.loads(response.text)
        return deserialized_response["result"]["decimals"]
    else:
        raise Exception("Bad Alchemy API response... Stopping the execution since Alchemy shouldn't fail!")
    

def fetch_pool_address(token_0_address: str, token_1_address: str, bips: int, web3_api_url: str):
    w3 = Web3(Web3.HTTPProvider(web3_api_url))

    uni_v3_factory_contract_address = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    UniswapV3Factory = w3.eth.contract(
        address=uni_v3_factory_contract_address,
        abi=uniswap_v3_factory_abi
    )
    
    result = UniswapV3Factory.functions.getPool(
        token_0_address,
        token_1_address,
        bips
    ).call()

    print(f"Pool address: {result}")
    return result
