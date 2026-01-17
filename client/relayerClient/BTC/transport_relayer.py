import argparse
from foundrycli import foundry_cli
import time
import json
import os
import sys
from cryptos import *
import threading
sys.path.append(".")
from sourcePlugin.BTC.BTC_Plugin import BitcoinPlugin
import sourcePlugin.HUB.Transport_Plugin as Transport_Plugin
class BitcoinTransportClient(Transport_Plugin.TransportBasicClient):
    def __init__(self,publicDataPath:str,privateDataPath:str,mainnet_or_regtest:int,api_or_rpc:int) -> None:
        Transport_Plugin.TransportBasicClient.__init__(self,publicDataPath,privateDataPath,mainnet_or_regtest,api_or_rpc)
class myThread(threading.Thread):
    def __init__(self, threadID:int, taskIndex:int,transport_client:BitcoinTransportClient):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.taskIndex = taskIndex
        self.transport_client = transport_client
    def run(self):
        print("Start thread %d to process task %d !" % (self.threadID,self.taskIndex))
        task = self.transport_client.transport_contract.getTaskByIndex(self.taskIndex)
         #task.printTask()
        (res,task) = self.transport_client.processSingleTask(task)
        if res:
            threadLock.acquire()
            self.transport_client.recordNewEndTask(task)
            threadLock.release()
        print("Close thread %d!" % self.threadID)
def startTransportClient(_type):
    if _type == 0:
        print("源链为比特币主链!")
    elif _type == 1:
        print("源链为比特币回归测试链!")
    else:
        print("输入参数错误")
        return False
    publicData = 'managerClient/hubchainInfo.json'
    privateData = 'relayerClient/BTC/configUser.json'
    transport_client = BitcoinTransportClient(publicData,privateData,_type,1)
    if not transport_client.transport_contract.checkMulti() or not transport_client.transport_contract.checkRelay():
        print("Check Transport Offchain ERROR: Transport Contract Has Not Registred!")
        return False
    if not transport_client.checkRelay():
        print("Check Relay Offchain ERROR: Shadow Ledger of Relay Contract Does Not Match Source Ledger!")
        return False
    print("传输搬运工客户端启动成功!")
    global threadLock
    threadLock = threading.Lock()
    threadIndex = 0
    #处理历史跨链任务
    history = transport_client.loadHistoryFromFile()
    print("处理历史跨链任务!")
    
    taskNum = transport_client.transport_contract.getTaskNum()
    for index in range(taskNum):
        if index in history['endTasks']:
            print("Task %d has been checked, pass!" % index)
        else:
            print("Start to process task %d!" % index)
            newThread = myThread(threadIndex,index)
            threadIndex += 1
            newThread.start()
    oldNum = taskNum
    while True:
        taskNum = transport_client.transport_contract.getTaskNum()
        if(taskNum > oldNum):
            newTasks = taskNum - oldNum
            print("Find %d new task(s) !" % newTasks)
            for index in range(newTasks):
                print("Start to process task %d!" % index)
                newThread = myThread(threadIndex,index + oldNum)
                threadIndex += 1
                newThread.start()
            oldNum = taskNum
        else:
            print("No New Task!")
            time.sleep(60)
if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--type", help="0 for Mainnet and 1 for Regtest")
    args = argParser.parse_args()
    startTransportClient(int(args.type))