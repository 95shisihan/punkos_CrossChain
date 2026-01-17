from foundrycli import foundry_cli
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import json
import eth_account
from web3 import Web3
import requests
import os
import sys
import hashlib
import struct

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
    with open('client/BSV/relaycontract.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global relay_contract_address
    relay_contract_address = save_dict1['deployedTo']
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
def getBlockHashFromHeight(height,param):
    if param=='True':
        print("目前不支持RPC连接")
    else:
        return getBlockHashFromHeight_API(height)
def getBlockHashFromHeight_API(height):
    """
    向区块链浏览器查询某高度对应的区块哈希
    
    参数：
    height -- 区块高度

    返回值：
    区块哈希
    """
    url = "https://api.whatsonchain.com/v1/bsv/main/block/height/"+str(height)
    response = requests.get(url)
    block = response.json()
    return(block['hash'])
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
def getMultiChainContractAddress():
    """
    向中继合约查询多链管理合约地址
    
    返回值：
    多链管理合约地址
    """
    res = foundry_cli(f'cast call {relay_contract_address} "getMultiChainContractAddress()(address)" --rpc-url {target_rpc_url}')
    return(res)
def getTopShadowHeight():
    """
    向中继合约查询影子链高度
    
    返回值：
    影子链高度
    """
    res = foundry_cli(f'cast call {relay_contract_address} "getTopHeight()(uint)" --rpc-url {target_rpc_url}')
    return(res)
def ifShouldRelay(param):
    while True:
        heightInSource = getTopBlockHeight(param)
        heightToRelay = getTopShadowHeight() + 1
        #print(heightToRelay)
        if (heightInSource > heightToRelay):
            #print(heightToRelay)
            return (heightToRelay)
        else:
            print("No New BCH Header To Realy!")
            time.sleep(10)
def commitNewHeader(hexHeader,relayer):
    """
    生成搬运工对区块头的承诺
    
    参数：
    hexHeader -- 区块头
    relayer -- 搬运工账户

    返回值：
    承诺值
    """
    typeList=['bytes','address']
    valueList= []
    valueList.append(Web3.to_bytes(hexstr = hexHeader))
    valueList.append(relayer.address)
    hash = Web3.solidity_keccak(typeList,valueList)
    return Web3.to_hex(hash)
def startRelayer(param):
    heightToRelay = ifShouldRelay(param)
    print(heightToRelay)
    heightToCommit = heightToRelay + 1
    hexHeaderToRelay = getBlockHeaderFromHeight(heightToRelay,param)
    hexHeaderToCommit = getBlockHeaderFromHeight(heightToCommit,param)
    print("成功获取源链数据！")
    #curHash = Web3.to_hex(hexstr=getBlockHashFromHeight(heightToCommit,param))
    curHash = foundry_cli(f'cast --to-uint256 {getBlockHashFromHeight(heightToCommit,param)}')
    #print(curHash)
    value = commitNewHeader(hexHeaderToCommit,eth_account.Account.from_key(private_key=private_key))
    print("准备向链上提交数据！")
    res = foundry_cli(f'cast send {relay_contract_address} "submitCommitedHeaderByRelayer(bytes,bytes32,bytes32)" {hexHeaderToRelay} {curHash} {value} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 999999' )#
    #res = foundry_cli(f'cast call {deployed_contract_address} "caculateHeaderHash(bytes)" {hexHeader} --rpc-url {rpc_url} --private-key {private_key} --gas-limit 9999999' )#
    #print(res)
    #print(heightContract+1)
def queryReward(multichain_contract_address):
    res = foundry_cli(f'cast call {multichain_contract_address} "balanceOf(address)(uint256)" {eth_account.Account.from_key(private_key=private_key).address} --rpc-url {target_rpc_url}')
    print(res)
def queryCurEpoch():
    res = foundry_cli(f'cast call {relay_contract_address} "getCurEpoch()(uint)" --rpc-url {target_rpc_url}')
    return(res)
    
def relayClient():
    #multichain_contract_address = getMultiChainContractAddress()
    #queryReward(multichain_contract_address)
    curEpoch = queryCurEpoch()
    while True:
        try:
            startRelayer()
            newEpoch = queryCurEpoch()
            if(newEpoch>curEpoch):
                time.sleep(2)
                #queryReward(multichain_contract_address)
                curEpoch = newEpoch
            time.sleep(1)
        except Exception as e:
            print("错误：",e)
            time.sleep(5)
def testRelayClient(param):
    while True:
        try:
            startRelayer(param)
        except Exception as e:
            print("错误：",e)
            time.sleep(5)
if __name__ == "__main__":
    #print(sys.argv[1])
    if sys.argv[1]=='1':
        print("目前不支持RPC连接")
    elif sys.argv[1]=='0': 
        load1()
        testRelayClient(False)
    else:
        print("输入参数错误")
