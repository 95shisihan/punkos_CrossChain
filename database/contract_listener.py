from abc import abstractmethod
import argparse    
import sys  
import time  
from typing import List, Tuple, Optional, Dict, Any, Union  
import threading
 
from foundrycli import foundry_cli
from dotenv import load_dotenv  
import os 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from crosschainzone_db import CrosschainZoneDatabaseManager as DatabaseManager
from item_info import SystemContractInfo,SourceChainInfo,HubChainInfo
from listener_task import TaskManager,TaskProcessor,Task,TaskType,DBWriteData
class ContractEventListener(threading.Thread):  
    def __init__(  
        self,   
        rpc_url: str,
        contract_address: str,
        task_manager: TaskManager
    ):   
        threading.Thread.__init__(self)
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.begin: int = 0
        self.task_manager = task_manager        
    def parse_bytes32_address(self, bytes32_addr: str) -> Tuple[bool, str]:  
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
            result = foundry_cli(f'cast parse-bytes32-address {bytes32_addr}')  
            return True, result  
            
        except Exception as e:  
            extra = {  
                'operation': 'parse_bytes32_address',  
                'bytes32_addr': bytes32_addr,  
                'error': str(e),  
                'status': 'error'  
            }  
            error_info = f"Failed to parse address | {extra}"  
            return False, error_info  
    def get_latest_block_number(self) -> Tuple[bool, Union[int, str]]:  
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
                'rpc_url': self.rpc_url,  
                'error': str(e),  
                'status': 'error'  
            }  
            error_info = f"Failed to get latest block number | {extra}"  
            return False, error_info
    def listen_events(  
        self,  
        end: int  
    ) -> Tuple[bool, Union[List[dict], str]]:  
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
            cmd = (  
                f'cast logs '  
                f'--address {self.contract_address} '  
                f'--rpc-url {self.rpc_url} '  
                f'--from-block {self.begin} '  
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
                'contract': self.contract_address,  
                'from_block': self.begin,  
                'to_block': end,  
                'error': str(e),  
                'status': 'error'  
            }  
            error_info = f"Failed to fetch contract events | {extra}"  
            return False, error_info 
class SystemContractEventListener(SystemContractInfo,ContractEventListener):   
    def __init__(  
        self,   
        rpc_url: str,
        db_manager: DatabaseManager,
        task_manager: TaskManager,
        multi_address: str,
        contract_address: str = '',
        contract_id: int = -1,
        chain_id: int = -1,
        level_id: int = -1,
        state: int = 0,
        manager_address: str = ''
    ):   
        SystemContractInfo.__init__(  
            self,  
            contract_address=contract_address,  
            contract_id=contract_id,  
            chain_id=chain_id,  
            level_id=level_id,  
            state=state,  
            manager_address=manager_address  
        )
        ContractEventListener.__init__(
            self,
            rpc_url=rpc_url,
            contract_address=contract_address,
            task_manager=task_manager
        )
        self.multi_address = multi_address
        self.db_manager = db_manager
    def update_event_begin(self) -> Optional[int]:
        res = self.db_manager.get_contract_visit_height(self.contract_id)
        if res is None:
            return None
        else:
            self.begin = res
            return res      
    def get_contract_manager(self) -> Optional[bool]:
        """  
        Get and verify contract manager address.  
        
        Returns:  
            Optional[bool]:  
            - True if manager unchanged  
            - False if manager changed  
            - None if operation failed  
        """
        try:
            old_manager = self.manager_address
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getContractManager()(address)" '  
                f'--rpc-url {self.rpc_url}'  
            )
            new_manager = foundry_cli(cmd)
            if old_manager == new_manager:
                return True
            else:
                self.manager_address = new_manager
                extra = {  
                    'operation': 'get_contract_manager',  
                    'contract_id': self.contract_id,
                    'contract_addr': self.contract_address,  
                    'old_manager': old_manager,  
                    'new_manager': new_manager  
                }  
                self.db_manager.logger.info(f"Contract manager changed | {extra}")  
                return False
        except Exception as e:  
            extra = {  
                'operation': 'get_contract_manager',  
                'contract_id': self.contract_id,
                'contract_addr': self.contract_address,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to get contract manager | {extra}")   
            return None
    def get_contract_state(self) -> Optional[bool]:  
        """  
        Get and verify contract state.  
        
        Returns:  
            Optional[bool]:  
            - True if state unchanged  
            - False if state changed  
            - None if operation failed  
        """  
        try:  
            old_state = self.state  
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getContractState()(uint)" '  
                f'--rpc-url {self.rpc_url}'  
            )  
            new_state = int(foundry_cli(cmd))  
            
            if old_state == new_state:  
                return True  
                  
            self.state = new_state  
            extra = {  
                'operation': 'get_contract_state',  
                'contract_id': self.contract_id,  
                'contract_addr': self.contract_address,  
                'old_state': old_state,  
                'new_state': new_state  
            }  
            self.db_manager.logger.info(f"Contract state changed | {extra}")  
            return False  

        except Exception as e:  
            extra = {  
                'operation': 'get_contract_state',  
                'contract_id': self.contract_id,  
                'contract_addr': self.contract_address,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to get contract state | {extra}")  
            return None 
    def create_db_write_task(self, data: DBWriteData):  
        task = Task(  
            task_type=TaskType.DB_WRITE,  
            data=data,  
            priority=0  
        )  
        self.task_manager.add_task(task)
class ManagerContractEventListener(SystemContractEventListener,HubChainInfo):    
    def __init__(  
        self,      
        rpc_url: str,  
        db_manager: DatabaseManager,
        task_manager: TaskManager,
        contract_address: str 
    ):   
        SystemContractEventListener.__init__(
            self,
            rpc_url=rpc_url,
            contract_address=contract_address,
            contract_id=0,
            chain_id=0,
            level_id=0,
            multi_address=contract_address,
            db_manager = db_manager,
            task_manager=task_manager
        )
        HubChainInfo.__init__(self)
        self.source_num:int = 0
        self.contract_num:int = 0
        self.event_signatures={  
            "UpdateContractInfo": "0x9dad43a7b4a76afed98c6a24f82688b4418e8fc9c31f37fc877d77f73477f8c9",
            "UpdateChainInfo": "0x4d0b8309615448c317b4a179cde98e9a0c5d77e4637f3be004f7c3c14d19fb4a",  
        }
        self.source_list: Dict[int:SourceChainInfo] = {}
        self.contract_list: Dict[int:SystemContractInfo] = {}
        self.chain_to_update = set()
        self.contract_to_update = set()
        self.relay_listeners: Dict[int, RelayContractEventListener] = {}
    
    def create_relay_listener(
        self,
        contract_info: SystemContractInfo,
        chain_info: SourceChainInfo
    ):   
        chain_id = contract_info.chain_id
        if chain_id not in self.relay_listeners:  
            relay_listener = RelayContractEventListener(  
                rpc_url=self.rpc_url,
                db_manager=self.db_manager,
                task_manager=self.task_manager,
                contract_id=contract_info.contract_id,
                chain_id=chain_id,
                symbol=chain_info.symbol,
                name=chain_info.name
            )  
            self.relay_listeners.update({chain_id:relay_listener})  
            relay_listener.start()  
    
    def add_to_set(
        item_to_update: set,
        new_id: int
    ) -> set:
        if new_id not in item_to_update:  
            item_to_update.add(new_id)  
        return item_to_update  
    
    def directly_update_manager_contract_info(self) -> Optional[bool]:  
        """  
        Retrieve and update manager contract information from manager contract  

        Returns:  
            Optional[bool]:  
            - True: First run listener and inserted manager contract information  
            - False: Updated manager contract information  
            - None: Retrieval failed  
        """
        res = self.get_contract_state()
        if res is None:
            return None
        res = self.get_contract_manager()
        if res is None:
            return None
        return self.db_manager.upsert_generic(  
            table_name="System_Contract",
            key_columns={'contract_id': 0},
            data={
                'contract_addr': self.contract_address,
                'manager_addr': self.manager_address,
                'chain_id': self.chain_id,  
                'level_id': self.level_id,  
                'state': self.state
            }      
        )
    
    def get_hub_info(self) -> Optional[bool]:  
        """  
        Retrieve and update hub chain information from manager contract  

        Returns:  
            Optional[bool]:  
            - True: No changes in hub chain information  
            - False: Hub chain information updated  
            - None: Retrieval failed  
        """  
        try:    
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getHubChainInfo()(uint256,string,string,uint256,address[])" '  
                f'--rpc-url {self.rpc_url}'  
            )
            res = foundry_cli(cmd).split('\n')    
            symbol = res[1]  
            name = res[2]    
            source_num = int(foundry_cli(  
                f'cast call {self.contract_address} '  
                f'"getSourceChainNum()(uint256)" '  
                f'--rpc-url {self.rpc_url}'  
            ))  
            contract_num = int(foundry_cli(  
                f'cast call {self.contract_address} '  
                f'"getSystemContractNum()(uint256)" '  
                f'--rpc-url {self.rpc_url}'  
            ))  
            # Track changes  
            changes = {}  
            
            # Compare and update attributes  
            if self.symbol != symbol:  
                self.symbol = symbol  
                changes['symbol'] = symbol  
            if self.name != name:  
                self.name = name  
                changes['name'] = name  
            if self.source_num != source_num:  
                self.source_num = source_num  
                changes['source_num'] = source_num  
            if self.contract_num != contract_num:  
                self.contract_num = contract_num  
                changes['contract_num'] = contract_num  
         
            if changes:  
                extra = {  
                    'operation': 'get_hub_info',    
                    'changes': changes  
                }  
                self.db_manager.logger.info(f"Hubchain information updated | {extra}")  
                return False  
            return True  

        except Exception as e:  
            extra = {  
                'operation': 'get_hub_info',  
                'chain_id': self.chain_id,  
                'contract_addr': self.contract_address,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to retrieve hub chain information | {extra}")  
            return None 
    
    def update_hub_info_in_db(self) -> Optional[bool]:  
        """  
        Wrapper method to update hub information in database  

        Returns:  
            Optional[bool]:  
            - True: No changes in hub information  
            - False: Hub information successfully updated  
            - None: Failed to process hub information  
        """   
        retrieval_result = self.get_hub_info()   
        if retrieval_result is not False:    
            return retrieval_result  
        task: DBWriteData = Task(
            table_name='Hub_Info',  
            key_columns={'chain_id': self.chain_id},   
            data={  
                'symbol': self.symbol,  
                'name': self.name,  
                'source_num': self.source_num,  
                'contract_num': self.contract_num,  
                'rpc': self.rpc_url,
                'multi_addr': self.contract_address,  
            }
        )
        self.create_db_write_task(task)  
        return False     
    
    def get_single_source_info(self, chain_id: int) -> Optional[bool]:  
        """  
        Retrieve and update source chain information from manager contract  

        Args:  
            chain_id (int): chain_id of source chain  
        
        Returns:  
            Optional[bool]:  
            - True: No changes in source chain information  
            - False: Source chain information updated  
            - None: Retrieval failed  
        """  
        if chain_id <= 0:  
            extra = {  
                'operation': 'get_single_source_info',  
                'chain_id': chain_id,  
                'error': 'Invalid chain ID',  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Invalid chain ID for source info retrieval | {extra}")  
            return None  

        try:  
            # Get basic chain info  
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getSourceChainInfo(uint256)(string,string,uint256,uint256,address[])" {chain_id} '  
                f'--rpc-url {self.rpc_url}'  
            )  
              
            res = foundry_cli(cmd).split('\n')  
            symbol = res[0]  
            name = res[1]  
            state = int(res[2])  
            contract_num = int(res[3])   

            # Get contract addresses  
            contract_list = [""]*3  
            for index in range(contract_num):  
                try:  
                    cmd = (  
                        f'cast call {self.contract_address} '  
                        f'"getSystemContractAddressByLevelID(uint256,uint256)(address)" {chain_id} {index} '  
                        f'--rpc-url {self.rpc_url}'  
                    )  
                    contract_list[index] = foundry_cli(cmd)  
                except Exception as contract_error:  
                    extra = {  
                        'operation': 'get_single_source_info',  
                        'chain_id': chain_id,    
                        'level_id': index,  
                        'error': str(contract_error),  
                        'status': 'error'  
                    }  
                    self.db_manager.logger.error(f"Failed to retrieve system contract address | {extra}")  
                    return None  

            # Create new source info object  
            new_source_info = SourceChainInfo(  
                chain_id=chain_id,  
                symbol=symbol,  
                name=name,  
                my_contract_num=contract_num,  
                my_contract_list=contract_list,  
                state=state  
            )  

            # Check if source exists  
            source_info: SourceChainInfo = self.source_list.get(chain_id)  
            if source_info is None:  
                self.source_list.update({chain_id: new_source_info})  
                extra = {  
                    'operation': 'get_single_source_info',  
                    'chain_id': chain_id,    
                    'symbol': symbol,  
                    'name': name,    
                }  
                self.db_manager.logger.info(f"New source chain information added | {extra}")  
                return False  

            # Update existing source info  
            changes = source_info.update(new_source_info)  
            self.source_list.update({chain_id: source_info})  

            if changes:  
                extra = {  
                    'operation': 'get_single_source_info',  
                    'chain_id': chain_id,    
                    'changes': changes  
                }  
                self.db_manager.logger.info(f"Source chain information updated | {extra}")  
                return False  

            return True  

        except Exception as e:  
            extra = {  
                'operation': 'get_single_source_info',  
                'chain_id': chain_id,    
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to retrieve source chain information | {extra}")  
            return None       
    
    def update_single_source_info_in_db(self,chain_id:int) -> Optional[bool]:
        retrieval_result = self.get_single_source_info(chain_id)
        if retrieval_result is not False:
            return retrieval_result 
        source_info: SourceChainInfo = self.source_list.get(chain_id)
        task: DBWriteData = {
            'table_name': 'Source_Info',
            'key_columns': {'chain_id': chain_id},
            'data': {
                'symbol': source_info.symbol,
                'name': source_info.name,
                'relay_addr': source_info.my_contract_list[0],  
                'tx_rule_addr': source_info.my_contract_list[1],  
                'transport_addr': source_info.my_contract_list[2]
            }
        } 
        self.create_db_write_task(task)  
        return True 
    
    def get_single_system_contract_info(self, contract_addr: str) -> Optional[Tuple[bool, int]]:  
        """  
        Retrieve and update system contract information from manager contract  

        Args:  
            contract_addr (str): address of system contract  
        
        Returns:  
            Optional[Tuple[bool, int]]:  
            - (True, contract_id): No changes in system contract information  
            - (False, contract_id): System contract information updated  
            - None: Retrieval failed  
        """  
        try:  
            # Get contract info  
            cmd = (  
                f'cast call {self.contract_address} '  
                f'"getSystemContractInfo(address)(uint256,uint256,uint256,uint256)" {contract_addr} '  
                f'--rpc-url {self.rpc_url}'  
            )    
            res = foundry_cli(cmd).split('\n')  
            contract_id = int(res[0])  
            chain_id = int(res[1])  
            level_id = int(res[2])  
            state = int(res[3])  

            if contract_id == 0 and contract_addr != self.contract_address:  
                extra = {  
                    'operation': 'get_single_system_contract_info',  
                    'contract_addr': contract_addr,  
                    'error': 'Invalid contract ID',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Invalid system contract address | {extra}")  
                return None  
 
            new_system_contract_info = SystemContractInfo(  
                contract_address=contract_addr,  
                contract_id=contract_id,  
                chain_id=chain_id,  
                level_id=level_id,  
                state=state  
            )  
  
            contract_info: SystemContractInfo = self.contract_list.get(contract_id)  
            if contract_info is None:  
                self.contract_list.update({contract_id: new_system_contract_info})  
                extra = {  
                    'operation': 'get_single_system_contract_info',  
                    'contract_id': contract_id, 
                    'contract_addr': contract_addr     
                }  
                self.db_manager.logger.info(f"New system contract information added | {extra}")  
                return False, contract_id  

            # Update existing contract info  
            changes = contract_info.update(new_system_contract_info)  
            self.contract_list.update({contract_id: new_system_contract_info})  

            if changes:  
                extra = {  
                    'operation': 'get_single_system_contract_info',  
                    'contract_id': contract_id, 
                    'contract_addr': contract_addr,    
                    'changes': changes   
                }  
                self.db_manager.logger.info(f"System contract information updated | {extra}")  
                return False, contract_id  

            return True, contract_id  

        except Exception as e:  
            extra = {  
                'operation': 'get_single_system_contract_info',  
                'contract_addr': contract_addr,    
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to retrieve system contract information | {extra}")  
            return None
    
    def update_single_system_contract_info_in_db(self,contract_addr: str) -> Optional[bool]:
        retrieval_result = self.get_single_system_contract_info(contract_addr)
        if retrieval_result is None:
            return None
        if_not_change, contract_id = retrieval_result
        if if_not_change:
            return True 
        contract_info: SystemContractInfo = self.contract_list.get(contract_id)
        task: DBWriteData = {
            'table_name': 'System_Contract',
            'key_columns': {'contract_id': contract_id},
            'data':{
                'contract_addr': contract_info.contract_address,  
                'manager_addr': contract_info.manager_address,  
                'state': contract_info.state,  
                'chain_id': contract_info.chain_id,  
                'level_id': contract_info.level_id
            } 
        }
        self.create_db_write_task(task)
        return False          
    
    def process_events(self, events: List[dict]):
        for event in events:
            self.process_single_event(event)
        
        # Update contract information  
        for contract_addr in self.contract_to_update:  
            res = self.update_single_system_contract_info_in_db(contract_addr)  
            if res is None:  
                extra = {  
                    'operation': 'process_events',  
                    'contract_address': contract_addr,  
                    'error': 'Failed to update system contract info',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Contract update failed | {extra}")  
                continue  

        # Update chain information  
        for chain_id in self.chain_to_update:  
            if chain_id == 0:  
                res = self.update_hub_info_in_db()    
            else:  
                res = self.update_single_source_info_in_db(chain_id)    

            if res is None:  
                extra = {  
                    'operation': 'process_events',  
                    'chain_id': chain_id,  
                    'error': 'Failed to update chain info',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Chain update failed | {extra}")  
            continue
    
        self.contract_to_update.clear()
        self.chain_to_update.clear()

    def process_single_event(self, event: dict) -> Optional[bool]:   
        try:   
            if event['topics'][0] == self.event_signatures["UpdateContractInfo"]:  
                return self.process_event_update_contract(event)
            elif event['topics'][0] == self.event_signatures["UpdateChainInfo"]:
                return self.process_event_update_chain(event) 
        except Exception as e:  
            extra = {  
                'operation': 'process_single_event',  
                'event': event,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Failed to process contract event | {extra}")  
            return None   
    
    def process_event_update_contract(self, event: dict) -> bool:    
        contract_addr = self.parse_bytes32_address(event['topics'][1])
        self.contract_to_update = ManagerContractEventListener.add_to_set(self.contract_to_update,contract_addr)
        return True
    
    def process_event_update_chain(self, event: dict) -> bool:
        chain_id = int(event['topics'][1],16)
        self.chain_to_update = ManagerContractEventListener.add_to_set(self.chain_to_update,chain_id)
        return True
    
    def client_prepare(self) -> Optional[bool]:  
        """  
        Prepare client by initializing contract and chain information  

        Returns:  
            Optional[bool]:  
            - True: Client prepared successfully  
            - False: Client needs update  
            - None: Preparation failed  
        """  
        try:   
            res = self.directly_update_manager_contract_info()  
            if res is None:  
                extra = {  
                    'operation': 'client_prepare',  
                    'error': 'Failed to update manager contract info',  
                    'status': 'error'  
                }  
                self.logger.error(f"Client preparation failed | {extra}")  
                return None  
            # Re-start listener for manager contract
            elif res is False:  
                try:  
                    # Get visit block index  
                    block_info = self.db_manager.get_specific_columns_by_key(  
                        table_name='System_Contract',  
                        key_columns={'contract_id': self.contract_id},  
                        columns_to_retrieve=['visit_block_index']  
                    )  
                    if block_info is None:  
                        extra = {  
                            'operation': 'client_prepare',  
                            'error': 'Failed to retrieve visit block index',  
                            'status': 'error'  
                        }  
                        self.logger.error(f"Client preparation failed | {extra}")  
                        return None  
                    self.begin = int(block_info['visit_block_index'])  

                    # Get hub info  
                    hub_info = self.db_manager.get_specific_columns_by_key(  
                        table_name='Hub_Info',  
                        key_columns={'chain_id': self.chain_id},  
                        columns_to_retrieve=['symbol', 'name', 'source_num', 'contract_num']  
                    )  
                    if hub_info is None:  
                        extra = {  
                            'operation': 'client_prepare',  
                            'error': 'Failed to retrieve hub info',  
                            'status': 'error'  
                        }  
                        self.logger.error(f"Client preparation failed | {extra}")  
                        return None  

                    # Update hub attributes  
                    try:  
                        symbol, name, source_num, contract_num = hub_info.values()  
                        self.symbol = str(symbol)  
                        self.name = str(name)  
                        self.source_num = int(source_num)  
                        self.contract_num = int(contract_num)  
                    except (ValueError, KeyError) as e:  
                        extra = {  
                            'operation': 'client_prepare',  
                            'error': f'Invalid hub info format: {str(e)}',  
                            'status': 'error'  
                        }  
                        self.logger.error(f"Client preparation failed | {extra}")  
                        return None  

                    # Load source chain information  
                    for chain_id in range(1, self.source_num + 1):  
                        source_info = self.db_manager.get_specific_columns_by_key(  
                            table_name='Source_Info',  
                            key_columns={'chain_id': chain_id},  
                            columns_to_retrieve=['symbol', 'name', 'state', 'relay_addr', 'tx_rule_addr', 'transport_addr']  
                        )  
                        if source_info is None:  
                            extra = {  
                                'operation': 'client_prepare',  
                                'chain_id': chain_id,  
                                'error': 'Failed to retrieve source chain info',  
                                'status': 'error'  
                            }  
                            self.logger.error(f"Client preparation failed | {extra}")  
                            return None  

                        # Create source chain info object  
                        symbol, name, state, relay_addr, tx_rule_addr, transport_addr = source_info.values()  
                        contract_list = [relay_addr, tx_rule_addr, transport_addr]  
                        my_contract_num = len(list(filter(bool, contract_list)))  
                        
                        self.source_list.update({  
                            chain_id: SourceChainInfo(  
                                chain_id=chain_id,  
                                symbol=symbol,  
                                name=name,  
                                my_contract_num=my_contract_num,  
                                my_contract_list=contract_list,  
                                state=state  
                            )  
                        })  

                    # Load system contract information  
                    for contract_id in range(1, self.contract_num):  
                        contract_info = self.db_manager.get_specific_columns_by_key(  
                            table_name='System_Contract',  
                            key_columns={'contract_id': contract_id},  
                            columns_to_retrieve=['contract_addr', 'manager_addr', 'state', 'chain_id', 'level_id']  
                        )  
                        if contract_info is None:  
                            extra = {  
                                'operation': 'client_prepare',  
                                'contract_id': contract_id,  
                                'error': 'Failed to retrieve system contract info',  
                                'status': 'error'  
                            }  
                            self.logger.error(f"Client preparation failed | {extra}")  
                            return None  

                        # Create system contract info object  
                        contract_addr, manager_addr, state, chain_id, level_id = contract_info.values()  
                        self.contract_list.update({  
                            contract_id: SystemContractInfo(  
                                contract_id=contract_id,  
                                contract_address=contract_addr,  
                                state=state,  
                                chain_id=chain_id,  
                                level_id=level_id,  
                                manager_address=manager_addr  
                            )  
                        })  

                    extra = {  
                        'operation': 'client_prepare',  
                        'chain_id': self.chain_id,  
                        'source_chains': len(self.source_list),  
                        'contracts': len(self.contract_list),  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Client prepared successfully | {extra}")  
                    return True  

                except Exception as e:  
                    extra = {  
                        'operation': 'client_prepare',  
                        'error': str(e),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Failed to prepare client | {extra}")  
                    return None  
            # First start listener for manager contract
            else:  
                self.begin = 0  
                extra = {  
                    'operation': 'client_prepare',  
                    'status': 'success',  
                    'message': 'Fresh start with block 0'  
                }  
                self.logger.info(f"Client prepared for fresh start | {extra}")  
                return True  

        except Exception as e:  
            extra = {  
                'operation': 'client_prepare',  
                'error': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Unexpected error during client preparation | {extra}")  
            return None
    
    def client_start(self) -> Optional[bool]:  
        """  
        Start client processing by handling new blocks and events  

        Returns:  
            Optional[bool]:  
            - True: No new blocks to process  
            - False: Successfully processed new blocks  
            - None: Processing failed  
        """  
        try:  
            # Get latest block number  
            end = self.get_latest_block_number()  
            if end is None:  
                extra = {  
                    'operation': 'client_start',  
                    'error': 'Failed to get latest block number',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Client start failed | {extra}")  
                return None  

            # Validate block range  
            if end < self.begin:  
                extra = {  
                    'operation': 'client_start',  
                    'begin_block': self.begin,  
                    'end_block': end,  
                    'error': 'End block lower than begin block',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Invalid block range | {extra}")  
                return None  

            # Check for new blocks  
            if end == self.begin:  
                extra = {  
                    'operation': 'client_start',  
                    'current_block': end,  
                    'status': 'no_new_blocks'  
                }  
                self.db_manager.logger.info(f"No new blocks to process | {extra}")  
                return True  

            # Limit block range to process  
            if end > self.begin + 100:  
                end = self.begin + 100  

            extra = {  
                'operation': 'client_start',  
                'begin_block': self.begin,  
                'end_block': end,  
                'block_count': end - self.begin,  
                'status': 'processing'  
            }  
            self.db_manager.logger.info(f"Processing new blocks | {extra}")  

            # Listen for events  
            events = self.listen_events(end)  
            if events is None:  
                extra = {  
                    'operation': 'client_start',  
                    'error': 'Failed to listen for events',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Event listening failed | {extra}")  
                return None  

            # Process events  
            self.process_events(events)  

            # Update block pointer  
            self.begin = end
            
            task: DBWriteData = {
                'table_name': 'System_Contract',  
                'key_columns': {'contract_id': self.contract_id},  
                'data':{'visit_block_index': end}
            }
            self.create_db_write_task(task)  

            return False  

        except Exception as e:  
            extra = {  
                'operation': 'client_start',  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Unexpected error during client operation | {extra}")  
            return None
    
    def run(self):
        while not self.task_manager.stop_event.is_set():   
            self.client_start()  
            time.sleep(10)

class RelayContractEventListener(SystemContractEventListener,SourceChainInfo):    
    def __init__(  
        self,      
        rpc_url: str,  
        db_manager: DatabaseManager,
        task_manager: TaskManager,
        contract_address: str,
        multi_address: str,
        chain_id: int,
        contract_id: int,
        symbol: str,
        name: str
    ):    
        SystemContractEventListener.__init__(
            self,
            rpc_url=rpc_url,
            contract_address=contract_address,
            contract_id=contract_id,
            chain_id=chain_id,
            level_id=0,
            multi_address=multi_address,
            db_manager = db_manager,
            task_manager=task_manager
        ) 
        SourceChainInfo.__init__(
            self,
            chain_id=chain_id,
            symbol=symbol,
            name=name
        )
        self.event_signatures = {  
            "UpdateShadowLedger": "0x00f76ab116a28b0fe312c7ff8d51d85886dc7a2a4e739f6911db90a4da110c7c",
            "OpenOldCommit": "0x3d6a8e5ef4d505e0b03ec65b743caffc5a90079d0a6851c06646d0878cfa89e3",
            "SubmitNewCommit":"0xecb32623cdb13b96fe5fe2ba21058d1fd83ed4a7ae572310702d3e2cf9fdca2c"
        }
    
    def directly_update_relay_contract_info(self) -> Optional[bool]:
        """  
        Retrieve and update relay contract information   

        Returns:  
            Optional[bool]:  
            - True: First run listener and inserted relay contract information  
            - False: Updated relay contract information  
            - None: Retrieval failed  
        """
        res = self.get_relay_basic_info()
        if res is None:
            return None 
        genesis_key, gas_bound, commit_time_out, require_stake, un_processed_penalty = res
        return self.db_manager.upsert_generic(
            table_name = 'Relay_Basic_Info',
            key_columns = {'chain_id': self.chain_id},  
            data = {
                'genesis_key': genesis_key,
                'gas_bound': gas_bound,
                'commit_time_out': commit_time_out,  
                'require_stake': require_stake,  
                'un_processed_penalty': un_processed_penalty
            } 
        )
    
    def get_relay_basic_info(self) -> Optional[Tuple[str, str, str, str, str]]:  
        """  
        Retrieve basic information from relay contract  

        Returns:  
            Optional[Tuple[str, str, str, str, str]]:  
            - Tuple containing (genesis_key, gas_bound, commit_timeout, require_stake, unprocessed_penalty)  
            - None if retrieval fails  
        """  
        contract_calls = [  
            ('getGenesisKey()(bytes32)', 'genesis key'),  
            ('getGasLowerBound()(bytes32)', 'gas lower bound'),  
            ('getMaxOpenCommitDelay()(bytes32)', 'max commit delay'),  
            ('getRequireStake()(bytes32)', 'required stake'),  
            ('getPenalty()(bytes32)', 'penalty')  
        ]  

        try:  
            results = []  
            for method, desc in contract_calls:  
                cmd = (  
                    f'cast call {self.contract_address} '  
                    f'"{method}" '  
                    f'--rpc-url {self.rpc_url}'  
                )  
                
                try:  
                    result = foundry_cli(cmd)  
                    results.append(result)    
                    
                except Exception as e:  
                    extra = {  
                        'operation': 'get_relay_basic_info',  
                        'contract_address': self.contract_address,  
                        'method': method,  
                        'error': str(e),  
                        'status': 'error'  
                    }  
                    self.db_manager.logger.error(f"Failed to retrieve {desc} | {extra}")  
                    return None    

            return tuple(results)  

        except Exception as e:  
            extra = {  
                'operation': 'get_relay_basic_info',  
                'contract_address': self.contract_address,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Unexpected error retrieving relay information | {extra}")  
            return None
    
    def update_relay_basic_info(self):
        res = self.get_relay_basic_info()
        if res is None:
            return None 
        genesis_key, gas_bound, commit_time_out, require_stake, un_processed_penalty = res
        task: DBWriteData = {
            'table_name': 'Relay_Basic_Info',
            'key_columns': {'chain_id': self.chain_id},  
            'data': {
                'genesis_key': genesis_key,
                'gas_bound': gas_bound,
                'commit_time_out': commit_time_out,  
                'require_stake': require_stake,  
                'un_processed_penalty': un_processed_penalty
            } 
        }
        self.create_db_write_task(task)
        return True            
    
    def start_process_events(self):
        end = self.get_latest_block_number()
        if end is not None:
            events = self.listen_events(self.begin,end)
            self.process_events(events)
            self.begin = end
    
    def process_events(self, events: List[dict]):
        for event in events:
            self.process_single_event(event)
    
    def process_single_event(self, event: dict):   
        if event['topics'][0] == self.event_signatures["UpdateShadowLedger"]:  
            self.process_event_update_shadow_ledger(event)
        elif event['topics'][0] == self.event_signatures["SubmitNewCommit"]:
            self.process_event_submit_new_commit(event)
        elif event['topics'][0] == self.event_signatures["OpenOldCommit"]:
            self.process_event_open_old_commit(event)  
    
    def process_event_update_shadow_ledger(self, event: dict):     
        '''
        Process event UpdateShadowLedger(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, bytes rawShadowBlock)
        '''
        task: DBWriteData = {
            'table_name': f"Relay_Shadow_Info_{self.chain_id}",
            'key_columns': {
                'key': event['topics'][1],
                'parent_key': event['data'][0]
            },
            'data': {
                'raw_data': event['data'][1]
            } 
        }
        self.create_db_write_task(task)
        return True  
    
    def process_event_submit_new_commit(self, event: dict):
        '''
        Process event SubmitNewCommit(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, address indexed relayer, bytes32 commit);
        '''
        task: DBWriteData = {
            'table_name': f"Relay_Shadow_Info_{self.chain_id}",
            'key_columns': {
                'key': event['topics'][1],
                'parent_key': event['data'][0],
            },
            'data': {
                'commitRelayer': self.parse_bytes32_address(event['topics'][2]),
                'commitValue': event['data'][1],
                'commitTx': event['transactionHash'],
                'commitBlockIndex': int(event['blockNumber'],16)
            }
        }
        self.create_db_write_task(task)
        return True 
    
    def process_event_open_old_commit(self, event: dict):
        '''
        Process event OpenOldCommit(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, address indexed relayer, bool result);
        '''
        task: DBWriteData = {
            'table_name': f"Relay_Shadow_Info_{self.chain_id}",
            'key_columns': {
                'key': event['topics'][1],
                'parent_key': event['data'][0]
            },
            'data': {
                'openRelayer': self.parse_bytes32_address(event['topics'][2]),
                'openResult': bool(int(event['data'][1],16)),
                'openTx': event['transactionHash'],
                'openBlockIndex': int(event['blockNumber'],16)
            } 
        }
        self.create_db_write_task(task)
        return True 
    
    def client_prepare(self):
        res = self.db_manager.get_specific_columns_by_key(  
            table_name='System_Contract',  
            key_columns={'contract_id': self.contract_id},  
            columns_to_retrieve=['visit_block_index']  
        )
        if res is None:
            return None
        self.begin = int(res['visit_block_index'])
        return True
    def client_start(self):
        try:  
            # Get latest block number  
            end = self.get_latest_block_number()  
            if end is None:  
                extra = {  
                    'operation': 'client_start',  
                    'error': 'Failed to get latest block number',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Client start failed | {extra}")  
                return None  

            # Validate block range  
            if end < self.begin:  
                extra = {  
                    'operation': 'client_start',  
                    'begin_block': self.begin,  
                    'end_block': end,  
                    'error': 'End block lower than begin block',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Invalid block range | {extra}")  
                return None  

            # Check for new blocks  
            if end == self.begin:  
                extra = {  
                    'operation': 'client_start',  
                    'current_block': end,  
                    'status': 'no_new_blocks'  
                }  
                self.db_manager.logger.info(f"No new blocks to process | {extra}")  
                return True  

            # Limit block range to process  
            if end > self.begin + 100:  
                end = self.begin + 100  

            extra = {  
                'operation': 'client_start',  
                'begin_block': self.begin,  
                'end_block': end,  
                'block_count': end - self.begin,  
                'status': 'processing'  
            }  
            self.db_manager.logger.info(f"Processing new blocks | {extra}")  

            # Listen for events  
            events = self.listen_events(end)  
            if events is None:  
                extra = {  
                    'operation': 'client_start',  
                    'error': 'Failed to listen for events',  
                    'status': 'error'  
                }  
                self.db_manager.logger.error(f"Event listening failed | {extra}")  
                return None  

            # Process events  
            self.process_events(events)  

            # Update block pointer  
            self.begin = end
            
            task: DBWriteData = {
                'table_name': 'System_Contract',  
                'key_columns': {'contract_id': self.contract_id},  
                'data':{'visit_block_index': end}
            }
            self.create_db_write_task(task)  

            return False  

        except Exception as e:  
            extra = {  
                'operation': 'client_start',  
                'error': str(e),  
                'status': 'error'  
            }  
            self.db_manager.logger.error(f"Unexpected error during client operation | {extra}")  
            return None
    
    def run(self):
        while not self.task_manager.stop_event.is_set():   
            self.client_start()  
            time.sleep(10)
def parse_arguments():  
    """  
    解析命令行参数  
    
    :return: 解析后的参数  
    """  
    parser = argparse.ArgumentParser(description="区块链合约事件监听器")  
    
    # RPC 和合约参数  
    parser.add_argument('--rpc', type=str, required=True, help="RPC服务器地址")  
    parser.add_argument('--contract', type=str, required=True, help="合约地址")   
    
    return parser.parse_args()  

def main():  
    load_dotenv() 
    try:   
        args = parse_arguments()  
        db_manager = DatabaseManager(  
            host=os.getenv('DB_HOST'),  
            port=os.getenv('DB_PORT'),  
            user=os.getenv('DB_USER'),  
            password=os.getenv('DB_PASS'),
            name=os.getenv('DB_NAME'),
            logger=CrosschainZoneLogger.setup_logging(console_output=True)  
        )
        task_manager = TaskManager()  
        manager_listener = ManagerContractEventListener(
            rpc_url=args.rpc,
            db_manager=db_manager,
            task_manager=task_manager,
            contract_address=args.contract,
        )
        task_processor = TaskProcessor(db_manager,task_manager)
        manager_listener.client_prepare()
        manager_listener.start()
        task_processor.start()
        '''
        res = manager_listener.get_latest_event_height()
        if res is None:
            sys.exit(1) 
        manager_listener.start_process_events()
        sourceNum =manager_listener.sourceNum
        relay_listener_list: List[RelayContractEventListener] = []
        for index in range(sourceNum):
            chain_id = index + 1
            relay_listener_list.append(RelayContractEventListener(
                rpc_url=args.rpc,
                db_manager=db_manager,
                chain_id=chain_id,
                manager_address=manager_listener.contract_address,
            ))
            relay_listener = relay_listener_list[index]
            res = relay_listener.get_relay_info_from_manager()
            if res:
                relay_listener.update_relay_basic_info()
                relay_listener.start_process_events()
        '''    
    
    except KeyboardInterrupt:  
        print("程序被手动中断")  
    #except Exception as e:  
        #print(f"主程序发生错误: {e}")  
        #sys.exit(1)  

if __name__ == '__main__':  
    main()  