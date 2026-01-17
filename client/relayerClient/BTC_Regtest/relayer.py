from foundrycli import foundry_cli
import time
import json
import eth_account
from web3 import Web3
import sys
sys.path.append(".")
import sourcePlugin.BTC.BTC_Plugin as BTC_Plugin


def loadHub():
    """
    从配置文件中读取信息
    """
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    global relay_contract_address
    relay_contract_address = save_dict[source_name]['relayAddress']
    global target_rpc_url
    target_rpc_url = save_dict['HubchainManager']['rpc']
    mode = save_dict['HubchainManager']['mode']
    with open(config_path,'r') as result_file:
        save_dict = json.load(result_file)
    global private_key
    private_key = save_dict['targetRPC']['relayerAccount'][mode]['private']
    save_dict['targetRPC']['mode'] = mode
    save_dict['targetRPC']['rpc'] = target_rpc_url
    data = json.dumps(save_dict, indent = 1)
    with open(config_path,'w',newline='\n') as result_file:
        result_file.write(data)
def loadSource():
    """
    从配置文件中读取信息
    """
    with open(config_path,'r') as result_file:
        save_dict = json.load(result_file)
    source_rpc_user = save_dict['bitcoinRPC']['user']
    source_rpc_password = save_dict['bitcoinRPC']['password']
    source_rpc_host = save_dict['bitcoinRPC']['host']
    source_rpc_port = save_dict['bitcoinRPC']['port']
    rpc_connection = BTC_Plugin.setRPCConnection(source_rpc_user,source_rpc_password,source_rpc_host,source_rpc_port)
    return rpc_connection

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
def ifShouldRelay_RPC(rpc_connection):
    while True:
        heightInSource = BTC_Plugin.getTopBlockHeight_RPC(rpc_connection)
        heightToRelay = getTopShadowHeight() + 1
        if (heightInSource > heightToRelay):
            return heightToRelay
        else:
            print("No New BTC Header To Realy!")
            time.sleep(10)
def ifShouldRelay_API():
    while True:
        heightInSource = BTC_Plugin.getTopBlockHeight_API()
        heightToRelay = getTopShadowHeight() + 1
        if (heightInSource > heightToRelay):
            return heightToRelay
        else:
            print("No New BTC Header To Realy!")
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
def getSourceData_RPC(rpc_connection):
    heightToRelay = ifShouldRelay_RPC(rpc_connection)
    print("影子账本当前高度:",heightToRelay)
    heightToCommit = heightToRelay + 1
    hexHeaderToRelay = BTC_Plugin.getBlockHeaderFromHeight_RPC(rpc_connection,heightToRelay)
    hexHeaderToCommit = BTC_Plugin.getBlockHeaderFromHeight_RPC(rpc_connection,heightToCommit)
    curHash = BTC_Plugin.getBlockHashFromHeight_RPC(rpc_connection,heightToCommit)
    print("成功获取源链数据,开始更新影子账本！")
    return (hexHeaderToRelay,hexHeaderToCommit,curHash)
def getSourceData_API():
    heightToRelay = ifShouldRelay_API()
    print("影子账本当前高度:",heightToRelay)
    heightToCommit = heightToRelay + 1
    hexHeaderToRelay = BTC_Plugin.getBlockHeaderFromHeight_API(heightToRelay)
    hexHeaderToCommit = BTC_Plugin.getBlockHeaderFromHeight_API(heightToCommit)
    curHash = BTC_Plugin.getBlockHashFromHeight_API(heightToCommit)
    print("成功获取源链数据,开始更新影子账本！")
    return (hexHeaderToRelay,hexHeaderToCommit,curHash)
def submitSourceData(hexHeaderToRelay,hexHeaderToCommit,curHash):
    value = commitNewHeader(hexHeaderToCommit,eth_account.Account.from_key(private_key=private_key))
    res = foundry_cli(f'cast send {relay_contract_address} "submitCommitedHeaderByRelayer(bytes,bytes32,bytes32)" {hexHeaderToRelay} {curHash} {value} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 999999' )
    print("影子账本更新成功")
def testRelayClient_RPC():
    rpc_connection = loadSource()
    while True:
        try:
            (hexHeaderToRelay,hexHeaderToCommit,curHash) = getSourceData_RPC(rpc_connection)
            submitSourceData(hexHeaderToRelay,hexHeaderToCommit,curHash)
        except Exception as e:
            print("错误：",e)
            time.sleep(5)
def startRelayerClient_RPC():
    rpc_connection = loadSource()
    while True:
        try:
            (hexHeaderToRelay,hexHeaderToCommit,curHash) = getSourceData_RPC(rpc_connection)
            submitSourceData(hexHeaderToRelay,hexHeaderToCommit,curHash)
        except Exception as e:
            print("错误：",e)
            time.sleep(5)
def startRelayerClient_API():
    while True:
        try:
            (hexHeaderToRelay,hexHeaderToCommit,curHash) = getSourceData_API()
            submitSourceData(hexHeaderToRelay,hexHeaderToCommit,curHash)
        except Exception as e:
            print("错误：",e)
            time.sleep(5)
if __name__ == "__main__":
    
    global source_name
    source_name = 'Bitcoin Regtest'
    source_symbol = 'BTC_Regtest'
    global config_path
    config_path = 'relayerClient/'+source_symbol+'/configUser.json'
    loadHub()
    if sys.argv[1]=='1':
        print("从RPC请求源链数据!")
        startRelayerClient_RPC()
    elif sys.argv[1]=='0': 
        print("从区块浏览器API请求源链数据!")
        #startRelayerClient_API()
    else:
        print("输入参数错误,默认从区块浏览器API请求源链数据!")
        #startRelayerClient_API()
