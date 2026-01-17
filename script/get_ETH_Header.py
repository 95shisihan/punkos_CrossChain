import requests  
import mysql.connector  
from mysql.connector import Error  
import logging  
import json  
from typing import Dict, Any, Optional, Tuple  
import time  
import sys 
from eth_utils import decode_hex, encode_hex
import rlp
import os
from web3 import Web3
from datetime import datetime  
from dotenv import load_dotenv
  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger

# BeaconCha.in API 基础 URL
BEACONCHA_URL = "https://beaconcha.in/api/v1"
# 您的 BeaconCha.in API Key
BEACONCHA_API_KEY = "T2NPQkJGWkVSS0VmaXdYaWpEakRJZUVmOUtUNg"

class ETHBlockHeaderManager:  
    def __init__(  
        self,   
        database_name: str,   
        host: str,   
        port: int,   
        user: str,   
        password: str,
        logger: CrosschainZoneLogger  
    ):    
        self.db_config = {  
            'host': host,  
            'port': port,  
            'user': user,  
            'password': password,  
            'database': database_name  
        }    
        self.logger = logger   

    def _get_connection(self):  
        """  
        Get database connection  
        
        :return: Database connection  
        """  
        try:  
            connection = mysql.connector.connect(**self.db_config)  
            return connection  
        except Error as e:  
            self.logger.error(f"Database connection failed: {e}")  
            raise 
    
    def getGenesisHeight_API(self) -> int:  
        """  
        计算最近的难度调整区块高度  

        :return: 难度调整区块高度  
        """  
        try:   
            genesisHeight = 10805880  
            return genesisHeight  
        except Exception as e:  
            self.logger.error(f"Failed to retrieve block height : {e}")  
            raise  
    
    def get_beacon_header_API(self, slot_number) -> tuple:
        """Retrieve Latest Beacon Header From BeaconCha.in"""
        url = f"{BEACONCHA_URL}/slot/{slot_number}"
        
        headers = {'apikey': BEACONCHA_API_KEY}
        
        response = requests.get(url, headers=headers)
        print("返回值是",response)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve Beacon Header, status code: {response.status_code}, response: {response.text}")
        data = response.json()
        header = data['data']
        beaconParams = {
            "slot": header['slot'],
            "proposerIndex": header['proposer'],
            "parentRoot": header['parentroot'],
            "stateRoot": header['stateroot'],
            "bodyRoot": header['blockroot']
        }
        executionParams = {
            "parentHash":header['exec_parent_hash'], 
            "feeRecipient": header['exec_fee_recipient'],
            "stateRoot": header['exec_state_root'],
            "receiptsRoot": header['exec_receipts_root'],
            "logsBloom": header['exec_logs_bloom'],
            "prevRandao": header['exec_random'],
            "blockNumber": header['exec_block_number'],
            "gasLimit": header['exec_gas_limit'],
            "gasUsed": header['exec_gas_used'],
            "timestamp": header['exec_timestamp'],
            "extraData": header['exec_extra_data'],
            "baseFeePerGas": header['exec_base_fee_per_gas'],
            "blockHash": header['exec_block_hash'],
            "transactionsRoot": None,
            "withdrawalsRoot": header['eth1data_depositroot'],
        }
        encoded_beacon = self.encode_beacon_params(beaconParams)
        encoded_exec = self.encode_exec_header(executionParams)
        encoded_header = rlp.encode([encoded_beacon, encoded_exec]).hex()
        hash = header['exec_block_hash']
        return hash, encoded_header 
    def encode_exec_header(self, execParams):
        try:
            return [
                decode_hex(execParams['parentHash']),
                decode_hex(execParams['withdrawalsRoot']),
                Web3.to_bytes(hexstr=execParams['feeRecipient']),
                decode_hex(execParams['stateRoot']),
                decode_hex(execParams['receiptsRoot']),
                decode_hex(execParams['logsBloom']),
                decode_hex(execParams['prevRandao']),
                int(execParams['blockNumber']),
                int(execParams['gasLimit']),
                int(execParams['gasUsed']), 
                int(execParams['timestamp']),
                bytes.fromhex(execParams['extraData'].replace('0x', '')),
                decode_hex('0x' + hex(int(execParams['baseFeePerGas']))[2:].zfill(64)),  # 正确处理整数类型
                decode_hex(execParams['blockHash'])
            ]
        except Exception as e:
            raise
    def encode_beacon_params(self, beaconParams):
        return [
            int(beaconParams['slot']),
            int(beaconParams['proposerIndex']),
            decode_hex(beaconParams['parentRoot']),
            decode_hex(beaconParams['stateRoot']),
            decode_hex(beaconParams['bodyRoot'])
        ]
    #query = "SELECT * FROM ETHRawData WHERE height = %s"
    #(raw_block, block_hash) = get_beacon_header(height)
    def get_block_header(self, height: int) -> Optional[Dict[str, Any]]:  
        connection = None  
        cursor = None  
        try:  
            # 1. First check if data exists in local database  
            connection = self._get_connection()  
            cursor = connection.cursor(dictionary=True)  
            self.logger.info(f"Tried to retrieve block {height} header from local database")
            # Query data for specified height  
            query = "SELECT * FROM ETHRawData WHERE height = %s"  
            cursor.execute(query, (height,))  
            local_data = cursor.fetchone()  
            # If data exists locally, return directly  
            if local_data:  
                self.logger.info(f"Successfully retrieved block {height} header from local database") 
                return local_data  
            # 2. If not in local database, fetch via API  
            self.logger.info(f"Failed to retrieve block {height} header from local database")
            self.logger.info(f"Tried to retrieve block {height} header from API or RPC")
            block_hash, raw_block = self.get_beacon_header_API(height)  
            
            # Prepare insert data  
            insert_data = {  
                'hash': block_hash,   
                'height': height,  
                'rawData': raw_block  
            }  
            self.logger.info(f"Successfully retrieved block {height} header from API or RPC")
             
            insert_query = """  
            INSERT INTO ETHRawData   
            (`hash`, `height`, `rawData`)   
            VALUES (%(hash)s, %(height)s, %(rawData)s)  
            """  
            try:
                cursor.execute(insert_query, insert_data)  
                connection.commit()
                self.logger.info(f"Successfully stored block {height} header in local database")
            except Exception as e:
                self.logger.warning(f"Failed to store block {height} header in local database: {e}")
            
            # Return inserted data  
            return insert_data  
        
        except Exception as e:  
            self.logger.error(f"Failed to retrieve block {height} header: {e}")  
            return None   
        
        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  

def main():  
    # 初始化数据管理器  
    load_dotenv()   
    print("完蛋啦")
    eth_manager = ETHBlockHeaderManager(  
        database_name=os.getenv('DB_NAME'),  
        host=os.getenv('DB_HOST'),  
        port=int(os.getenv('DB_PORT')),  
        user=os.getenv('DB_USER'),  
        password=os.getenv('DB_PASS'),
        logger=CrosschainZoneLogger.setup_logging()  
    )
    print("完蛋啦")
    try:
        height = int(sys.argv[1])
        print("完蛋啦")
        if (height == -1):
            height = eth_manager.getGenesisHeight_API()  
            block_data = eth_manager.get_block_header(height)
            if block_data:  
                return json.dumps({  
                    "status": True,  
                    "hash": block_data['hash'],  
                    "raw": block_data['rawData'],  
                    "height": height   
                })  
            else:  
                return json.dumps({  
                    "status": False,  
                    "message": "Unable to retrieve block data"  
                })  
        else:
            block_data = eth_manager.get_block_header(height)
            if block_data:  
                return json.dumps({  
                    "status": True,  
                    "hash": block_data['hash'],  
                    "raw": block_data['rawData'],  
                    "height": height   
                })  
            else:  
                return json.dumps({  
                    "status": False,  
                    "message": "Unable to retrieve block data"  
                })
    except Exception as e:  
        return json.dumps({  
            "status": False,  
            "message": str(e)  
        })  

if __name__ == '__main__':  
    result = main()
    print(result)