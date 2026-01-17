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


def load():
    """
    从配置文件中读取信息
    """
    with open('client/BTC_Regtest/relayContract.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global relay_contract_address
    relay_contract_address = save_dict1['deployedTo']
    with open('client/BTC_Regtest/configUser.json','r') as result_file:
        save_dict2 = json.load(result_file)['targetRPC']
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict2['host']+':'+str(save_dict2['port'])
    with open('client/BTC_Regtest/configUser.json','r') as result_file:
        save_dict3 = json.load(result_file)['bitcoinRPC']
    global source_rpc_user
    source_rpc_user = save_dict3['user']
    global source_rpc_password
    source_rpc_password = save_dict3['password']
    global source_rpc_host
    source_rpc_host = save_dict3['host']
    global source_rpc_port
    source_rpc_port = save_dict3['port']
    with open('client/BTC_Regtest/transportContract.json','r') as result_file:
        save_dict4 = json.load(result_file)
    global transport_contract_address
    transport_contract_address = save_dict4['deployedTo']



def getTxListFromHeight(height):
    """
    向源链全节点查询某高度对应的区块头
    
    参数：
    h -- 区块高度

    返回值：
    区块头
    """
    rpc_connection = AuthServiceProxy(f"http://{source_rpc_user}:{source_rpc_password}@{source_rpc_host}:{source_rpc_port}")
    hashBlock = rpc_connection.getblockhash(height)
    block = rpc_connection.getblock(hashBlock)
    return (hashBlock,block['merkleroot'],block['tx'])


def generateSPVProof

def generateTxProofFromListToStr(siblings):
    str=''
    if len(siblings) == 0:
        return (str)
    else:
        depth = len(siblings)    
    for i in range(depth):
        str = str + siblings[i]    
    return (str)
def verifyTxOffChain(height,txIndex):
    (blockhash,txRoot,txList) = getTxListFromHeight(height)
    tree = mk_merkle_proof(txRoot,txList,txIndex) 
    print(tree)
def verifyTxOnchain1(height,txIndex):
    (blockHash,txRoot,txList) = getTxListFromHeight(height)
    tree = mk_merkle_proof(txRoot,txList,txIndex) 
    txHash = tree['tx_hash']
    merkleProof = txHash + generateTxProofFromListToStr(tree['siblings'])
    leafNode = foundry_cli(f'cast --to-uint256 {Web3.to_hex(txIndex)}')
    print(blockHash)
    res = foundry_cli(f'cast call {relay_contract_address} "verifyTxByUser(bytes,bytes,bytes)(bool)" {leafNode} {merkleProof} {blockHash} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def verifyTxOnchain2(height,txIndex):
    (blockHash,txRoot,txList) = getTxListFromHeight(height)
    tree = mk_merkle_proof(txRoot,txList,txIndex) 
    txHash = tree['tx_hash']
    merkleProof = txHash + generateTxProofFromListToStr(tree['siblings'])
    leafNode = foundry_cli(f'cast --to-uint256 {Web3.to_hex(txIndex)}')
    print(blockHash)
    res = foundry_cli(f'cast send {transport_contract_address} "verifyTxByUser(address,bytes,bytes,bytes)" {relay_contract_address} {leafNode} {merkleProof} {blockHash} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 999999')
    print(res)
    #print(txRoot)
if __name__ == "__main__":
    load()
    height=112
    txIndex=1
    verifyTxOnchain2(height,txIndex)
