import argparse
from foundrycli import foundry_cli
import time
import json
import eth_account
from web3 import Web3
import os
import sys
sys.path.append(".")
import sourcePlugin.BTC.BTC_Plugin as BTC_Plugin
import sourcePlugin.HUB.Transport_Plugin as Transport_Plugin
from bitcoinlib.services.bitcoind import *
def loadHub() -> tuple[Transport_Plugin.TransportContract,Transport_Plugin.RelayContract]:
    """
    从配置文件中读取信息
    """
    with open('managerClient/hubchainInfo.json','r') as result_file:
        save_dict = json.load(result_file)
    target_rpc_url = save_dict['HubchainManager']['rpc']
    mode = save_dict['HubchainManager']['mode']
    multichain_contract_address = save_dict['HubchainManager']['address']
    relay_contract_address = save_dict[source_name]['relayContract']['address']
    transport_contract_address = save_dict[source_name]['transportContract']['address']
    relay_contract = Transport_Plugin.RelayContract(relay_contract_address,target_rpc_url)
    transport_contract = Transport_Plugin.TransportContract(transport_contract_address,target_rpc_url)
    transport_contract.loadMulti(multichain_contract_address)
    transport_contract.loadRelay(relay_contract_address)
    with open('relayerClient/BTC/configUser.json','r') as result_file:
        save_dict = json.load(result_file)
    private_key = save_dict['targetRPC']['relayerAccount'][mode]['private']
    transport_contract.loadWallet(private_key)
    save_dict['targetRPC']['mode'] = mode
    save_dict['targetRPC']['rpc'] = target_rpc_url
    data = json.dumps(save_dict, indent = 1)
    with open('relayerClient/BTC/configUser.json','w',newline='\n') as result_file:
        result_file.write(data)
    return transport_contract,relay_contract 
def loadSource():
    rpc_connection = BitcoindClient(base_url='http://bob:bob@localhost:18334').proxy
    return rpc_connection

def getHeightFromSource(mode,rpc_connection):
    if mode == 0:
        return BTC_Plugin.getTopBlockHeight_API()
    elif mode == 1:
        return BTC_Plugin.getTopBlockHeight_RPC(rpc_connection)
    else:
        print ("Mode is wrong. This ought to never happen!")
def getBlockHashFromSource(mode,rpc_connection,height):
    if mode == 0:
        return BTC_Plugin.getBlockHashFromHeight_API(height)
    elif mode == 1:
        return BTC_Plugin.getBlockHashFromHeight_RPC(rpc_connection,height)
    else:
        print ("Mode is wrong. This ought to never happen!")
def detectOldTasks():
    data_path = 'relayerClient/BTC/'+source_name+'.json'
    print(os.path.exists(data_path))
def startTransportClient(_type):
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
    global BTC_PARAM 
    BTC_PARAM = 6
    global transport_contract,relay_contract
    transport_contract,relay_contract = loadHub()
    rpc_connection = loadSource()
    
    print("传输搬运工客户端启动成功!")
    
    headerIndex = 89
    txIndex = 0
    txid = BTC_Plugin.getRawTxFromIndex_RPC(rpc_connection,headerIndex,txIndex)
    #print(txid)
    rawTx = BTC_Plugin.getRawTxFromHash_RPC(rpc_connection,txid,True)
    
    #print(Transaction.parse_hex(rawTx['hex']))
    #transport_contract.testHashRawTx(rawTx['hex'],txHash)
    res = transport_contract.createTransportTask(rawTx['hex'],txid)
    print(res)
    #print(HUB_Plugin.getTaskNumFromTransport(transport_contract_address,target_rpc_url))


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--type", help="0 for Mainnet and 1 for Regtest")
    args = argParser.parse_args()
    startTransportClient(int(args.type))