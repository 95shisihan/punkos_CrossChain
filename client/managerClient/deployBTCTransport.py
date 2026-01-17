from foundrycli import foundry_cli
import time
import json
import requests
import argparse

def loadHub():
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    mode = save_dict['HubchainManager']['mode']
    global target_rpc_url
    target_rpc_url = save_dict['HubchainManager']['rpc']
    global multichain_contract_address
    multichain_contract_address = save_dict['HubchainManager']['address']
    global relay_contract_address
    relay_contract_address = save_dict[source_name]['relayContract']['address']
    global transport_contract_path
    transport_contract_path = save_dict[source_name]['transportContract']['path']+":"+ save_dict[source_name]['transportContract']['name']
    with open('managerClient/configManager.json','r') as result_file:
        save_dict = json.load(result_file)
    global private_key
    private_key = save_dict['targetAccount'][mode]['private']
def deploy():
    res = foundry_cli(f'forge create {transport_contract_path} --rpc-url {target_rpc_url} --private-key {private_key} --legacy')
    print(res)
    global transport_contract_address
    transport_contract_address = res['deployedTo']
    print("传输合约部署成功!") 
def register():
    #print(source_chain_id)
    res = foundry_cli(f'cast send {transport_contract_address} "register(address,address)" {multichain_contract_address} {relay_contract_address} --rpc-url {target_rpc_url} --private-key {private_key} --gas-limit 9999999')
    #print(res)
    print("传输合约启动成功!")
    #res = foundry_cli(f'cast call {transport_contract_address} "getRelayContract()(address)" --rpc-url {target_rpc_url}')
    #print(res)
def record():
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    save_dict[source_name]['transportContract']['address'] = transport_contract_address
    data = json.dumps(save_dict, indent = 1)
    with open('managerClient/hubchainInfo.json','w',newline='\n') as result_file:
        result_file.write(data)
    print("传输合约信息记录成功!")
def deployBTCTransport(_type):
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
    loadHub() 
    deploy()
    record()
    register()
if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--type", help="0 for Mainnet and 1 for Regtest")
    args = argParser.parse_args()
    deployBTCTransport(int(args.type))
