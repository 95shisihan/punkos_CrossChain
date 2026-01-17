from foundrycli import foundry_cli
import time
import sys
import json
from web3 import Web3
import requests

private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
def loadDeploy():
    """
    部署合约前，从配置文件中读取信息
    """
    with open('client/infoMultiChain.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global multichain_contract_address
    multichain_contract_address = save_dict1['deployedTo']
    with open('client/BCH/config.json','r') as result_file:
            save_dict2 = json.load(result_file)['targetRPC']
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict2['host']+':'+str(save_dict2['port'])
def loadRelayer():
    """
    部署合约后，启动搬运客户端前，从配置文件中读取信息
    """
    with open('client/BCH/relaycontract.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global relay_contract_address
    relay_contract_address = save_dict1['deployedTo']
def deployRelayContract():
    relay_contract_path = 'src/BCH/BCH_RelayContract.sol:BCH_RelayContract'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key}')
    relay_contract_address = res['deployedTo']
    with open('client/BCH/relaycontract.json','w') as result_file:
        json.dump(res, result_file)
def deployOnchainLightClient():
    relay_contract_path = 'src/BCH/BCH_OnchainLightClient.sol:BCH_OLC'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key}')
    relay_contract_address = res['deployedTo']
    with open('client/BCH/relaycontract.json','w') as result_file:
        json.dump(res, result_file)
def getGenesisParams():
    """
    返回两个参数，与/src/cross-std/OnchainLightClient.sol的接口函数setGenesisByUnion(bytes calldata genesisHeader, bytes calldata params)的输入参数对应,参数类型为bytes
    """
    height = setGenesisHeight()
    hexHeader = getBlockHeaderFromHeight(height)
    genesisParams = foundry_cli(f'cast --to-uint256 {height}')
    return (hexHeader,genesisParams)
def startOnchainLightClient():
    (genesisHeader,params) = getGenesisParams()
    res = foundry_cli(f'cast send {relay_contract_address} "setGenesisByUnion(bytes,bytes)" {genesisHeader} {params} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def startRelayContract():
    (genesisHeaderBytes,paramsBytes) = getGenesisParams()
    res = foundry_cli(f'cast send {relay_contract_address} "updateByUnion(address,bytes,bytes)" {multichain_contract_address} {Web3.to_hex(genesisHeaderBytes)} {Web3.to_hex(paramsBytes)} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def RelayClientForOnchainLightClient():
    heightToRelay = getTopShadowHeight() + 1
    print(heightToRelay)
    hexHeader = getBlockHeaderFromHeight(heightToRelay)
    res = foundry_cli(f'cast send {relay_contract_address} "submitNewHeaderByRelayer(bytes)" {hexHeader} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 999999' )#
    #res = foundry_cli(f'cast call {deployed_contract_address} "caculateHeaderHash(bytes)" {hexHeader} --rpc-url {rpc_url} --private-key {private_key} --gas-limit 9999999' )#
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
def RelayClient():
    heightToRelay = getTopShadowHeight() + 1
    print(heightToRelay)
    heightToCommit = heightToRelay + 1
    hexHeaderToRelay = getBlockHeaderFromHeight(heightToRelay)
    hexHeaderToCommit = getBlockHeaderFromHeight(heightToCommit)
    print("成功获取源链数据！")
    #curHash = Web3.to_hex(hexstr=getBlockHashFromHeight(heightToCommit,param))
    curHash = foundry_cli(f'cast --to-uint256 {getBlockHashFromHeight(heightToCommit)}')
    #print(curHash)
    value = commitNewHeader(hexHeaderToCommit,eth_account.Account.from_key(private_key=private_key))
    print("准备向链上提交数据！")
    res = foundry_cli(f'cast send {relay_contract_address} "submitCommitedHeaderByRelayer(bytes,bytes32,bytes32)" {hexHeaderToRelay} {curHash} {value} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 999999' )#
    #res = foundry_cli(f'cast call {deployed_contract_address} "caculateHeaderHash(bytes)" {hexHeader} --rpc-url {rpc_url} --private-key {private_key} --gas-limit 9999999' )#
    #print(res)
    #print(heightContract+1)    

def getBlockHeaderFromHeight(height):
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

def getTopBlockHeight():
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
def setGenesisHeight():
    topHeight = getTopBlockHeight()
    genesisHeight = topHeight - 1
    return (genesisHeight)
def getTopShadowHeight():
    """
    向中继合约查询影子链高度
    
    返回值：
    影子链高度
    """
    res = foundry_cli(f'cast call {relay_contract_address} "getHeightToRelay()(uint)" --rpc-url {target_rpc_url}')
    return (res)

if __name__ == "__main__":
    if sys.argv[1]=='1': #测试ABC_RelayContract.sol
        loadDeploy()
        deployRelayContract()
        startRelayContract()
        loadRelayer()
    elif sys.argv[1]=='0': #测试ABC_OnchainLightClient.sol
        print("Test OLC!")
        loadDeploy()
        #deployRelayContract()
        loadRelayer()
        #startOnchainLightClient()
        while True:
            RelayClientForOnchainLightClient()
    else:
        print("输入参数错误！")



