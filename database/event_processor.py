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
from basic_listener import MultiContractListener


class EventProcessor(MultiContractListener):
    def __init__(self,
        rpc_url: str,
        multi_address: str,
        db_manager: DatabaseManager
    ):
        MultiContractListener.__init__(
            self,
            rpc_url=rpc_url,
            contract_address= '', 
            multi_address = multi_address
        )
        self.db_manager = db_manager
        self.running = True 
        signal.signal(signal.SIGINT, self.signal_handler)  
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):    
        print(f"\nReceived signal {signum}")  
        self.running = False 
    def client(self):
        print("Start event processor")
        self.running = True
        while self.running:
            
            if not self.client_circle():
                return None
            time.sleep(5)
            
        print("Shutting down manager contract listener...")
        sys.exit(0)
    def search_event_name(self, event_sig: str) -> str:
        for key, val in self.event_signatures.items():
            if val == event_sig:
                return key
        else:
            return "Unknown"
    def client_circle(self) -> bool:
        db_result = self.db_manager.get_all_records_by_conditions(
            table_name='event_info',
            conditions={'if_process': False},
            columns_to_retrieve=['no','contract_addr','event_sig','event_topic','event_data','tx_hash','event_index']
        )
        if db_result is None:
            return False
        for item in db_result:
            event_name = self.search_event_name(item['event_sig'])
            if event_name == 'UpdateShadowLedger':
                self.process_event_update_shadow_ledger(item)
            elif event_name == 'SubmitNewCommit':
                self.process_event_submit_new_commit(item)
            elif event_name == 'OpenOldCommit':
                self.process_event_open_old_commit(item)
    def process_event_submit_new_commit(self,event_item) -> bool:
        topics = MultiContractListener.str_list(event_item['event_topic'])
        prev_key = event_item['event_data'][0:66]
        commit_value = '0x' + event_item['event_data'][66:]
        result, relayer_addr = self.parse_bytes32_address(topics[1])
        if not result:
            return False
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='system_contract_info',
            key_columns={'contract_addr': event_item['contract_addr']},
            columns_to_retrieve=['chain_id']
        )
        if not db_result:
            return False
        chain_id = db_result['chain_id']
        db_result = self.db_manager.upsert_generic(
            table_name = f"source_shadow_info_{chain_id}",
            key_columns = {
                'shadow_key': topics[0],
                'prev_key': prev_key
            },
            data = {
                'commit_relayer_addr': relayer_addr,
                'commit_value': commit_value,
                'commit_event_no': event_item['no'],
            } 
        )
        print(db_result)
        return True
    
    def process_event_open_old_commit(self,event_item) -> bool:
        topics = MultiContractListener.str_list(event_item['event_topic'])
        prev_key = event_item['event_data'][0:66]
        open_result = bool(int('0x' + event_item['event_data'][66:],16))
        result, relayer_addr = self.parse_bytes32_address(topics[1])
        if not result:
            return False
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='system_contract_info',
            key_columns={'contract_addr': event_item['contract_addr']},
            columns_to_retrieve=['chain_id']
        )
        if not db_result:
            return False
        chain_id = db_result['chain_id']
        db_result = self.db_manager.upsert_generic(
            table_name = f"source_shadow_info_{chain_id}",
            key_columns = {
                'shadow_key': topics[0],
                'prev_key': prev_key
            },
            data = {
                'open_relayer_addr': relayer_addr,
                'open_result': open_result,
                'open_event_no': event_item['no'],
            } 
        )
        print(db_result)
        return True 

    def process_event_update_shadow_ledger(self,event_item) -> bool:
        topics = MultiContractListener.str_list(event_item['event_topic'])
        prev_key = event_item['event_data'][0:66]
        raw_data = '0x' + event_item['event_data'][66:]
        db_result = self.db_manager.get_specific_columns_by_key(
            table_name='system_contract_info',
            key_columns={'contract_addr': event_item['contract_addr']},
            columns_to_retrieve=['chain_id']
        )
        if not db_result:
            return False
        chain_id = db_result['chain_id']
        db_result = self.db_manager.upsert_generic(
            table_name = f"source_shadow_info_{chain_id}",
            key_columns = {
                'shadow_key': topics[0],
                'prev_key': prev_key
            },
            data = {
                'raw_data': raw_data
            } 
        )
        print(db_result)
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
         
        event_processor = EventProcessor(
            rpc_url=db_result['rpc'],
            db_manager=db_manager,
            multi_address=db_result['multi_addr'],
        )
        print(event_processor.client_circle())    
    except Exception as e:  
        print(f"主程序发生错误: {e}")  
        sys.exit(1)  

if __name__ == '__main__':  
    main()  