from foundrycli import foundry_cli
import time
import json
import eth_account
from web3 import Web3
import sys

def load(param):
    """
    从配置文件中读取信息
    param:0表示远程测试链;1表示本地测试链
    """
    with open('managerClient/configManager.json','r') as result_file:
        save_dict = json.load(result_file)
    global deployed_contract_path
    global private_key
    global target_rpc_url
    target_rpc_url = 'http://'+save_dict['targetRPC'][param]['host']+':'+str(save_dict['targetRPC'][param]['port'])
    deployed_contract_path = save_dict['managerContract']['path']+':'+save_dict['managerContract']['name']
    private_key = save_dict['targetAccount'][param]['private']
def deploy():
    res = foundry_cli(f'forge create {deployed_contract_path} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
    global multichain_contract_address
    multichain_contract_address = res['deployedTo']
def record(param):
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    save_dict['HubchainManager']['address'] = multichain_contract_address
    save_dict['HubchainManager']['rpc'] = target_rpc_url
    #save_dict['HubchainManager']['key'] = private_key
    save_dict['HubchainManager']['mode'] = param
    data = json.dumps(save_dict, indent = 1)
    with open('managerClient/hubchainInfo.json','w',newline='\n') as result_file:
        result_file.write(data)
def loadHub():
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    global private_key
    global target_rpc_url
    global multichain_contract_address
    private_key = save_dict['HubchainManager']['key']
    target_rpc_url = save_dict['HubchainManager']['rpc']
    multichain_contract_address = save_dict['HubchainManager']['address']
def addManager():
    manager = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
    res = foundry_cli(f'cast send {multichain_contract_address} "addManager(address)" {manager} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
if __name__ == "__main__":
    if sys.argv[1]=='1':
        print("Hubchain 中继链为本地测试链!")
        load(1)
        deploy()
        record(1)
    elif sys.argv[1]=='0': 
        print("Hubchain 中继链为计算区提供的测试链!")
        load(0)
        deploy()
        record(0)
    else:
        print("输入参数错误")
    
    
    #loadHub()
    #addManager()



