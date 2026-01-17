from foundrycli import foundry_cli
from typing import Union
import eth_account
import time
import json
import sys
import os
from web3 import Web3
sys.path.append(".")
from ..BTC.BTC_Plugin import BitcoinPlugin
from .General_Plugin import GeneralSourcePlugin
class RelayContract(GeneralSourcePlugin):
    def __init__(self,multi:str,address:str,rpc:str,path:str) -> None:
        self.multi = multi
        self.address = address
        self.rpc = rpc
        self.path = path
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        with open('out/BTC/BTC_RelayContract.sol/BTC_Relaycontract.json','r') as result_file:
            abi = json.load(result_file)["abi"]
        self.contract = self.w3.eth.contract(address = self.address,abi=abi) 
    def loadWallet(self,private_key:str) -> None:
        self.account = eth_account.Account.from_key(private_key=private_key)
    def deployContract(self,chain_type:int) -> bool:
        try:
            res = foundry_cli(f'forge create {self.path} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --constructor-args {chain_type}')
            self.address = res['deployedTo'] 
            return True
        except Exception as e:
            print("ERROR When Deploy Contract: %s !" % e)
            return False  
    def getMultiAddress(self) -> str:
        """
        Query Address of MultiChain Manager Contract
        """
        #res = foundry_cli(f'cast call {self.address} "getMultiChainContractAddress()(address)" --rpc-url {self.rpc}')
        res = self.contract.functions.getMultiChainContractAddress().call()
        return(res)
    def checkMulti(self) -> bool:
        return self.multi == self.getMultiAddress()
    def getTopShadowHeight(self) -> int:
        """
        向中继合约查询影子链高度
        
        返回值：
        影子链高度
        """
        #res = foundry_cli(f'cast call {self.address} "getTopHeight()(uint)" --rpc-url {self.rpc}')
        res = self.contract.functions.getTopHeight().call()
        return(res)
    def getBlockHashInShadowMainChainFromHeight(self,height) -> str:
        """
        向中继合约查询高度对应的主链哈希
        
        返回值：
        影子链高度
        """
        res = foundry_cli(f'cast call {self.address} "getMainChainHeaderHash(uint)(bytes32)" {height} --rpc-url {self.rpc}')
        return(res)
    
    def submitGenesis(self,hexGenesis:str,genesisParams:str) -> tuple[bool,str]: 
        try:
            res = foundry_cli(f'cast send {self.address} "updateByUnion(address,bytes,bytes)" {self.multi} {hexGenesis} {genesisParams} --rpc-url {self.rpc} --private-key {self.account.key.hex()}')
            return (True,res)
        except Exception as e:
            return (False,e)
    def submitSourceData(self,hexHeaderToRelay:str,curHash:str,value:str) -> tuple[bool,str]:
        try:
            res = foundry_cli(f'cast send {self.address} "submitCommitedHeaderByRelayer(bytes,bytes32,bytes32)" {hexHeaderToRelay} {curHash} {value} --rpc-url {self.rpc} --private-key {self.account.key.hex()} --gas-limit 999999' )
            return (True,res)        
        except Exception as e:
            return (False,e)
class BasicRelayClient:
    nameList = ['Bitcoin','Ethereum']
    symbolList = ['BTC','ETH']
    typeList = ['Mainnet','Regtest']
    def __init__(self,publicDataPath:str,privateDataPath:str,btc_or_eth:int,mainnet_or_regtest:int,api_or_rpc:int,manager_or_relayer:int) -> None:
        self.btc_or_eth = btc_or_eth
        self.mainnet_or_regtest = mainnet_or_regtest
        self.publicDataPath = publicDataPath
        self.source_name = BasicRelayClient.nameList[btc_or_eth] + ' ' + BasicRelayClient.typeList[mainnet_or_regtest]
        self.loadHub(publicDataPath,privateDataPath,manager_or_relayer)
        self.loadSource(privateDataPath,btc_or_eth,mainnet_or_regtest,api_or_rpc) 
    def loadHub(self,publicDataPath:str,privateDataPath:str,manager_or_relayer:int) -> None:
        """
        从配置文件中读取信息
        """
        with open(publicDataPath,'r') as result_file:
            save_dict = json.load(result_file)
        target_rpc_url = save_dict['HubchainManager']['rpc']
        mode = save_dict['HubchainManager']['mode']
        multichain_contract_address = save_dict['HubchainManager']['address']
        if manager_or_relayer == 0:
            relay_contract_path = save_dict[self.source_name]['relayContract']['path']+":"+ save_dict[self.source_name]['relayContract']['name']
            relay_contract_address = ''
        else:
            relay_contract_address = save_dict[self.source_name]['relayContract']['address']
            relay_contract_path = ''
        
        with open(privateDataPath,'r') as result_file:
            save_dict = json.load(result_file)
        private_key = save_dict['targetRPC']['relayerAccount'][mode]['private']
        save_dict['targetRPC']['mode'] = mode
        save_dict['targetRPC']['rpc'] = target_rpc_url
        data = json.dumps(save_dict, indent = 1)
        with open(privateDataPath,'w',newline='\n') as result_file:
            result_file.write(data)
        relay_contract = RelayContract(multichain_contract_address,relay_contract_address,target_rpc_url,relay_contract_path)
        relay_contract.loadWallet(private_key)
        self.relay_contract = relay_contract
    def updatePublicData(self) -> None:
        with open(self.publicDataPath,'r') as result_file:
            save_dict = json.load(result_file)
        save_dict[self.source_name]['relayContract']['address'] = self.relay_contract.address
        data = json.dumps(save_dict, indent = 1)
        with open(self.publicDataPath,'w',newline='\n') as result_file:
            result_file.write(data)
        print("Success to record %s 's  relay address %s !" %(self.source_name,self.relay_contract.address)) 
    def loadSource(self,privateDataPath:str,btc_or_eth:int,mainnet_or_regtest:int,api_or_rpc:int) -> None:
        if btc_or_eth == 0:
            print("Souce Chain is BTC!")
            self.source_plugin = BitcoinPlugin(mainnet_or_regtest,api_or_rpc,privateDataPath)
        elif btc_or_eth == 1:
            print("Souce Chain is ETH!")
            #self.source_plugin = BitcoinPlugin(mainnet_or_regtest,api_or_rpc,privateDataPath)
        else:
            print("Wrong!")
    def checkIfShouldRelay(self) -> int:
        while True:
            heightInSource = self.source_plugin.getTopBlockHeight()
            heightToRelay = self.relay_contract.getTopShadowHeight() + 1
            if (heightInSource > heightToRelay):
                return heightToRelay
            else:
                print("No New BTC Header To Realy!")
                time.sleep(30)
    def getSourceData(self,height:int):
        heightToRelay = height
        heightToCommit = heightToRelay + 1
        hashHeaderToRelay,hexHeaderToRelay = self.source_plugin.getBlockHeaderByHeight(heightToRelay)
        hashHeaderToCommit,hexHeaderToCommit = self.source_plugin.getBlockHeaderByHeight(heightToCommit)
        value = BasicRelayClient.commitNewHeader(hexHeaderToCommit,self.relay_contract.account)
        return (hexHeaderToRelay,hashHeaderToCommit,value)
    def startManagerClient(self) -> bool:
        res1 = self.relay_contract.deployContract(self.mainnet_or_regtest)
        if not res1:
            return False
        else:
            self.updatePublicData()
        (hexGenesis,genesisParams) = self.source_plugin.getGenesisData()
        (res2,data2) = self.relay_contract.submitGenesis(hexGenesis,genesisParams)
        return res2
    def startRelayClient(self) -> None:
        while True:
            try:
                heightToRelay = self.checkIfShouldRelay()
                print(heightToRelay)
                (hexHeaderToRelay,hashHeaderToCommit,value) = self.getSourceData(heightToRelay)
                self.relay_contract.submitSourceData(hexHeaderToRelay,hashHeaderToCommit,value)
                time.sleep(1)
            except Exception as e:
                print("错误：",e)
                time.sleep(10)
    @staticmethod
    def commitNewHeader(hexHeader:str,relayer:eth_account.Account) -> str:
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
    