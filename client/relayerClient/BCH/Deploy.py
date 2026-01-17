from foundrycli import foundry_cli

import requests
import time
import sys
import json

private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
def load1():
    """
    从配置文件中读取信息
    """
    with open('client/infoMultiChain.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global multichain_contract_address
    multichain_contract_address = save_dict1['deployedTo']
    with open('client/BCH/config.json','r') as result_file:
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
    url = "https://api.blockchair.com/bitcoin-cash/raw/block/"+str(height)
    response = requests.get(url)
    result = response.json()['data']
    if height==0 :
        return result[0]['raw_block'][0:160]
    else:
        return result[str(height)]['raw_block'][0:160]
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
    url = "https://api.blockchair.com/bitcoin-cash/stats"
    response = requests.get(url)
    result = response.json()['data']
    return result['best_block_height']
def setGenesisHeight(param):
    topHeight = getTopBlockHeight(param)
    genesisHeight = topHeight - 1
    return (genesisHeight)
def submitGenesis(param):
    height = setGenesisHeight(param)
    hexHeader = getBlockHeaderFromHeight(height,param) 
    genesisParams = foundry_cli(f'cast --to-uint256 {height}')
    print(genesisParams)
    res = foundry_cli(f'cast send {relay_contract_address} "updateByUnion(address,bytes,bytes)" {multichain_contract_address} {hexHeader} {genesisParams} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def deployRelayContract():
    relay_contract_path = 'src/BCH/BCH_RelayContract.sol:BCH_RelayContract'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --legacy')
    relay_contract_address = res['deployedTo']
    with open('client/BCH/relaycontract.json','w') as result_file:
        json.dump(res, result_file)
if __name__ == "__main__":
    #print(sys.argv[1])
    if sys.argv[1]=='1':
        print("目前不支持RPC连接")
    elif sys.argv[1]=='0': 
        load1()
        deployRelayContract()
        submitGenesis(False)
    else:
        print("输入参数错误")

