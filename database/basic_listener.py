from abc import abstractmethod   
import json
import sys  
import time  
from typing import List, Tuple, Optional, Dict, Any, Union  
import signal
 
from foundrycli import foundry_cli
from dotenv import load_dotenv  
import os

from traitlets import This 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from crosschainzone_db import CrosschainZoneDatabaseManager as DatabaseManager
from item_info import SystemContractInfo,SourceChainInfo,HubChainInfo
from listener_task import TaskManager,TaskProcessor,Task,TaskType,DBWriteData
class ContractListener():  
    def __init__(  
        self,   
        rpc_url: str,
        contract_address: str,
    ):   
        self.rpc_url = rpc_url
        self.contract_address = contract_address        
    
    def parse_bytes32_address(self, bytes32_addr: str) -> Tuple[bool, Union[str, dict]]:  
        """  
        Parse bytes32 format address to standard Ethereum address.  
        
        Args:  
            bytes32_addr: Address in bytes32 format  
            
        Returns:  
            Tuple[bool, str]:  
            - First element: True if parsing succeeds, False if fails  
            - Second element: Parsed address if successful, error message if failed  
        """  
        try:  
            rpc_result = foundry_cli(f'cast parse-bytes32-address {bytes32_addr}')  
            return True, rpc_result  
        except Exception as e:  
            extra = {  
                'operation': 'parse_bytes32_address',  
                'bytes32_addr': bytes32_addr,  
                'error': str(e)  
            }    
            return False, extra  
    
    def get_latest_block_number(self) -> Tuple[bool,int|dict]:  
        """  
        Get the latest block number from the blockchain.  
        
        Returns:  
            Tuple[bool, Union[int, str]]:  
            - First element: True if successful, False if failed  
            - Second element: Block number if successful, error message if failed  
        """  
        try:  
            block_number = int(foundry_cli(f'cast block-number --rpc-url {self.rpc_url}'))  
            return True, block_number   
        except Exception as e:   
            extra = {  
                'operation': 'get_latest_block_number',  
                'params': {},
                'error_type': type(e).__name__,  
                'message': str(e)    
            }  
            return False, extra
    
    def listen_events(  
        self,
        begin: int,
        end: int,
        addr: Optional[str] = None   
    ) -> Tuple[bool, Union[List[dict], dict]]:  
        """  
        Listen for contract events within specified block range  

        Args:  
            end: Ending block height  
            
        Returns:  
            Tuple[bool, Union[List[dict], str]]:  
            - First element: True if successful, False if failed  
            - Second element: List of events if successful, error message if failed  
            
        Note:  
            - Uses foundry cast command to fetch events  
            - Block range from self.begin to specified end  
            - Events are sorted by block height ascending  
        """  
        try:  
            # Build cast logs command
            if addr is None:
                addr = self.contract_address  
            cmd = (  
                f'cast logs '  
                f'--address {addr} '  
                f'--rpc-url {self.rpc_url} '  
                f'--from-block {begin} '  
                f'--to-block {end} '  
                f'-j'  # Output as JSON  
            )  
            
            # Execute command to get events  
            events = foundry_cli(cmd)  
            
            return True, events  

        except Exception as e:  
            # Build error details  
            extra = {  
                'operation': 'listen_events',
                'params': {
                    'contract': addr,  
                    'from_block': begin,  
                    'to_block': end,
                },  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }      
            return False, extra

    def list_str(list_data: list) -> str:
        return ",".join(list_data)
    
    def str_list(str_data: str) -> list:
        return str_data.split(",")

    def parse_event(self, event: dict) -> Tuple[dict, dict]:
        event_info = {
            "contract_addr": event['address'],
            "event_sig": event['topics'][0],
            "event_topic": ContractListener.list_str(event['topics'][1:]),
            "event_data": event['data'],
            "event_index": int(event['transactionLogIndex'],16),
            "tx_hash": event['transactionHash']  
        }
        tx_info = {
            "tx_index": int(event['transactionIndex'],16),
            "block_hash": event['blockHash']
        }
        return event_info, tx_info
    
    def get_block_info(self, block_hash:str) -> Tuple[bool,dict]:
        try:
            cmd = (  
                f'cast block {block_hash} '  
                f'--rpc-url {self.rpc_url} '   
                f'--json' 
            )
            rpc_result = foundry_cli(cmd)
            prev_hash = rpc_result["parentHash"]
            block_height = int(rpc_result["number"],16)
            block_info = {
                "prev_hash": prev_hash, 
                "block_height": block_height
            }
            return True, {block_hash:block_info}
        except Exception as e:   
            extra = {  
                'operation': 'get_block_info',  
                'params': {'block_hash': block_hash},
                'error_type': type(e).__name__,  
                'message': str(e)    
            }  
            return False, extra
    
    def get_tx_info(self, tx_hash:str) -> Tuple[bool,dict]:
        try:
            cmd = (  
                f'cast tx {tx_hash} '  
                f'--rpc-url {self.rpc_url} '   
                f'-j' 
            )
            rpc_result = foundry_cli(cmd)
            block_hash = rpc_result["blockHash"]
            tx_index = int(rpc_result["transactionIndex"],16)
            tx_info = {
                "block_hash": block_hash,
                "tx_index": tx_index
            }
            return True, tx_info
        except Exception as e:   
            extra = {  
                'operation': 'get_tx_info',  
                'params': {'tx_hash': tx_hash},
                'error_type': type(e).__name__,  
                'message': str(e)   
            }   
            return False, extra    

class SystemContractListener(ContractListener):   
    def __init__(  
        self,   
        rpc_url: str,
        contract_address: str,
        multi_address: str = None
    ):   
        ContractListener.__init__(
            self,
            rpc_url=rpc_url,
            contract_address=contract_address,
        )
        self.multi_address = multi_address
        self.event_signatures={  
            "UpdateContractInfo": "0x1f3eff3cfedf1665c0e88a9a9282ad6604e4c5d9b8e1282e2b5ecda89de78e9b",
            "UpdateChainInfo": "0x4d0b8309615448c317b4a179cde98e9a0c5d77e4637f3be004f7c3c14d19fb4a",
            "UpdateShadowLedger": "0xf84b95d9a1dd29294edf6b0d3aa10096d7a5da82d1ce5be5c9efd6ccabb5777e",
            "OpenOldCommit": "0x3d6a8e5ef4d505e0b03ec65b743caffc5a90079d0a6851c06646d0878cfa89e3",
            "SubmitNewCommit":"0xecb32623cdb13b96fe5fe2ba21058d1fd83ed4a7ae572310702d3e2cf9fdca2c",
            "RecordRelayerContribution": ""  
        }        
    
    def get_my_manager(self, block: int, addr: str = None) -> Optional[bool]:
        """  
        Get and verify contract manager address.  
        
        Returns:  
            Optional[bool]:  
            - True if manager unchanged  
            - False if manager changed  
            - None if operation failed  
        """
        if addr is None:
            addr = self.contract_address
        cmd = (  
            f'cast call {addr} '  
            f'"getContractManager()(address)" '
            f'--block {block} '   
            f'--rpc-url {self.rpc_url}'  
        )    
        try:
            manager = foundry_cli(cmd)
            return True, manager
        except Exception as e:  
            extra = {  
                'operation': 'get_contract_manager',
                'params': {
                    'contract_address': addr,
                    'block_number': block
                },  
                'error_type': type(e).__name__r,  
                'message': str(e)   
            }     
            return False, extra
    
    def get_my_state(self, block: int, addr: str = None) -> Tuple[bool,int|dict]:  
        """  
        Get and verify contract state.  
        
        Returns:  
            Optional[bool]:  
            - True if state unchanged  
            - False if state changed  
            - None if operation failed  
        """  
        try:    
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getContractState()(uint)" '  
                f'--rpc-url {self.rpc_url}'  
            )  
            state = int(foundry_cli(cmd))    
            return True, state  

        except Exception as e:  
            extra = {  
                'operation': 'get_my_state',  
                'params': {'contract_address': self.contract_address},
                'error_type': type(e).__name__,  
                'message': str(e)    
            }  
            return False, extra

class MultiContractListener(SystemContractListener):
    def __init__(  
        self,      
        rpc_url: str,
        contract_address: str,   
        multi_address: str
    ):   
        SystemContractListener.__init__(
            self,
            rpc_url = rpc_url,
            contract_address = contract_address,
            multi_address = multi_address
        )
                
    def get_hub_info(self, block: int, addr: str = None) -> Tuple[bool, tuple[str, str, int, int]|dict]:  
        """  
        Retrieve and update hub chain information from manager contract  

        Returns:    
        """  
        if addr is None:
            addr = self.multi_address
        cmd_1 = (  
            f'cast call {addr} '  
            f'"getHubChainInfo()(uint256,string,string,uint256,address[])" '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )
        cmd_2 = (  
            f'cast call {addr} '  
            f'"getSourceChainNum()(uint256)" '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )
        cmd_3 = (  
            f'cast call {addr} '  
            f'"getSystemContractNum()(uint256)" '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )
        try:    
            rpc_result_1 = foundry_cli(cmd_1).split('\n')
            rpc_result_2 = foundry_cli(cmd_2)
            rpc_result_3 = foundry_cli(cmd_3)     
            symbol = rpc_result_1[1]  
            name = rpc_result_1[2]    
            source_num = int(rpc_result_2)  
            contract_num = int(rpc_result_3)  
            return True, (symbol, name, source_num, contract_num) 

        except Exception as e:  
            extra = {  
                'operation': 'get_hub_info',  
                'params': {
                    'contract_address': addr,
                    'block_number': block
                },    
                'error_type': type(e).__name__,  
                'message': str(e)  
            }
            return False, extra 
    
    def get_single_source_info(self, chain_id: int, block: int, addr: str = None) -> Tuple[bool, tuple[str, str, int]|dict]:  
        """  
        Retrieve and update source chain information from manager contract  

        Args:  
            chain_id (int): chain_id of source chain  
        
        Returns:  
             
        """  
        if chain_id <= 0:  
            extra = {  
                'operation': 'get_single_source_info',  
                'params': {
                    'contract_address': addr,
                    'block_number':block,
                    'chain_id':chain_id
                },  
                'error_type': 'InputParamError',  
                'message': f'Chain id is wrong'  
            }  
            return False, extra   
        if addr is None:
            addr = self.multi_address
        cmd = (  
            f'cast call {addr} '  
            f'"getSourceChainInfo(uint256)(string,string,uint256,uint256,address[])" {chain_id} '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        )
        try:  
            rpc_result = foundry_cli(cmd).split('\n')  
            symbol = rpc_result[0]  
            name = rpc_result[1]  
            state = int(rpc_result[2])  
            return True, (symbol, name, state)  

        except Exception as e:  
            extra = {  
                'operation': 'get_single_source_info',  
                'params': {
                    'contract_address': addr,
                    'block_number':block,
                    'chain_id':chain_id
                },     
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra      
    
    def get_system_contract_address_by_id(self, contract_id: int, block: int, addr: str = None) -> Tuple[bool,str|dict]:
        if addr is None:
            addr = self.multi_address
        cmd = (  
            f'cast call {addr} '  
            f'"getSystemContractAddressByID(uint256)(address)" {contract_id} '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        ) 
        try:      
            rpc_result = foundry_cli(cmd)
            contract_address = rpc_result
            return True, contract_address
        except Exception as e:    
            extra = {  
                'operation': 'get_system_contract_address_by_id',  
                'params': {
                    'contract_address': addr,
                    'block_number': block,
                    'contract_id': contract_id
                },     
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return False, extra 
    
    def get_system_contract_info_by_address(self, contract_addr: str, block: int, addr: str = None) -> Tuple[bool,tuple[int, int, int]|dict]:  
        """  
        Retrieve system contract information from manager contract  

        Args:  
            contract_addr (str): address of system contract  
        
        Returns:   
            - Tuple[int,int,int]: System contract information  
            - None: Retrieval failed  
        """  
        if addr is None:
            addr = self.multi_address
        cmd = (  
            f'cast call {addr} '  
            f'"getSystemContractInfo(address)(uint256,uint256,uint256,uint256)" {contract_addr} '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        ) 
        try:    
            rpc_result = foundry_cli(cmd).split('\n')  
            contract_id = int(rpc_result[0])  
            chain_id = int(rpc_result[1])  
            level_id = int(rpc_result[2])  
            state = int(rpc_result[3])  

            if contract_id == 0 and contract_addr != addr:  
                extra = {  
                    'operation': 'get_system_contract_info_by_address',  
                    'params': {
                        'contract_address': addr,
                        'block_number': block,
                        'search_addr': contract_addr,
                    },  
                    'error_type': 'InputParamError',  
                    'message': f'Contract address is wrong'  
                }  
                return False, extra   
 
            return True, (chain_id, level_id, state)  

        except Exception as e:  
            extra = {  
                'operation': 'get_system_contract_info_by_address',  
                'params': {
                    'contract_address': addr,
                    'block_number': block,
                    'search_addr': contract_addr,
                },
                'error_type': type(e).__name__,  
                'message': str(e)     
            }  
            return False, extra 
    
    def get_source_chain_id_by_symbol(self, symbol: str, block: int, addr: str = None) -> Tuple[bool,int|dict]:
        if addr is None:
            addr = self.multi_address
        cmd = (  
            f'cast call {addr} '  
            f'"getSourceChainIDBySymbol(string)(uint256)" {symbol} '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        ) 
        try:    
            rpc_result = foundry_cli(cmd)  
            chain_id = int(rpc_result)     
            return True, chain_id  

        except Exception as e:  
            extra = {  
                'operation': 'get_source_chain_id_by_symbol',  
                'params': {
                    'contract_address': addr,
                    'block_number': block,
                    'symbol': symbol,
                },
                'error_type': type(e).__name__,  
                'message': str(e)     
            }  
            return False, extra 

    def get_contract_address_by_level_id(self, chain_id: int, level_id: int, block: int, addr: str = None) -> Tuple[bool,str|dict]:
        if addr is None:
            addr = self.multi_address
        cmd = (  
            f'cast call {addr} '  
            f'"getSystemContractAddressByLevelID(uint256,uint256)(address)" {chain_id} {level_id} '
            f'--block {block} '  
            f'--rpc-url {self.rpc_url}'  
        ) 
        try:    
            rpc_result = foundry_cli(cmd)  
            address = rpc_result     
            return True, address  

        except Exception as e:  
            extra = {  
                'operation': 'get_contract_address_by_level_id',  
                'params': {
                    'contract_address': addr,
                    'block_number': block,
                    'chain_id': chain_id,
                    'level_id': level_id,
                },
                'error_type': type(e).__name__,  
                'message': str(e)     
            }  
            return False, extra 


class CrosschainZoneListener(MultiContractListener):    
    def __init__(  
        self,      
        rpc_url: str,
        multi_address: str,   
        db_manager: DatabaseManager,
    ):   
        MultiContractListener.__init__(
            self,
            rpc_url = rpc_url,
            contract_address = multi_address,
            multi_address = multi_address
        )
        self.db_manager = db_manager
        
        self.chain_id: int = 0
        self.contract_id:int = 0
        self.level_id: int = 0
        
        self.contract_list: Dict[int,str] = {self.contract_id:self.contract_address}
        self.new_contract_list: Dict[int,str] = {}
        self.chain_list: set[int] = {self.chain_id}
        
        self.latest_block_number: int = 0
        self.begin: int = 0
        self.end: int = 0
        
        self.running = True 
        signal.signal(signal.SIGINT, self.signal_handler)  
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):    
        print(f"\nReceived signal {signum}")  
        self.running = False 
    
    def client(self):
        print("Checking if manager contract listener inited")
        if not self.db_init():
            return None
        print("Running listener for history events")
        if not self.client_init():
            return None
        if not self.client_prepare():
            return None
        
        self.running = True
        while self.running:
            if not self.start_listen_contracts(
                contract_list=self.contract_list,
                begin_block_num = self.begin,
                end_block_num = self.latest_block_number
            ):
                return None
            if not self.update_db_visit_block_height():
                return None
            self.begin = self.latest_block_number + 1
            print("Running listener for new events")
            time.sleep(5)
            if not self.update_latest_block_number():
                return None
        print("Shutting down manager contract listener...")
        sys.exit(0) 
    
    def db_init(self) -> bool:
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='crosschainzone_info',  
            key_columns={'no': 0},  
            columns_to_retrieve=['visit_block_height']  
            )
        if not isinstance(db_result, dict):  
            extra = {  
                'operation': 'check_db_if_init',  
                'error_type': 'DBError',
                'message': 'Failed to retrieve database',    
            }  
            self.db_manager.logger.error(f"Operation failed | {extra}")  
            return False 
        self.begin = int(db_result['visit_block_height']) + 1
        return True
    
    def client_init(self) -> bool:
        result1 = self.check_hub_if_init()
        result2 = self.check_multi_if_init()
        if result1 and result2:
            return True
        else:
            return False
                
    def client_prepare(self) -> bool:
        if not self.update_latest_block_number():
            return False
        if not self.prepare_contract_list_to_listen():
            return False
        if not self.new_contract_list:
            if not self.start_listen_contracts(
                contract_list=self.new_contract_list,
                begin_block_num = 0,
                end_block_num = self.begin
            ):
                return False
            self.new_contract_list.clear()
        return True
    
    def check_hub_if_init(self) -> bool:
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='hub_chain_info',  
            key_columns={'chain_id': 0},  
            columns_to_retrieve=['visit_block_height']  
            )
        if isinstance(db_result, dict):
            return True
        elif db_result is False:
            upsert_result = self.db_manager.upsert_generic(
                table_name='hub_chain_info',
                key_columns={'chain_id': 0},
                data={
                    'symbol': 'HC',
                    'name': 'HubChain',
                    'source_chain_num': 0,
                    'system_contract_num': 1,
                    'visit_block_height': 0
                }
            )
            if upsert_result is None:
                return False
            return True
        elif db_result is None:
            return False
    
    def check_multi_if_init(self) -> bool:
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='system_contract_info',  
            key_columns={'contract_id': 0},  
            columns_to_retrieve=['visit_block_height']  
            )
        if isinstance(db_result, dict):
            return True
        elif db_result is False:
            upsert_result = self.db_manager.upsert_generic(
                table_name='system_contract_info',
                key_columns={'contract_id': 0},
                data={
                    'contract_addr': self.multi_address,
                    'manager_addr': self.contract_address,
                    'contract_state': 2,
                    'chain_id': 0,
                    'level_id': 0,
                    'visit_block_height': 0,
                }
            )
            if upsert_result is None:
                return False
            return True
        elif db_result is None:
            return False
    
    def update_latest_block_number(self) -> bool:
        rpc_result, info = self.get_latest_block_number()
        if not rpc_result:
            self.db_manager.logger.error(f"Operation failed | {info}") 
            return False
        else:
            self.latest_block_number = info
            return True
    
    def prepare_contract_list_to_listen(self) -> Optional[bool]:
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='hub_chain_info',  
            key_columns={'chain_id': int(0)},  
            columns_to_retrieve=['source_chain_num','system_contract_num']  
            )
        if not isinstance(db_result, dict):
            return None
        old_contract_num = int(db_result['system_contract_num'])
        old_source_num = int(db_result['source_chain_num'])
        for contract_id in range(1,old_contract_num):
            result, info = self.get_system_contract_address_by_id(contract_id,self.latest_block_number,addr=self.multi_address)
            if not result: 
                self.db_manager.logger.error(f"Operation failed | {info}") 
                return None
            contract_addr = info
            self.contract_list.update({contract_id:contract_addr})
        for chain_id in range(1,1 + old_source_num):
            self.chain_list.add(chain_id)
        rpc_result, info = self.get_hub_info(self.latest_block_number,addr=self.multi_address)     
        if not rpc_result:
            self.db_manager.logger.error(f"Operation failed | {info}")
            return None
        symbol, name, new_source_num, new_contract_num = info
        
        
        for contract_id in range(old_contract_num, new_contract_num):
            if not self.record_new_system_contract(contract_id):
                return None
        for chain_id in range(1 + old_source_num, 1 + new_source_num):
            if not self.record_new_source_chain(chain_id):
                return None    
        
        db_result = self.db_manager.upsert_generic(  
            table_name="hub_chain_info",
            key_columns={'chain_id': 0},
            data={
                'symbol': symbol,
                'name': name,
                'source_chain_num': new_source_num,  
                'system_contract_num': new_contract_num,  
                'visit_block_height': self.latest_block_number
            }
        )
        if db_result is None:
            return None
        else:
            return True
    
    def record_new_source_chain(self, chain_id:int) -> bool:
        rpc_result, info = self.get_single_source_info(chain_id,self.latest_block_number,addr=self.multi_address)     
        if not rpc_result:
            self.db_manager.logger.error(f"Operation failed | {info}") 
            return False
        symbol, name, state = info
        db_result = self.db_manager.upsert_generic(  
            table_name="source_chain_info",
            key_columns={'chain_id': chain_id},
            data={
                'symbol': symbol,
                'name': name,
                'state': state,    
                'visit_block_height': self.latest_block_number,
            }
        )
        if db_result is None:
            return False
        self.chain_list.add(chain_id)
        return True
   
    def record_new_system_contract(self,contract_id:int) -> bool:
        #create new table
        #init info in system_contract_info
        rpc_result, info = self.get_system_contract_address_by_id(contract_id,self.latest_block_number,addr=self.multi_address)
        if not rpc_result:
            self.db_manager.logger.error(f"Operation failed | {info}") 
            return False
        contract_addr = info
        rpc_result, info = self.get_system_contract_info_by_address(contract_addr,self.latest_block_number,addr=self.multi_address)
        if not rpc_result:
            self.db_manager.logger.error(f"Operation failed | {info}")
            return False
        chain_id, level_id, state = info
        db_result = self.db_manager.upsert_generic(  
            table_name="system_contract_info",
            key_columns={'contract_id': contract_id},
            data={
                'contract_addr': contract_addr,
                'manager_addr': self.contract_address,
                'contract_state': state,
                'chain_id': chain_id,
                'level_id': level_id,  
                'visit_block_height': self.latest_block_number,
            }
        )
        if db_result is None:
            return False
        self.new_contract_list.update({contract_id:contract_addr})
        return True
    
    def start_listen_contracts(self, contract_list: dict, begin_block_num: int, end_block_num) -> bool:
        
        if begin_block_num > end_block_num:
            print("No new block detected")
            return True
        tx_list: Dict[str,Any] = {}
        block_list: Dict[str,Any] = {}  
        for contract_id, contract_addr in contract_list.items():
            rpc_result, events = self.listen_events(
                addr=contract_addr,
                begin=begin_block_num,
                end=end_block_num
            )
            if not rpc_result:
                return False
            result = self.process_events(events, tx_list, block_list)
            if result is None:
                return False
            tx_list, block_list = result
            if contract_id in self.new_contract_list:
                self.new_contract_list.pop(contract_id)
                self.contract_list.update({contract_id:contract_addr})
        for contract_id, contract_addr in self.new_contract_list.items():
            rpc_result, events = self.listen_events(addr=contract_addr,begin=0, end=end_block_num)
            if not rpc_result:
                return False
            result = self.process_events(events, tx_list, block_list)
            if result is None:
                return False
            tx_list, block_list = result
            self.contract_list.update({contract_id:contract_addr})
        self.new_contract_list.clear()
        
        for tx_hash, tx_info in tx_list.items():
            db_result = self.db_manager.upsert_generic(  
                table_name="hub_tx_info",
                key_columns={'tx_hash': tx_hash},
                data=tx_info
            )
            if db_result is None:
                return False
        for block_hash, block_info in block_list.items():
            db_result = self.db_manager.upsert_generic(  
                table_name="hub_block_info",
                key_columns={'block_hash': block_hash},
                data={
                    'prev_hash': block_info['prev_hash'], 
                    'block_height': block_info['block_height'],
                    'if_matter': True
                }
            )
            if db_result is None:
                return False
        return True
    
    def process_events(self, events: list[dict], tx_list: dict, block_list: dict) -> Optional[tuple[dict, dict]]:
        for event in events:
            result = self.process_single_event(event,tx_list,block_list)
            if result is not None:
                tx_list, block_list = result
            else:
                return None
        return tx_list, block_list
    
    def process_single_event(self, event: dict, tx_list: dict, block_list: dict) -> Optional[tuple[dict, dict]]:   
        if_event_process = False
        event_sig = event['topics'][0]
        if event_sig == self.event_signatures["UpdateChainInfo"]:
            chain_id = int(event['topics'][1],16)
            if chain_id not in self.chain_list:
                self.record_new_source_chain(chain_id)
                if_event_process = True
        elif event_sig == self.event_signatures["UpdateContractInfo"]:
            contract_id = int(event['topics'][1],16)
            if contract_id not in self.contract_list:
                self.record_new_system_contract(contract_id)
                if_event_process = True    
        event_info, tx_info = self.parse_event(event)
        tx_hash = event_info['tx_hash']
        if tx_hash not in tx_list:
            tx_list.update({tx_hash:tx_info})
            block_hash = tx_info['block_hash']
            if block_hash not in block_list:
                rpc_result, block_info = self.get_block_info(block_hash)
                if rpc_result:
                    block_list.update(block_info)
                else:
                    self.db_manager.logger.error(f"Failed to get block info | {block_info}")
                    return None
                
        db_result = self.db_manager.upsert_generic(  
            table_name="event_info",
            key_columns={'tx_hash': tx_hash,'event_index':event_info['event_index']},
            data={
                'contract_addr': event_info['contract_addr'],
                'event_sig': event_info['event_sig'],
                'event_topic': event_info['event_topic'],
                'event_data': event_info['event_data'],
                'if_process': if_event_process 
                }
            )
        if db_result is None:
            return None
        return tx_list, block_list   
      
    def update_db_visit_block_height(self) -> bool:
        db_result = self.db_manager.upsert_generic(
            table_name='crosschainzone_info',  
            key_columns={'no': 0},  
            data={'visit_block_height': self.latest_block_number}  
            )
        if db_result is None:
            return False
        self.begin = self.latest_block_number + 1
        return True
    
 

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
         
        manager_listener = CrosschainZoneListener(
            rpc_url=db_result['rpc'],
            db_manager=db_manager,
            multi_address=db_result['multi_addr'],
        )
        print(manager_listener.client())    
    except Exception as e:  
        print(f"主程序发生错误: {e}")  
        sys.exit(1)  

if __name__ == '__main__':  
    main()  