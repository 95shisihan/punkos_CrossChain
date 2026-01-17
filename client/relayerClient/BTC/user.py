from foundrycli import foundry_cli
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import json
import requests
import hashlib
import json
import binascii
from cryptos import *
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
    global transport_contract_address
    transport_contract_address = save_dict['Bitcoin Regtest']['transportAddress']
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
def generateTxProofFromListToStr(siblings):
    str=''
    if len(siblings) == 0:
        return (str)
    else:
        depth = len(siblings)    
    for i in range(depth):
        str = str + siblings[i]    
    return (str)
def generateTxProof_API(heightHeader,indexTx):
    hashHeader = BTC_Plugin.getBlockHashFromHeight_API(heightHeader)
    (txRoot,txList) = BTC_Plugin.getTxListFromHash_API(hashHeader)
    tree = mk_merkle_proof(txRoot,txList,indexTx) 
    txHash = tree['tx_hash']
    leafNode = foundry_cli(f'cast --to-uint256 {Web3.to_hex(indexTx)}')
    merkleProof = leafNode + generateTxProofFromListToStr(tree['siblings'])
    return (txHash,merkleProof,hashHeader)
def generateTxProof_RPC(heightHeader,indexTx):
    rpc_connection = loadSource()
    hashHeader = BTC_Plugin.getBlockHashFromHeight_RPC(rpc_connection,heightHeader)
    (txRoot,txList) = BTC_Plugin.getTxListFromHash_RPC(rpc_connection,hashHeader)
    tree = mk_merkle_proof(txRoot,txList,indexTx) 
    txHash = tree['tx_hash']
    leafNode = foundry_cli(f'cast --to-uint256 {Web3.to_hex(indexTx)}')
    merkleProof = leafNode + generateTxProofFromListToStr(tree['siblings'])
    return (txHash,merkleProof,hashHeader)
def verifyTxOnchain(txHash,merkleProof,hashHeader):
    #res = foundry_cli(f'cast send {relay_contract_address} "verifyTxByUser(bytes,bytes,bytes)(bool)"  {leafNode} {merkleProof} {hashHeader} --rpc-url {target_rpc_url} --private-key {private_key}')
    res = foundry_cli(f'cast call {relay_contract_address} "verifyTxByUser(bytes,bytes,bytes)(bool)" {txHash} {merkleProof} {hashHeader} --rpc-url {target_rpc_url} --private-key {private_key}')
    print("交易验证结果1:",res)
def submitTx(txHash,merkleProof,hashHeader):
    res = foundry_cli(f'cast send {transport_contract_address} "verifyTx(address,bytes,bytes,bytes)(bool)" {relay_contract_address} {txHash} {merkleProof} {hashHeader} --rpc-url {target_rpc_url} --private-key {private_key}')
    print("交易验证结果2:",res)
if __name__ == "__main__":
    global source_name
    source_name = 'Bitcoin Regtest'
    source_symbol = 'BTC_Regtest'
    global config_path
    config_path = 'relayerClient/'+source_symbol+'/configUser.json'
    loadHub()
    heightHeader = 25 #844705
    indexTx = 0
    if sys.argv[1]=='1':
        print("从RPC请求源链数据!")
        (txHash,merkleProof,hashHeader) = generateTxProof_RPC(heightHeader,indexTx)
        verifyTxOnchain(txHash,merkleProof,hashHeader)
    elif sys.argv[1]=='0': 
        print("从区块浏览器API请求源链数据!")
        (txHash,merkleProof,hashHeader) = generateTxProof_API(heightHeader,indexTx)
        #(t1,merkleProof2,t3) = generateTxProof_API(heightHeader,wrongIndex)
        #print ("!!!!!",leafNode,merkleProof,hashHeader)
        verifyTxOnchain(txHash,merkleProof,hashHeader)
        submitTx(txHash,merkleProof,hashHeader)
    else:
        print("输入参数错误,默认从区块浏览器API请求源链数据!")