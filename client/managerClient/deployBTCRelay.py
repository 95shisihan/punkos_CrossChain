import argparse
from foundrycli import foundry_cli
import json
import sys
sys.path.append(".")
import sourcePlugin.BTC.BTC_Plugin as BTC_Plugin
from sourcePlugin.HUB.Relay_Plugin import BasicRelayClient
def loadHub():
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    mode = save_dict['HubchainManager']['mode']
    global target_rpc_url
    target_rpc_url = save_dict['HubchainManager']['rpc']
    global multichain_contract_address
    multichain_contract_address = save_dict['HubchainManager']['address']
    global relay_contract_path
    relay_contract = save_dict[source_name]['relayContract']
    relay_contract_path = relay_contract['path']+":"+ relay_contract['name']
    with open('managerClient/configManager.json','r') as result_file:
        save_dict = json.load(result_file)
    global private_key
    private_key = save_dict['targetAccount'][mode]['private']
def loadSource():
    """
    从配置文件中读取信息
    """
    with open('managerClient/configManager.json','r') as result_file:
        save_dict = json.load(result_file)
    source_rpc = save_dict['sourceRPC'][source_name]
    source_rpc_user = source_rpc['user']
    source_rpc_password = source_rpc['password']
    source_rpc_host = source_rpc['host']
    source_rpc_port = source_rpc['port']
    rpc_connection = BTC_Plugin.setRPCConnection(source_rpc_user,source_rpc_password,source_rpc_host,source_rpc_port)
    return rpc_connection
def deploy():
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --constructor-args {chain_type}')
    global relay_contract_address
    relay_contract_address = res['deployedTo']
    print("中继合约部署成功!")   
def record():
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    save_dict[source_name]['relayContract']['address'] = relay_contract_address
    data = json.dumps(save_dict, indent = 1)
    with open('managerClient/hubchainInfo.json','w',newline='\n') as result_file:
        result_file.write(data)
    print("中继合约信息记录成功!") 
def getGenesis_RPC(rpc_connection):
    height = BTC_Plugin.getGenesisHeight_RPC(rpc_connection)
    (hashHeader,hexHeader) = BTC_Plugin.getBlockHeaderFromHeight_RPC(rpc_connection,height)  
    return (height,hashHeader,hexHeader)
def getGenesis_API():
    height = BTC_Plugin.getGenesisHeight_API()
    (hashHeader,hexHeader) = BTC_Plugin.getBlockHeaderFromHeight_API(height)  
    return (height,hashHeader,hexHeader)
def submitGenesis(heightGenesis,hashGenesis,hexGenesis): 
    genesisParams = foundry_cli(f'cast --to-uint256 {heightGenesis}')
    res = foundry_cli(f'cast send {relay_contract_address} "updateByUnion(address,bytes,bytes)" {multichain_contract_address} {hexGenesis} {genesisParams} --rpc-url {target_rpc_url} --private-key {private_key}')
    #print(res)
    print("中继合约启动成功!")  
    chainID = foundry_cli(f'cast call {relay_contract_address} "getChainID()(uint)" --rpc-url {target_rpc_url}')
    print("源链在中继链注册标号为",chainID,"!")
    res = foundry_cli(f'cast call {relay_contract_address} "getMainnet()(uint)" --rpc-url {target_rpc_url}')
    print("源链在中继链注册的链类型",res,"!")
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    save_dict[source_name]['chainID'] = chainID
    save_dict[source_name]['relayContract']['genesis']['hash'] = hashGenesis
    save_dict[source_name]['relayContract']['genesis']['height'] = heightGenesis
    data = json.dumps(save_dict, indent = 1)
    with open('managerClient/hubchainInfo.json','w',newline='\n') as result_file:
        result_file.write(data) 
def deployBTCRelayTest(_type,_rpc):
    global source_name
    if _type == 0:
        source_name = 'Bitcoin Mainnet'
        print("源链为比特币主链!")
    elif _type == 1:
        source_name = 'Bitcoin Regtest'
        print("源链为比特币回归测试链!")
    else:
        print("输入参数错误")
        return False
    global chain_type
    chain_type = _type
    loadHub()
    if _rpc == 0:
        if _type == 1:
            print("比特币回归测试链不支持区块浏览器API!")
            return False
        print("从区块浏览器API请求源链数据!")
        heightGenesis,hashGenesis,hexGenesis = getGenesis_API() 
    elif _rpc == 1: 
        print("从RPC请求源链数据!")
        rpc_connection = loadSource()
        heightGenesis,hashGenesis,hexGenesis = getGenesis_RPC(rpc_connection)
    else:
        print("输入参数错误")
        return False 
    deploy()
    record()
    submitGenesis(heightGenesis,hashGenesis,hexGenesis)
def deployBTCRelay(_type,_rpc):
    if _type == 0:
        print("源链为比特币主链!")
    elif _type == 1:
        print("源链为比特币回归测试链!")
    else:
        print("输入参数错误")
        return False
    if _rpc == 0:
        if _type == 1:
            print("比特币回归测试链不支持区块浏览器API!")
            return False
        print("从区块浏览器API请求源链数据!") 
    elif _rpc == 1: 
        print("从RPC请求源链数据!")
    else:
        print("输入参数错误")
        return False 
    publicData = 'managerClient/hubchainInfo.json'
    privateData = 'relayerClient/BTC/configUser.json'
    BTC_RelayClient = BasicRelayClient(publicData,privateData,0,_type,_rpc,manager_or_relayer=0)
    res = BTC_RelayClient.startManagerClient()
    print(res)   
if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--type", help="0 for Mainnet and 1 for Regtest")
    argParser.add_argument("-r", "--rpc", help="0 for API and 1 for RPC")
    args = argParser.parse_args()
    #print("args=%s" % args)
    #print("args.type=%d" % int(args.type))
    #print("args.rpc=%s" % args.rpc)
    deployBTCRelay(int(args.type),int(args.rpc))
