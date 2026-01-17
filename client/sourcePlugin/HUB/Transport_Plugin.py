from foundrycli import foundry_cli
from typing import Union
import eth_account
import time
import json
import sys
import os
sys.path.append(".")
from .Relay_Plugin import RelayContract,BasicRelayClient
from ..BTC.BTC_Plugin import BitcoinPlugin

class TransportTask:
    def __init__(self,index:int,hash:str) -> None:
        self.index = index
        self.hash = hash
    def setTask(self,user:str,relayer:str,rawTx:str,state:int,timestamp:int) -> None:
        self.user = user
        self.relayer = relayer
        self.rawTx = rawTx
        self.state = state
        self.timestamp = timestamp
    def printTask(self) -> None:
        print("Index:",self.index)
        print("Hash:",self.hash)
        print("User:",self.user)
        print("Relayer:",self.relayer)
        print("RawTx:",self.rawTx)
        print("State:",self.state)
        print("Timestamp:",self.timestamp)
    def checkIfEnd(self) -> bool:
        """
        Check if the Transport Task Never be Modified
        """
        if self.state in [3,4,5]:
            return True
        else:
            return False
    def checkIfMine(self,my_address:str) -> bool:
        """
        Check if my_address Matches the Relayer of Transport Task
        """
        if(self.relayer == my_address):
            return True
        else:
            return False
    def checkIfCanBeAccepted(self,time_out:int) -> int:
        """
        Check if the Task can be Accepted or Re-Accepted by any Relayer.
        
        Return 0 if the New Task can be Accepted. 
        Return 1 if the Old Task can be Re-Accepted.
        Return 2 for Other Conditions.
        """
        if self.state == 1:
            return 0
        elif self.state == 2:
            if int(time.time()) - self.timestamp > time_out:
                return 1
            else:
                return 2
        else:
            return 2 
class TransportContract:
    def __init__(self,address:str,rpc:str) -> None:
        self.address = address
        self.rpc = rpc
    def loadWallet(self,private_key:str) -> None:
        self.account = eth_account.Account.from_key(private_key=private_key)
    def loadRelay(self,address:str) -> None:
        self.relay = address
    def loadMulti(self,address:str) -> None:
        self.multi = address
    def getMultiAddress(self) -> str:
        """
        Query Address of MultiChain Manager Contract
        """
        res = foundry_cli(f'cast call {self.address} "getMultiChain()(address)" --rpc-url {self.rpc}')
        return(res)
    def getRelayAddress(self) -> str:
        """
        Query Address of Relay Contract
        """
        return foundry_cli(f'cast call {self.address} "getRelayContract()(address)" --rpc-url {self.rpc}')
    def checkMulti(self) -> bool:
        return self.multi == self.getMultiAddress()
    def checkRelay(self) -> bool:
        return self.relay == self.getRelayAddress()
    def getTaskNum(self) -> int:
        """
        Query Number of History Tasks
        """
        res = foundry_cli(f'cast call {self.address} "getTaskNum()(uint)" --rpc-url {self.rpc}')
        return(int(res))
    def getTaskHashByIndex(self,index:int) -> str:
        taskHash = foundry_cli(f'cast call {self.address} "getTaskHashByNum(uint)(bytes32)" {index} --rpc-url {self.rpc}')
        return taskHash.split('0x')[-1]
    def getTaskKeyByIndex(self,index:int) -> TransportTask:
        taskHash = self.getTaskHashByIndex(index)
        task = TransportTask(index,taskHash)
        return task
    def updateTaskInfo(self,task:TransportTask) -> TransportTask:
        res = foundry_cli(f'cast call {self.address} "getTaskByHash(bytes32)(address,address,bytes,uint,uint256)" {task.hash} --rpc-url {self.rpc}').split('\n')
        task.setTask(
            user = res[0],
            relayer = res[1],
            rawTx = res[2].split('0x')[-1],
            state = int(res[3]),
            timestamp = int(res[4])
        )
        return task
    def getTaskByIndex(self,index:int) -> TransportTask:
        task = self.getTaskKeyByIndex(index)
        return self.updateTaskInfo(task)
    def acceptTask(self,task:TransportTask) -> tuple[int,TransportTask]:
        """
        Relayer Tries to Accept a New Task on Transport Contract.

        Returns: 
            res: the result(0 accepted by me; 1 accepted by others; 2 withdrawed by user; 3 other conditions
            task: the new info of task
        """
        
        res = foundry_cli(f'cast send {self.address} "acceptTask(bytes32)" {task.hash} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --gas-limit 999999 -j' )
        print("Send hubchain tx %s to accept task!" % res['transactionHash'])
        task = self.updateTaskInfo(task)
        if task.state == 2:
            if task.checkIfMine(self.account.address):
                return (0,task)
            else:
                return (1,task)
        elif task.state == 3:
            return (2,task) 
        else:
            return (3,task)
    def reAcceptTask(self,task:TransportTask) -> tuple[int,TransportTask]:
        """
        Relayer Tries to Re-Accept an Old Task on Transport Contract.

        Returns: 
            res: the result(0 re-accepted by me; 1 re-accepted by others; 2 withdrawed or successed; 3 other conditions
            task: the new info of task
        """
        res = foundry_cli(f'cast send {self.address} "reAcceptTask(bytes32)" {task.hash} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --gas-limit 999999' )
        print("Send hubchain tx %s to re-accept task!" % res['transactionHash'])
        oldTimestamp = task.timestamp
        task = self.updateTaskInfo(task)
        if task.state == 2 and task.timestamp > oldTimestamp:
            if task.checkIfMine(self.account.address):
                return (0,task)
            else:
                return (1,task)
        elif task.state in [4,5]:
            return (2,task) 
        else:
            return (3,task)
    def accept_or_ReAccept_Task(self,task:TransportTask,type:bool) -> tuple[int, Union[TransportTask,str]]:
        """
        Relayer Tries to Accept or Re-Accept a Task on Transport Contract.

        Args:
            task: the target transport task
            type (bool): True for accept task; False for re-accept
        Returns: 
            res: the result(0 accepted by me; 1 accepted by others; 2 withdrawed or successed; 3 other conditions; 4 error
            info: the new info of task if res in [0,1,2,3]; error info if res = 4
        """
        try:
            if type:
                return self.reAcceptTask(task)
            else:
                return self.acceptTask(task)
        except Exception as e:
            print("Accept or Re-Accept Task Onchain ERROR: %s !" % e)
            return (4,e)
    def finishTask(self,task:TransportTask,leafProof:str,rootKey:str) -> tuple[int, Union[TransportTask,Exception]]:
        """
        Relayer Tries to Finish a Task on Transport Contract.

        Args:
            task: the target transport task
            leafProof (str): Merkle Path of Tx
            rootKey (str): Hash of Block which Records the Tx
        Returns: 
            res: the result(0 successed; 1 withdrawed ; 2 re-accepted by others; 3 wrong tx proof; 4 error
            info: the new info of task if res in [0,1,2,3]; error info if res = 4
        """
        print("Try to finish task with index %d !" % task.index)
        try:
            res = foundry_cli(f'cast send {self.address} "finishTask(bytes32,bytes,bytes)(bool)" {task.hash} {leafProof} {rootKey} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --gas-limit 999999 -j')
            print("Send hubchain tx %s to finish task!" % res['transactionHash'])
            oldTimestamp = task.timestamp
            task = self.updateTaskInfo(task)
            if task.state == 4:
                return (0,task)
            elif task.state == 5:
                return (1,task)
            elif task.state == 2:
                if task.timestamp > oldTimestamp:
                    return (2,task)  
                else:
                    return (3,task) 
            else:
                return (4,task) 
        except Exception as e:
            print("Finish Task Onchain ERROR: %s !" % e)
            return (4,e)
    def testHashRawTx(self,rawTx:str,txid:str):
        res = foundry_cli(f'cast call {self.address} "hashRawTx(bytes)(bytes32)" {rawTx} --rpc-url {self.rpc}' )
        print("Target txid: %s !" % txid)
        print("Actual txid: %s !" % res)
    def createTransportTask(self,rawTx:str,hashTx:str) -> tuple[bool,str]:
        """
        User Tries to Create a new Transport Task
        
        Args:
            rawTx: a new and valid Source Tx can be recorded by Source Chain
        
        Returns: 
            res: the result(True or False)
        """
        try:
            task = TransportTask(-1,hashTx)
            task = self.updateTaskInfo(task)
            #task.printTask()
            if task.state != 0:
                return (False,"Create Task Offchain ERROR: Task Existed!")
            res = foundry_cli(f'cast send {self.address} "createTask(bytes)" {rawTx} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --gas-limit 999999 -j' )
            print("Send hubchain tx %s to create new task!" % res['transactionHash'])
            task = self.updateTaskInfo(task)
            #task.printTask()
            if task.user == self.account.address:
                return (True, "Success to create task with taskID %s!" % task.hash)
            else:
                #print(res)
                return (False,"Create Task Offchain ERROR: Fail to Create Task!")
        except Exception as e:
            print("Create Task Onchain ERROR: ", e)
            return (False,e)
class TransportBasicClient:
    def __init__(self,publicDataPath:str,privateDataPath:str,mainnet_or_regtest:int,api_or_rpc:int) -> None:
        nameList = ['Bitcoin Mainnet','Bitcoin Regtest']
        self.source_name = nameList[mainnet_or_regtest]
        self.loadHub(publicDataPath,privateDataPath)
        self.loadBitcoin(mainnet_or_regtest,api_or_rpc,privateDataPath)
        self.TIME_OUT = 60*60*2
        self.PARAM = 6
    def loadHub(self,publicDataPath:str,privateDataPath:str) -> None:
        """
        从配置文件中读取信息
        """
        with open(publicDataPath,'r') as result_file:
            save_dict = json.load(result_file)
        target_rpc_url = save_dict['HubchainManager']['rpc']
        mode = save_dict['HubchainManager']['mode']
        multichain_contract_address = save_dict['HubchainManager']['address']
        relay_contract_address = save_dict[self.source_name]['relayContract']['address']
        transport_contract_address = save_dict[self.source_name]['transportContract']['address']
        with open(privateDataPath,'r') as result_file:
            save_dict = json.load(result_file)
        private_key = save_dict['targetRPC']['relayerAccount'][mode]['private']
        save_dict['targetRPC']['mode'] = mode
        save_dict['targetRPC']['rpc'] = target_rpc_url
        data = json.dumps(save_dict, indent = 1)
        with open(privateDataPath,'w',newline='\n') as result_file:
            result_file.write(data)
        relay_contract = RelayContract(relay_contract_address,target_rpc_url)
        transport_contract = TransportContract(transport_contract_address,target_rpc_url)
        transport_contract.loadMulti(multichain_contract_address)
        transport_contract.loadRelay(relay_contract_address)
        transport_contract.loadWallet(private_key)
        self.transport_contract = transport_contract
        self.relay_contract = relay_contract
    def loadBitcoin(self,mainnet_or_regtest:int,api_or_rpc:int,privateDataPath:str) -> None:
        bitcoin_plugin = BitcoinPlugin(mainnet_or_regtest)
        if api_or_rpc == 0:
            self.source_plugin = bitcoin_plugin
        else:
            with open(privateDataPath,'r') as result_file:
                save_dict = json.load(result_file)
            source_rpc = save_dict['bitcoinRPC'][self.source_name]
            source_rpc_user = source_rpc['user']
            source_rpc_password = source_rpc['password']
            source_rpc_host = source_rpc['host']
            source_rpc_port = source_rpc['port']
            bitcoin_plugin.setRPCConnection(source_rpc_user,source_rpc_password,source_rpc_host,source_rpc_port)
            self.source_plugin = bitcoin_plugin
        self.task_data_path = 'relayerClient/'+self.source_plugin.symbol+'/data/'+self.source_plugin.chainType+'.json'
    
    def checkRelay(self) -> bool:
        heightInSource = self.source_plugin.getTopBlockHeight()
        print("Height of Source Ledger: %d !" % heightInSource)
        heightInShadow = self.relay_contract.getTopShadowHeight()
        print("Height of Shadow Ledger: %d !" % heightInShadow)
        if abs(heightInSource - heightInShadow) > self.PARAM:
            return False
        else:
            return True
    def getWaitTime(start:int,time_out:int) -> int:
        """
            计算从当前时刻到超时时刻需要等待的时间
        参数：
            start 起始时间
            time_out 等待时间上限
        返回值:
            wait等待时间(>=0)
        """
        now = int(time.time())
        wait = int(start) + int(time_out) - now
        if wait < 0:
            return 0
        else:
            return wait 

    def checkTaskIfValid(self,task:TransportTask) -> bool:
        (res1,msg) = self.source_plugin.getRawTxByTxId(task.hash,False)
        if res1:
            return True
        else:
            res2 = self.source_plugin.sendRawTx(task.hash,task.rawTx)
            return res2
    def waitSourceTxRecorded(self,txid:str) -> tuple[bool, str, int]:
        return self.source_plugin.waitTxRecorded(txid)
    def waitNewSourceBlock(self,blockNum: int) -> bool:
        return self.source_plugin.waitNewBlock(blockNum);
    def processSingleTask(self,task:TransportTask) -> tuple[bool,TransportTask]:
        if task.checkIfEnd():
            return (True,task)
        else:
            (res,task) = self.processSingleActiveTask(task)
            if res == 0:
                return (True,task)
            return (False,task)
    def processSingleActiveTask(self,task:TransportTask) -> tuple[int,Union[TransportTask,Exception]]:
        """
        处理进行中的单一跨链任务(完整生命周期),当任务处于终止状态或等待用户操作状态退出
        
        参数: 
            task任务信息
        
        返回值: 
            res任务执行结果(0完全终止,1等待用户操作,2异常或主动中断)
            taskInfo(任务的最新信息或报错信息)
        """
        if task.checkIfMine(self.transport_contract.account.address):#自己的未完成的任务
            print("Continue to process my task with index %d !" % task.index)
            return self.finishMyTask(task)
        res1 = task.checkIfCanBeAccepted(self.TIME_OUT)
        if res1 in [0,1]: #待抢单的任务
            if(self.checkTaskIfValid(task)):
                print("Try to accept or re-accept new task with index %d !" % task.index)
                (res2,task) = self.transport_contract.accept_or_ReAccept_Task(task,bool(res1))
                if res2 == 0:
                    print("Success to accept task index %d !" % task.index)
                    return self.finishMyTask(task)
                elif res2 == 1:
                    print("Fail to accept task index %d, it is accepted by %s !" % (task.index,task.relayer))
                    wait = self.getWaitTime(task.timestamp,self.TIME_OUT)
                    time.sleep(wait)
                    task = self.transport_contract.updateTaskInfo(task)
                    if task.checkIfEnd():
                        return (0,task)
                    else:
                        return self.processSingleActiveTask(task)
                elif res2 == 2:
                    print("Fail to accept task index %d, it ended with state %d !" % (task.index,task.state))
                    return (0,task)
                else:
                    return (2,task)
            else: #等待用户撤销的无效任务
                print(" Task with index %d is invalid and wait for user's operation!" % task.index)
                return (1,task)
        else: #其它搬运工进行中的任务
            wait = self.getWaitTime(task.timestamp,self.TIME_OUT)
            time.sleep(wait)
            task = self.transport_contract.updateTaskInfo(task)
            if task.checkIfEnd():
                return (0,task)
            else:
                return self.processSingleActiveTask(task)
    def finishMyTask(self,task:TransportTask) -> tuple[bool,Union[TransportTask,str]]:
        """
        处理进行中的单一跨链任务(完整生命周期),当任务处于终止状态或等待用户操作状态退出
        
        参数: 
            task任务信息
        
        返回值: 
            type终止任务的类型(True完成,False异常)
            taskInfo(任务的最新信息)
        """
        #等待交易上链
        (res,hashHeader,confirm) = self.source_plugin.waitTxRecorded(task.hash)
        if not res:
            return (False,task)
        #生成交易证明
        (txHash,merkleProof,hashHeader) = self.source_plugin.generateTxProof(hashHeader,task.hash)
        #等待区块头被中继合约确认
        if confirm <= self.PARAM:
            print("Wait %d new source block(s) !" % (self.PARAM - confirm))
            self.waitNewSourceBlock(self.PARAM - confirm)
        #提交交易证明
        return self.transport_contract.finishTask(task,merkleProof,hashHeader)
    def loadHistoryFromFile(self) -> dict:
        path = self.task_data_path
        if os.path.exists(path):
            with open(path,'r') as result_file:
                history = json.load(result_file)
            if history["transportAddress"] != self.transport_contract.address:
                history = {
                    "transportAddress":"",
                    "endTasks":[]
                }
                history["transportAddress"] = self.transport_contract.address
                data = json.dumps(history, indent = 1)
                with open(path,'w',newline='\n') as result_file:
                    result_file.write(data)
            return history
        else:
            history = {
                "transportAddress":"",
                "endTasks":[]
            }
            history["transportAddress"] = self.transport_contract.address
            data = json.dumps(history, indent = 1)
            with open(path,'w',newline='\n') as result_file:
                result_file.write(data)
            return history
    def recordNewEndTask(self,task:TransportTask) -> None:
        path = self.task_data_path
        with open(path,'r') as result_file:
            save_dict = json.load(result_file)
        if task.index not in save_dict['endTasks']:
            save_dict['endTasks'].append(task.index)
            data = json.dumps(save_dict, indent = 1)
            with open(path,'w',newline='\n') as result_file:
                result_file.write(data)
            print("Success to record new end task with index %d !" % task.index)

