import argparse
from foundrycli import foundry_cli
import time
import json
import eth_account
from web3 import Web3
import sys
sys.path.append(".")
from sourcePlugin.BTC.BTC_Plugin import BitcoinPlugin
from sourcePlugin.HUB.Relay_Plugin import BasicRelayClient


def startBTCRelayer(_type,_rpc):
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
    BTC_RelayClient = BasicRelayClient(publicData,privateData,0,_type,_rpc,manager_or_relayer=1)
    BTC_RelayClient.startRelayClient()
if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--type", help="0 for Mainnet and 1 for Regtest")
    argParser.add_argument("-r", "--rpc", help="0 for API and 1 for RPC")
    args = argParser.parse_args()
    #print("args=%s" % args)
    #print("args.type=%d" % int(args.type))
    #print("args.rpc=%s" % args.rpc)
    startBTCRelayer(int(args.type),int(args.rpc))