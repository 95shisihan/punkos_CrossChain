from foundrycli import foundry_cli
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import json


private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'

def load():
    """
    从配置文件中读取信息
    """
    with open('client/infoMultiChain.json','r') as result_file:
        save_dict1 = json.load(result_file)
    global multichain_contract_address
    multichain_contract_address = save_dict1['deployedTo']
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

def getBlockHeaderFromHeight(h):
    """
    向源链全节点查询某高度对应的区块头
    
    参数：
    h -- 区块高度

    返回值：
    区块头
    """
    rpc_connection = AuthServiceProxy(f"http://{source_rpc_user}:{source_rpc_password}@{source_rpc_host}:{source_rpc_port}")
    hashBlock = rpc_connection.getblockhash(h)
    #print(hashBlock)
    hexHeader = rpc_connection.getblockheader(hashBlock,False)
    #print(hexHeader)
    return hexHeader
def getBlockHashFromHeight(h):
    """
    向源链全节点查询某高度对应的区块哈希
    
    参数：
    h -- 区块高度

    返回值：
    区块哈希
    """
    rpc_connection = AuthServiceProxy(f"http://{source_rpc_user}:{source_rpc_password}@{source_rpc_host}:{source_rpc_port}")
    hashBlock = rpc_connection.getblockhash(h)
    return hashBlock
def getTopBlockHeight():
    """
    向源链全节点查询主链高度
    
    返回值：
    最大高度
    """
    rpc_connection = AuthServiceProxy(f"http://{source_rpc_user}:{source_rpc_password}@{source_rpc_host}:{source_rpc_port}")
    topHeight = rpc_connection.getblockchaininfo()['headers']
    return topHeight
def setGenesisHeight():
    return 0

def deployRelayContract():
    relay_contract_path = 'src/BTC_Regtest/BTC_RelayContract.sol:BTC_RelayContract'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --legacy')
    print(res)
    relay_contract_address = res['deployedTo']
    with open('client/BTC_Regtest/relayContract.json','w') as result_file:
        json.dump(res, result_file)
def submitGenesis():
    height = setGenesisHeight()
    hexHeader = getBlockHeaderFromHeight(height)  
    genesisParams = foundry_cli(f'cast --to-uint256 {height}')
    res = foundry_cli(f'cast send {relay_contract_address} "updateByUnion(address,bytes,bytes)" {multichain_contract_address} {hexHeader} {genesisParams} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
if __name__ == "__main__":
    load() 
    deployRelayContract()
    submitGenesis()

