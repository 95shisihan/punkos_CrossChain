import requests  
import mysql.connector  
from mysql.connector import Error   
import json  
from typing import Dict, Any, Optional, Tuple  
import time  
import sys   
import os  
from datetime import datetime  
from dotenv import load_dotenv
  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger 

class BTCBlockHeaderManager:  
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

    def getTopBlockHeight_API(self, max_retries: int = 3) -> int:  
        """  
        Retrieve the latest block height with retry mechanism  
        
        :param max_retries: Maximum number of retry attempts  
        :return: Latest block height  
        """   
        for attempt in range(max_retries):  
            try:  
                url = "https://api.blockchair.com/bitcoin/stats"  
                self.logger.info(  
                    "Initiating block height retrieval",   
                    extra={  
                        'url': url,  
                        'attempt': attempt + 1  
                    }  
                )   
                response = requests.get(url, timeout=10)  
                response.raise_for_status()  
                result = response.json()['data']  
                block_height = result['best_block_height']  
                self.logger.info(  
                    "Block height retrieved successfully",  
                    extra={  
                        'block_height': block_height,  
                        'attempt': attempt + 1  
                    }  
                )   
                return block_height  
            except requests.exceptions.RequestException as e:  
                error_log = {  
                    "event": "block_height_retrieval_failure",  
                    "timestamp": datetime.now().isoformat(),  
                    "attempt": {  
                        "current": attempt + 1,  
                        "max": max_retries  
                    },  
                    "error": {  
                        "type": type(e).__name__,  
                        "message": str(e),  
                        "url": url  
                    }  
                }  
                
                self.logger.warning(  
                    "Block height API request failed",  
                    extra={'error_details': json.dumps(error_log)}  
                )  
                
                # Exponential backoff  
                if attempt < max_retries - 1:  
                    wait_time = 2 ** attempt  
                    self.logger.info(  
                        f"Waiting {wait_time} seconds before retry",  
                        extra={  
                            'wait_time': wait_time,  
                            'attempt': attempt + 1  
                        }  
                    )  
                    time.sleep(wait_time)  
        
        # Final failure handling  
        final_error = {  
            "event": "block_height_retrieval_ultimate_failure",  
            "timestamp": datetime.now().isoformat(),  
            "error": "Failed to retrieve block height after maximum retries"  
        }  
        
        self.logger.error(  
            "Exhausted all retry attempts for block height retrieval",  
            extra={'error_details': json.dumps(final_error)}  
        )  
        
        raise Exception("Unable to retrieve block height after multiple attempts")   

    def getGenesisHeight_API(self) -> int:  
        """  
        Calculate the most recent difficulty adjustment block height  

        :return: Difficulty adjustment block height  
        """  
        try:  
            top_height = self.getTopBlockHeight_API()  
            genesis_height = top_height - top_height % 2016  
            return genesis_height  
        except Exception as e:  
            self.logger.error(f"Failed to calculate genesis block height: {e}")  
            raise  
    
    def getBlockHeader_API(self, height: int) -> Dict[str, str]:
        url = f"https://api.blockchair.com/bitcoin/raw/block/{height}"  
            
        response = requests.get(  
            url,   
            timeout=10,  
            headers={  
                'User-Agent': 'CrosschainZone/1.0',  
                'Accept': 'application/json'  
            }  
        )  
            
        # Check API response  
        response.raise_for_status()  
        result = response.json()['data']  
            
        # Extract block information  
        if height == 0:  
            block_hash = result[0]['decoded_raw_block']['hash']  
            raw_block = result[0]['raw_block'][0:160]  
        else:  
            block_hash = result[str(height)]['decoded_raw_block']['hash']  
            raw_block = result[str(height)]['raw_block'][0:160]
        return block_hash, raw_block
    def get_block_header(self, height: int) -> Optional[Dict[str, Any]]:  
        """  
        Retrieve block header information, prioritize local database query,   
        fetch and store from API if not exists  
        
        :param height: Block height  
        :return: Block header information dictionary, return None if retrieval fails  
        """  
        connection = None  
        cursor = None  
        
        try:  
            # 1. First check if data exists in local database  
            connection = self._get_connection()  
            cursor = connection.cursor(dictionary=True)  
            self.logger.info(f"Tried to retrieve block {height} header from local database")
            # Query data for specified height  
            query = "SELECT * FROM BTCRawData WHERE height = %s"  

            try:
                # 尝试执行查询
                cursor.execute(query, (height,))  
                local_data = cursor.fetchone()
                
                if local_data:  
                    self.logger.info(f"Successfully retrieved block {height} header from local database") 
                    return local_data  
                    
            except mysql.connector.Error as err:
                # 专门捕获表不存在的错误 (错误码 1146)
                if err.errno == 1146:
                    error_msg = "CRITICAL ERROR: Table 'BTCRawData' does not exist in database! Please create it manually."
                    self.logger.error(error_msg)
                    # 直接抛出异常，不再继续执行 API 请求
                    raise Exception(error_msg)
                else:
                    # 其他数据库错误，可能也需要中断
                    raise err
            # 2. If not in local database, fetch via API  
            self.logger.info(f"Failed to retrieve block {height} header from local database")
            self.logger.info(f"Tried to retrieve block {height} header from API or RPC")
            block_hash, raw_block = self.getBlockHeader_API(height)  
            
            # Prepare insert data  
            insert_data = {  
                'hash': block_hash,   
                'height': height,  
                'rawData': raw_block  
            }  
            self.logger.info(f"Successfully retrieved block {height} header from API or RPC")
            # Insert into database  
            insert_query = """  
            INSERT INTO BTCRawData   
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
    load_dotenv()   
    btc_manager = BTCBlockHeaderManager(  
        database_name=os.getenv('DB_NAME'),  
        host=os.getenv('DB_HOST'),  
        port=int(os.getenv('DB_PORT')),  
        user=os.getenv('DB_USER'),  
        password=os.getenv('DB_PASS'),
        logger=CrosschainZoneLogger.setup_logging()  
    )   
    try:  
        height = int(sys.argv[1])  
        if (height == -1):  
            height = btc_manager.getGenesisHeight_API()  
            block_data = btc_manager.get_block_header(height)  
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
            block_data = btc_manager.get_block_header(height)  
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