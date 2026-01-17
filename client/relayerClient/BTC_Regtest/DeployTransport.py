from foundrycli import foundry_cli
import time
import json
from web3 import Web3
import requests
import sys


private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
def load():
    """
    从配置文件中读取信息
    """
    with open('client/BTC_Regtest/configUnion.json','r') as result_file:
        save_dict = json.load(result_file)['targetRPC']
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict['host']+':'+str(save_dict['port'])
def deployTransprtContract():
    transport_contract_path = 'src/BTC_Regtest/BTC_Transport.sol:BTC_Transport'
    global transport_contract_address
    res = foundry_cli(f'forge create {transport_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --legacy')
    transport_contract_address = res['deployedTo']
    with open('client/BTC_Regtest/transportContract.json','w') as result_file:
        json.dump(res, result_file)
if __name__ == "__main__":
    load()
    deployTransprtContract()