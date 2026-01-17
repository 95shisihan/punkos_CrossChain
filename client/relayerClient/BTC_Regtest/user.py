from foundrycli import foundry_cli
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import json
import requests
import hashlib
import json
import binascii
from cryptos import *
from web3 import Web3

from bitcoinlib.services.bitcoind import BitcoindClient
from bitcoinlib.transactions import *
import json
import eth_account



private_key_list = [
    '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d',
    '0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a',
    '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6',
    '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a',
    '0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba',
    '0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e',
    '0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356',
    '0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97',
    '0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6']
private_key = private_key_list[5]
def big_small_end_convert(data):
    return binascii.hexlify(binascii.unhexlify(data)[::-1])
def load():
    """
    从配置文件中读取信息
    """
    with open('client/BTC_Regtest/transportContract.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global transport_contract_address
    transport_contract_address = save_dict1['deployedTo']
    with open('client/BTC_Regtest/configUser.json','r') as result_file:
        save_dict2 = json.load(result_file)
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict2['targetRPC']['host']+':'+str(save_dict2['targetRPC']['port'])
    global source_rpc_user
    source_rpc_user = save_dict2['bitcoinRPC']['user']
    global source_rpc_password
    source_rpc_password = save_dict2['bitcoinRPC']['password']
    global source_rpc_host
    source_rpc_host = save_dict2['bitcoinRPC']['host']
    global source_rpc_port
    source_rpc_port = save_dict2['bitcoinRPC']['port']
def generateSourceTx():
    base_url = 'http://'+source_rpc_user+':'+source_rpc_password+'@'+source_rpc_host+':'+ str(source_rpc_port)
    #print(base_url)
    bdc = BitcoindClient(base_url=base_url)
    #print(bdc.proxy.listunspent())
    txid='d3eb0a8c83d5d97aec2b16d161613ee560a34ffb73ef82e3a744682ee4758556'
    vout=0
    address='mymhZsG8GJxY7eKpRFMTVfW8pj8Ukui46k'
    input = Input(prev_txid=txid,output_n=vout)
    #print(input)
    output=Output(value=4999900000,address=address,network='testnet')
    #print(output)
    tx=Transaction(inputs=[input],outputs=[output])
    #print(tx)
    res = bdc.proxy.signrawtransaction(tx.raw_hex())['hex']
    txHash= bdc.proxy.decoderawtransaction(res)['txid']
    return (res,txHash)
def submitTask(signedTx,txHash):
    res = foundry_cli(f'cast send {transport_contract_address} "initTask(bytes)" {signedTx} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
    res = foundry_cli(f'cast call {transport_contract_address} "getTaskByNum(uint)(address,address,bytes32,uint256,uint256)" {0} --rpc-url {target_rpc_url}')
    print(res)
    res = foundry_cli(f'cast call {transport_contract_address} "getTaskByHash(bytes32)(address,address,bytes32,uint256,uint256)" {txHash} --rpc-url {target_rpc_url}')
    print(res)

if __name__ == "__main__":
    load()
    (signedTx,txHash) = generateSourceTx()
    #print(tx)
    submitTask(signedTx,txHash)