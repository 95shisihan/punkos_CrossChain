from foundrycli import foundry_cli

import requests
import time
import sys
import json
import hashlib
import struct
from web3 import Web3

private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
def hash256(s):
    return hashlib.new('sha256',s).digest()
def double_hash256(s):
    return hash256(hash256(s))
def string_to_bytes(s):
    return bytes.fromhex(s)[::-1]
def long_to_bytes(n):
    return struct.pack("<L",n)
def load1():
    """
    从配置文件中读取信息
    """
    with open('client/infoMultiChain.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global multichain_contract_address
    multichain_contract_address = save_dict1['deployedTo']
    with open('client/BSV/config.json','r') as result_file:
        save_dict2 = json.load(result_file)['targetRPC']
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict2['host']+':'+str(save_dict2['port'])
def getBlockHeaderFromHeight(height,param):
    if param=='True':
        print("目前不支持RPC连接")
    else:
        return getBlockHeaderFromHeight_API(height)
def getBlockHeaderFromHeight_API(height):
    """
    向区块链浏览器查询某高度对应的区块头
    
    参数：
    h -- 区块高度

    返回值：
    区块头
    """
    url = "https://api.whatsonchain.com/v1/bsv/main/block/height/"+str(height)
    response = requests.get(url)
    block = response.json()
    blockinfo = {"version":0, "hashPrevBlock":0, "hashMerkleRoot":0, "time":0, "bits":0, "nonce":0,}
    blockinfo['version'] = block['version']
    blockinfo['hashPrevBlock'] = block['previousblockhash']
    blockinfo['hashMerkleRoot'] = block['merkleroot']
    blockinfo['time'] = block['time']
    blockinfo['bits'] = int(block['bits'],16)
    blockinfo['nonce'] = block['nonce']
    bytesHeader = long_to_bytes(blockinfo['version'])+string_to_bytes(blockinfo['hashPrevBlock'])+string_to_bytes(blockinfo['hashMerkleRoot'])+long_to_bytes(blockinfo['time'])+long_to_bytes(blockinfo['bits'])+long_to_bytes(blockinfo['nonce'])
    #blockHash =  ''.join(["%02x" % x for x in double_hash256(bytesHeader)[::-1]])
    #print(blockHash)
    #print(block['hash'])
    return Web3.to_hex(bytesHeader)
    
def getTopBlockHeight(param):
    if param=='True':
        print("目前不支持RPC连接")
    else:
        return getTopBlockHeight_API()
def getTopBlockHeight_API():
    """
    向区块链浏览器查询主链高度

    返回值：
    最大高度
    """
    url = "https://api.whatsonchain.com/v1/bsv/main/chain/info"
    response = requests.get(url)
    result = response.json()
    return result['blocks']
def setGenesisHeight(param):
    topHeight = getTopBlockHeight(param)
    genesisHeight = topHeight - topHeight % 2016
    return (genesisHeight)
def submitGenesis(param):
    height = setGenesisHeight(param)
    hexHeader = getBlockHeaderFromHeight(height,param) 
    genesisParams = foundry_cli(f'cast --to-uint256 {height}')
    print(genesisParams)
    res = foundry_cli(f'cast send {relay_contract_address} "updateByUnion(address,bytes,bytes)" {multichain_contract_address} {hexHeader} {genesisParams} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def deployRelayContract():
    relay_contract_path = 'src/BSV/BSV_RelayContract.sol:BSV_RelayContract'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --legacy')
    relay_contract_address = res['deployedTo']
    with open('client/BSV/relaycontract.json','w') as result_file:
        json.dump(res, result_file)
if __name__ == "__main__":
    #print(sys.argv[1])
    if sys.argv[1]=='1':
        print("目前不支持RPC连接")
    elif sys.argv[1]=='0': 
        load1()
        deployRelayContract()
        submitGenesis(False)
        #getBlockHeaderFromHeight_API(811076)
        #print(getTopBlockHeight_API())
    else:
        print("输入参数错误")

