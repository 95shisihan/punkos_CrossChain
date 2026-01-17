import os
import sys 
import json
from dotenv import load_dotenv
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from typing import List, Tuple, Optional, Dict, Any, Union
import mysql.connector  
from basic_db import BasicDatabaseManager

def main():
    load_dotenv() 

    # 创建数据库管理器  
    db_manager = BasicDatabaseManager(  
        host=os.getenv('DB_HOST'),  
        port=os.getenv('DB_PORT'),  
        user=os.getenv('DB_USER'),  
        password=os.getenv('DB_PASS'),
        database_name=os.getenv('DB_NAME'),
        logger=CrosschainZoneLogger.setup_logging(console_output=True),
    )
    
    db_result = db_manager.upsert_generic(
        table_name='crosschainzone_info',
        key_columns={'no': 0},
        data={
            'zone_type': 0,
            'rpc': 'http://127.0.0.1:8545',
            'multi_addr': '0x5FbDB2315678afecb367f032d93F642f64180aa3',
            'visit_block_height': 0
        }
    )
    '''
    db_result = db_manager.get_all_records_by_conditions(
        table_name=f'source_shadow_info_{2}',
        conditions={'open_result':True},
        columns_to_retrieve=['no']
    )
    print(db_result)
    db_result = db_manager.get_specific_columns_by_key(
        table_name=f'source_shadow_info_{2}',
        key_columns={'no':2},
        columns_to_retrieve=['shadow_key']
    )
    '''
    print(db_result)

if __name__ == '__main__':  
    main()