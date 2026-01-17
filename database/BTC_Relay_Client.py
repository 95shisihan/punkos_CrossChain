from abc import abstractmethod
import argparse    
import sys  
import time  
from typing import List, Tuple, Optional, Dict, Any, Union  
import requests 
from foundrycli import foundry_cli
from dotenv import load_dotenv  
import os 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from crosschainzone_db import CrosschainZoneDatabaseManager as DatabaseManager
from basic_listener import ContractListener,SystemContractListener,MultiContractListener
import eth_account
from web3 import Web3

def getRelayContractAddress(symbol: str, rpc_url:str, multi_address: str) -> Optional[str]:
    tmp_listner = MultiContractListener(
        rpc_url = rpc_url,
        contract_address = None,
        multi_address = multi_address
    )
    rpc_result, block_number = tmp_listner.get_latest_block_number()
    if not rpc_result:
        return None
    rpc_result, chain_id = tmp_listner.get_source_chain_id_by_symbol(symbol=symbol,block=block_number)
    if not rpc_result:
        return None
    rpc_result, relay_address = tmp_listner.get_contract_address_by_level_id(
        chain_id=chain_id,
        level_id=0,
        block=block_number
    )
    if not rpc_result:
        return None
    return relay_address

class StakeSystemContractListener(SystemContractListener):
    def __init__(self,
        rpc_url: str,
        contract_address: str,
        multi_address: str,
        private_key: str
    ):
        SystemContractListener.__init__(
            self,
            rpc_url = rpc_url,
            contract_address = contract_address,
            multi_address= multi_address
        )
        self.private_key = private_key
    def get_gas_lower_bound(self, block: int) -> Tuple[bool,str|dict]:
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getGasLowerBound()(uint256)" '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        ) 
        try:    
            rpc_result = foundry_cli(cmd)  
            gasLowerBound = rpc_result     
            return True, gasLowerBound  

        except Exception as e:  
            extra = {  
                'operation': 'getGasLowerBound',  
                'params': {
                    'contract_address': self.contract_address,
                    'block_number': block,
                },
                'error_type': type(e).__name__,  
                'message': str(e)     
            }  
            return False, extra

    def get_require_stake(self, block: int) -> Tuple[bool, int|dict]:  
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getRequireStake()(uint256)" '  
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )  
        try:  
            rpc_result = foundry_cli(cmd)  
            requireStake = int(rpc_result)  
            return True, requireStake  

        except Exception as e:  
            extra = {  
                'operation': 'getRequireStake',  
                'params': {  
                    'contract_address': self.contract_address,  
                    'block_number': block,  
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra  

    def get_my_stake(self, block: int) -> Tuple[bool, int|dict]:  
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getMyStake()(uint256)" '
            f'--private-key {self.private_key} '    
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )  
        try:  
            rpc_result = foundry_cli(cmd)  
            myStake = int(rpc_result)  
            return True, myStake  

        except Exception as e:  
            extra = {  
                'operation': 'getMyStake',  
                'params': {  
                    'contract_address': self.contract_address,  
                    'block_number': block,  
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra  

    def get_commit_stake(self, block: int, old_key: str, new_key: str) -> Tuple[bool, int|dict]:  
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getCommitState(bytes32,bytes32)(uint256)" '    
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )  
        try:  
            rpc_result = foundry_cli(cmd)  
            commit_state = int(rpc_result)  
            return True, commit_state  

        except Exception as e:  
            extra = {  
                'operation': 'get_commit_stake',  
                'params': {  
                    'contract_address': self.contract_address,  
                    'block_number': block,  
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra  

    
    def write_become_relayer(self, value_in_wei: int):
        """  
        调用合约的becomeRelayer函数来成为relayer  
        
        Args:  
            sender_address: 发送交易的地址  
            value_in_wei: 要质押的ETH数量（以wei为单位）  
        
        Returns:  
            Tuple[bool, str|dict]: (成功状态, 交易哈希/错误信息)  
        """  
        cmd = (  
            f'cast send {self.contract_address} '  
            f'"becomeRelayer()" '  
            f'--private-key {self.private_key} '  
            f'--value {value_in_wei} '  
            f'--rpc-url {self.rpc_url} '
            f'-j'  
        )  
        
        try:  
            # 执行交易  
            tx_result = foundry_cli(cmd)  
            # cast send 成功后会返回交易哈希   
            return True, tx_result 

        except Exception as e:  
            extra = {  
                'operation': 'write_become_relayer',  
                'params': {  
                    'contract_address': self.contract_address,    
                    'value_in_wei': value_in_wei,  
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra

    def write_update_shadow_ledger(self, prev_raw:str, cur_key:str, commit:str) -> tuple[bool,str]:
        cmd = (  
            f'cast send {self.contract_address} '  
            f'"updateShadowLedgerByRelayer(bytes,bytes32,bytes32)" {prev_raw} {cur_key} {commit} '   
            f'--gas-limit {1000000} '  
            f'--rpc-url {self.rpc_url} '
            f'--private-key {self.private_key}'  
        )
        try: 
            # 执行交易  
            tx_result = foundry_cli(cmd)  
            # cast send 成功后会返回交易哈希   
            return True, tx_result        
        except Exception as e:  
            extra = {  
                'operation': 'write_update_shadow_ledger',  
                'params': {  
                    'contract_address': self.contract_address, 
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra



class BTCBlockHeaderManager:  
    def __init__(  
        self,   
        db_manager: DatabaseManager  
    ):    
        self.db_manager = db_manager
        self.source_top_height: int = 0   

    def get_BTC_top_height_API(self) -> Tuple[bool, int|dict]:   
        try:  
            url = "https://api.blockchair.com/bitcoin/stats"    
            response = requests.get(url, timeout=10)  
            response.raise_for_status()  
            result = response.json()['data']  
            block_height = int(result['best_block_height'])
            self.source_top_height = block_height    
            return True, block_height  
        except Exception as e:  
            extra = {   
            }  
            return False, extra       
    
    def update_BTC_top_height(self) -> bool:
        result, block_height = self.get_BTC_top_height_API()
        return result
    
    def get_BTC_block_header(self, height_or_hash: int|str) -> Tuple[bool,dict]:
        db_result, block_info = self.get_BTC_block_header_DB(height_or_hash)
        if db_result:
            return True, block_info
        api_result, block_info = self.get_BTC_block_header_API(height_or_hash)
        if api_result:
            print(self.save_BTC_block_header_DB(block_info))
        return api_result, block_info
    
    def get_BTC_block_header_API(self, height_or_hash: int|str) -> Tuple[bool,dict]:
        if isinstance(height_or_hash,int):
            return self.get_BTC_block_header_by_height_API(height_or_hash)
        else:
            return self.get_BTC_block_header_by_hash_API(height_or_hash)
    
    def get_BTC_block_header_by_hash_API(self, block_hash: str) -> Tuple[bool,tuple[str,int,str]|dict]:
        if block_hash[0:2] == '0x':
            tmp_block_hash = block_hash[2:]
        else:
            tmp_block_hash = block_hash
            block_hash = '0x' + block_hash
        try:
            url = f"https://api.blockchair.com/bitcoin/raw/block/{tmp_block_hash}"
            response = requests.get(  
                url,   
                timeout=10,  
                headers={  
                    'User-Agent': 'CrosschainZone/1.0',  
                    'Accept': 'application/json'  
                }  
            )
            response.raise_for_status()  
            result = response.json()['data']  
            block_height = result[tmp_block_hash]['decoded_raw_block']['height'] 
            raw_block = result[tmp_block_hash]['raw_block'][0:160]
            block_info = {  
                'hash': block_hash,   
                'height': block_height,  
                'rawData': raw_block  
            }
            return True, block_info
        except Exception as e:  
            extra = {   
            }  
            return False, extra
    
    def get_BTC_block_header_by_height_API(self, block_height: int) -> Tuple[bool,dict]:
        try:
            url = f"https://api.blockchair.com/bitcoin/raw/block/{block_height}"
            response = requests.get(  
                url,   
                timeout=10,  
                headers={  
                    'User-Agent': 'CrosschainZone/1.0',  
                    'Accept': 'application/json'  
                }  
            )
            response.raise_for_status()  
            result = response.json()['data']  
            if block_height == 0:  
                block_hash = result[0]['decoded_raw_block']['hash']  
                raw_block = result[0]['raw_block'][0:160]  
            else:  
                block_hash = result[str(block_height)]['decoded_raw_block']['hash']  
                raw_block = result[str(block_height)]['raw_block'][0:160]
            if block_hash[0:2] != '0x':
                block_hash = '0x' + block_hash
            block_info = {  
                'hash': block_hash,   
                'height': block_height,  
                'rawData': raw_block  
            }
            return True, block_info
        except Exception as e:  
            extra = {   
            }  
            return False, extra
    
    def get_BTC_block_header_DB(self, height_or_hash: int|str) -> Tuple[bool,dict]:
        if isinstance(height_or_hash,int):
            return self.get_BTC_block_header_by_height_DB(height_or_hash)
        else:
            return self.get_BTC_block_header_by_hash_DB(height_or_hash)
    
    def get_BTC_block_header_by_height_DB(self, block_height: int) -> Tuple[bool,dict]:
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='BTCRawData',
            key_columns={'height':block_height},
            columns_to_retrieve=['hash','rawData']
        )
        if db_result:
            if db_result['hash'][0:2] != '0x':
                block_hash = '0x' + db_result['hash']
            else:
                block_hash = db_result['hash']
            block_info = {  
                'hash': block_hash,   
                'height': block_height,  
                'rawData': db_result['rawData']  
            }
            return True, block_info
        return False, {}
    
    def get_BTC_block_header_by_hash_DB(self, block_hash: str) -> Tuple[bool,dict]:
        if block_hash[0:2] == '0x':
            tmp_block_hash = block_hash[2:]
        else:
            tmp_block_hash = block_hash
            block_hash = '0x' + block_hash
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='BTCRawData',
            key_columns={'hash':tmp_block_hash},
            columns_to_retrieve=['height','rawData']
        )
        if db_result:
            block_info = {  
                'hash': block_hash,   
                'height': int(db_result['height']),  
                'rawData': db_result['rawData']  
            }
            return True, block_info
        return False, {}

    def save_BTC_block_header_DB(self, block_info: dict) -> bool:
        
        block_hash = block_info['hash']
        if block_hash[0:2] == '0x':
            block_hash = block_hash[2:]
        db_result = self.db_manager.upsert_generic(
            table_name='BTCRawData',
            key_columns={'hash': block_hash},
            data={
                'height': block_info['height'],
                'rawData': block_info['rawData']
            }
        )
        if db_result:
            return True
        else:
            return False

class RelayerClient(StakeSystemContractListener,BTCBlockHeaderManager):
    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        multi_address: str,
        private_key: str,
        db_manager: DatabaseManager
    ):
        StakeSystemContractListener.__init__(
            self,
            rpc_url = rpc_url,
            contract_address = contract_address,
            multi_address= multi_address,
            private_key = private_key
        )
        BTCBlockHeaderManager.__init__(
            self,
            db_manager=db_manager
        )
        self.block_number = int(0)
        self.tmp_shadow_list: dict = {}
        self.genesis_hash: str = None
        self.if_check_genesis: bool = False
        self.account: eth_account.Account = eth_account.Account.from_key(private_key=private_key)


    def client(self):
        if not self.check_if_relay_work():
            return None
        if not self.check_if_relayer():
            return None
        for i in range(20):
            if not self.client_round():
                return None
        return True    
    
    def check_if_relay_work(self) -> bool:
        if not self.update_latest_block_number():
            return False
        rpc_result, state = self.get_my_state(self.block_number)
        if not rpc_result:
            return False
        rpc_result, genesis_hash = self.get_genesis_hash(self.block_number)
        if not rpc_result:
            return False
        self.genesis_hash = genesis_hash
        return (state == 2)
    
    def check_if_relayer(self) -> bool:
        if not self.update_latest_block_number():
            return False
        rpc_result, value_in_wei = self.get_require_stake(self.block_number)
        if not rpc_result:
            return False
        rpc_result, myStake = self.get_my_stake(self.block_number)
        if not rpc_result:
            return False
        if myStake >= 2 * value_in_wei:
            print("I am relayer")
        else:
            print("I am not relayer")
            value_in_wei_to_stake = 2 * value_in_wei - myStake
            rpc_result, tx = self.write_become_relayer(value_in_wei_to_stake)
            if not rpc_result:
                return False
            else:
                if not self.update_latest_block_number():
                    return False
                result, myStake = self.get_my_stake(self.block_number)
                if not result:
                    return False
                if myStake >= 2 * value_in_wei:
                    print("I am new relayer")
                    return True
                else:
                    return False
        return True

    
    def client_round(self) -> bool:
        if not self.update_latest_block_number():
            return False
        rpc_result, top_shadow_key = self.get_top_key_from_shadow_ledger(self.block_number)
        if not rpc_result:
            return False
        db_result, top_shadow_info = self.get_BTC_block_header(top_shadow_key)
        if not db_result:
            return False
        top_height:int = top_shadow_info['height']
        self.tmp_shadow_list.update({top_height:top_shadow_info})
        if not self.if_check_genesis:
            block_info = self.fetch_block(top_height + 1)
            rpc_result = self.get_commit_stake(self.block_number,block_info['hash'],top_shadow_key)
            if rpc_result == 0:
                print("I am the first relayer")
                self.if_check_genesis = True
                self.relay_new_block(top_height)
                return True
            else:
                print("I am not the first relayer")
                self.if_check_genesis = True
        self.relay_new_block(top_height + 1)
        return True

    def relay_new_block(self, height) -> bool:
        self.update_BTC_top_height()
        if self.source_top_height < height + 1:
            print("No new source block")
        else:
            prev_block = self.fetch_block(height)
            cur_block = self.fetch_block(height + 1)
            commit = self.commit_new_header(cur_block['rawData'])
            
            print(self.write_update_shadow_ledger(
                prev_raw=prev_block['rawData'],
                cur_key=cur_block['hash'],
                commit=commit
            ))
            

    def fetch_block(self, height) -> Optional[dict]:
        block_info = self.tmp_shadow_list.get(height)
        if block_info is not None:
            return block_info
        else:
            result, block_info = self.get_BTC_block_header(height)
            if not result:
                return None
            else:
                return block_info

    def update_latest_block_number(self) -> bool:
        rpc_result, block_number = self.get_latest_block_number()
        if not rpc_result:
            return False
        self.block_number = block_number
        return True
    
    def get_top_key_from_shadow_ledger(self, block: int = None):
        if block is None:
            block = self.block_number
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getTopKeyFromShadowLedger()(bytes32)" '   
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )  
        try:  
            rpc_result = foundry_cli(cmd)  
            top_key = rpc_result  
            return True, top_key  

        except Exception as e:  
            extra = {   
            }  
            return False, extra
    
    def get_genesis_hash(self, block: int = None):
        if block is None:
            block = self.block_number
        cmd = (  
            f'cast call {self.contract_address} '  
            f'"getGenesisHash()(bytes32)" '   
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )  
        try:  
            rpc_result = foundry_cli(cmd)  
            genesis_key = rpc_result  
            return True, genesis_key  

        except Exception as e:  
            extra = {   
            }  
            return False, extra

    def commit_new_header(self,hexHeader:str) -> str:
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
        valueList.append(self.account.address)
        hash = Web3.solidity_keccak(typeList,valueList)
        return Web3.to_hex(hash)

def main():  
    load_dotenv() 
    try:    
        db_manager = DatabaseManager(  
            host=os.getenv('DB_HOST'),  
            port=os.getenv('DB_PORT'),  
            user=os.getenv('DB_USER'),  
            password=os.getenv('DB_PASS'),
            database_name=os.getenv('DB_NAME'),
            logger=CrosschainZoneLogger.setup_logging(console_output=True)  
        )
        db_result = db_manager.get_specific_columns_by_key(
            table_name='crosschainzone_info',
            key_columns={'no': 0},
            columns_to_retrieve=['rpc','multi_addr']
        )
        if db_result is None:
            return None
        
        #print(db_result)
        result = getRelayContractAddress(symbol='BTC',rpc_url=db_result['rpc'],multi_address=db_result['multi_addr']) 
        if result is None:
            return None
        contract_address = result
        contract_listener = RelayerClient(
            rpc_url=db_result['rpc'],
            contract_address=contract_address,
            multi_address=db_result['multi_addr'],
            private_key = os.getenv('DEV_PRIVATE_KEY'),
            db_manager=db_manager
        )
        print(contract_listener.client())
        
        #
        #
        
    except Exception as e:  
        print(f"主程序发生错误: {e}")  
        sys.exit(1)  

if __name__ == '__main__':  
    main()  