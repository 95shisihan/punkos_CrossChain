import argparse  
import logging  
import sys  
import time  
from typing import Dict, List, Tuple, Optional, Any  

import mysql.connector  
from mysql.connector import Error  
from foundrycli import foundry_cli  #用于与区块链交互，执行合约调用

# 配置日志  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',  
    handlers=[  
        logging.StreamHandler(sys.stdout),  
        logging.FileHandler('contract_event_listener.log', encoding='utf-8')  
    ]  
)  
logger = logging.getLogger(__name__)  

class DatabaseManager:  
    """数据库管理器"""  
    def __init__(  
        self,   
        host: str,   
        port: int,   
        user: str,   
        password: str,   
        database: str  
    ):  
        """  
        初始化数据库连接  
        
        :param host: 数据库主机  
        :param port: 数据库端口  
        :param user: 用户名  
        :param password: 密码  
        :param database: 数据库名  
        """  
        self.config = {  
            'host': host,  
            'port': port,  
            'user': user,  
            'password': password,  
            'database': database,  
            'charset': 'utf8mb4'  
        }  
        self.connection = None  
        self.cursor = None  

    def _connect(self):  
        """  
        建立数据库连接  
        """  
        try:  
            self.connection = mysql.connector.connect(**self.config)  
            self.cursor = self.connection.cursor(dictionary=True)  
        except Error as e:  
            logger.error(f"数据库连接失败: {e}")  
            raise  

    def _close(self):  
        """  
        关闭数据库连接  
        """  
        if self.cursor:  
            self.cursor.close()  
        if self.connection and self.connection.is_connected():  
            self.connection.close()  
    
    def query_basic_data(  self,     ):   #查询HubInfo表中的基本数据，返回rpc和multiChainAddress
        try:  
            # 如果没有连接，先连接  
            if not self.connection or not self.connection.is_connected():  
                self._connect()  

            sql = """  
            SELECT rpc, multiChainAddress   
            FROM HubInfo   
            WHERE chainID = 0  
            """  
            
            self.cursor.execute(sql)  
            result = self.cursor.fetchone()  
            return result
        except Error as e:  
            logger.error(f"数据库操作失败: {e}")  
            # 回滚事务  
            if self.connection:  
                self.connection.rollback()  
            raise  
        finally:  
            # 确保连接被关闭  
            self._close()  

    def query_visit_block_height_by_address(self,address):  
        #查询SystemContract表中地址对应的visitBlockHeight字段
        """  
        根据地址查询visitBlockHeight  
        
        参数:  
        - address: 要查询的地址  
        
        返回:  
        - visitBlockHeight（整数）  
        - 如果未找到记录，返回None  
        """  
        if not self.connection or not self.connection.is_connected():  
            self._connect() 
        try:  
            cursor = self.connection.cursor(dictionary=True) 
            # 构建查询语句  
            query = """  
            SELECT visitBlockHeight   
            FROM SystemContract   
            WHERE address = %s  
            """  
            
            # 执行查询  
            cursor.execute(query, (address,))  
            
            # 获取结果  
            result = cursor.fetchone()  
            # 返回visitBlockHeight，未找到返回None  
            return result['visitBlockHeight'] if result else None  
        
        except Exception as e:  
            print(f"查询地址区块高度时发生错误: {e}")  
            raise 

    def update_visit_block_height_by_address(self,address,height):  
        #更新SystemContract表中地址对应的visitBlockHeight字段
        """  
        根据地址查询visitBlockHeight  
        
        参数:  
        - address: 要查询的地址  
        
        返回:  
        - visitBlockHeight（整数）  
        - 如果未找到记录，返回None  
        """  
        if not self.connection or not self.connection.is_connected():  
            self._connect() 
        try:  
            update_query = """  
            UPDATE SystemContract   
            SET visitBlockHeight = %s   
            WHERE address = %s  
            """  
                
            # 执行更新  
            self.cursor.execute(  
                update_query,   
                (height, address)  
            )
            self.connection.commit()  
        
        except Exception as e:  
            print(f"查询地址区块高度时发生错误: {e}")  
            raise 

    
    def upsert_relay_data(self, data: Dict[str, Any], contractAddress:str, eventHeight:int) -> Optional[int]:  
        #检查数据是否存在，存在则更新，不存在则插入。
        # 涉及字段：key,commitTx,commitBlockIndex,commitRelayer,commitValue,
        # openTx,openBlockIndex,openRelayer,openResult,rawData
        #并与此同时更新SystemContract表中的visitBlockHeight字段
        """  
        基于 key 实现 Upsert 操作，支持部分字段更新，不进行类型转换  
        
        :param connection: 数据库连接  
        :param data: 待插入/更新的数据  
        :return: 记录的 no（新插入或更新的记录号）  
        """  
        
        if 'key' not in data:  
            raise ValueError("数据必须包含 'key' 字段")  
        if not self.connection or not self.connection.is_connected():  
            self._connect() 
        try:  
            cursor = self.connection.cursor(dictionary=True)  
            
            # 先检查是否存在  
            check_sql = "SELECT no FROM RelayData WHERE `key` = %(key)s"  
            cursor.execute(check_sql, {'key': data['key']})  
            existing_record = cursor.fetchone()  
            
            if existing_record:  
                # 动态构建更新 SQL  
                update_fields = []  
                update_params = {'key': data['key']}  
                
                # 除 key 外的所有字段  
                optional_fields = [  
                    'commitTx', 'commitBlockIndex', 'commitRelayer',   
                    'commitValue', 'openTx', 'openBlockIndex',   
                    'openRelayer', 'openResult', 'rawData'  
                ]  
                
                for field in optional_fields:  
                    if field in data:  
                        update_fields.append(f"`{field}` = %({field})s")  
                        update_params[field] = data[field]  
                
                if not update_fields:  
                    # 没有要更新的字段  
                    return existing_record['no']  
                
                # 构建完整的更新 SQL  
                update_sql = f"""  
                UPDATE RelayData   
                SET {', '.join(update_fields)}  
                WHERE `key` = %(key)s  
                """  
                
                cursor.execute(update_sql, update_params)  
                update_query = """  
                UPDATE SystemContract   
                SET visitBlockHeight = %s   
                WHERE address = %s  
                """  
                
                # 执行更新  
                cursor.execute(  
                    update_query,   
                    (eventHeight, contractAddress)  
                )
                self.connection.commit()  
                logger.info(f"成功更新/插入影子区块: {data['key']} (BlockNo: {existing_record['no']})")
                return existing_record['no']  
            else:  
                # 插入新记录  
                # 确保所有字段都存在  
                full_fields = [  
                    'key', 'commitTx', 'commitBlockIndex', 'commitRelayer',   
                    'commitValue', 'openTx', 'openBlockIndex',   
                    'openRelayer', 'openResult', 'rawData'  
                ]  
                
                # 准备插入的字段和值  
                insert_fields = []  
                insert_values = []  
                insert_params = {}  
                
                for field in full_fields:  
                    if field in data:  
                        insert_fields.append(f"`{field}`")  
                        insert_values.append(f"%({field})s")  
                        insert_params[field] = data[field]  
                    elif field != 'key':  
                        # 对于非 key 的其他字段，如果未传入，使用 NULL  
                        insert_fields.append(f"`{field}`")  
                        insert_values.append("NULL")  
                
                # 构建插入 SQL  
                insert_sql = f"""  
                INSERT INTO RelayData   
                ({', '.join(insert_fields)})   
                VALUES   
                ({', '.join(insert_values)})  
                """  
                
                cursor.execute(insert_sql, insert_params) 
                update_query = """  
                UPDATE SystemContract   
                SET visitBlockHeight = %s   
                WHERE address = %s  
                """  
                
                # 执行更新  
                cursor.execute(  
                    update_query,   
                    (eventHeight, contractAddress)  
                ) 
                self.connection.commit()  
                logger.info(f"成功更新/插入影子区块: {data['key']} (BlockNo: {cursor.lastrowid})")
                return cursor.lastrowid  
        
        except mysql.connector.Error as error:  
            print(f"Upsert 操作错误: {error}")  
            self.connection.rollback()  
            return None  
        finally:  
            if cursor:  
                cursor.close()

class ContractEventListener:  
    """区块链合约事件监听器"""  
    def __init__(  
        self,   
        chain_symbol: str,  
        db_manager: DatabaseManager  
    ):  
        """  
        初始化事件监听器  
        
        :param rpc_url: RPC服务器地址  
        :param contract_address: 合约地址  
        :param db_manager: 数据库管理器  
        """  
        self.rpc_url = ''  
        self.multi_address = ''
        self.chain_symbol = chain_symbol  
        self.db_manager = db_manager  
        self.chain_id = 0
        self.relay_address = ''
        # 事件签名  
        self.event_signatures = {  
            "UpdateShadowLedger": "0x00f76ab116a28b0fe312c7ff8d51d85886dc7a2a4e739f6911db90a4da110c7c",
            "OpenOldCommit": "0x3d6a8e5ef4d505e0b03ec65b743caffc5a90079d0a6851c06646d0878cfa89e3",
            "SubmitNewCommit":"0xecb32623cdb13b96fe5fe2ba21058d1fd83ed4a7ae572310702d3e2cf9fdca2c"
        }  
    def load_hub_info(self):   
        #从数据库中加载中继链信息，RPC地址和多链合约地址
        try:  
            res = self.db_manager.query_basic_data()
            self.rpc_url = res['rpc']
            self.multi_address = res['multiChainAddress']
        except Exception as e:  
            logger.error(f"导入中继链信息失败:  - {e}")  
            return None
    def load_source_info(self):
        #根据chain_symbol，从中继链获取源链ID和系统合约地址
        try:  
            cmd = (  
                f'cast call {self.multi_address} '  
                f'"getSourceChainIDBySymbol(string)(uint)" {self.chain_symbol} '  
                f'--rpc-url {self.rpc_url} -- --json'  
            )  
            self.chain_id = int(foundry_cli(cmd))
            
            level_id = int(0)
            cmd = (  
                f'cast call {self.multi_address} '  
                f'"getSystemContractAddressByLevelID(uint,uint)(address)" {self.chain_id} {level_id} '  
                f'--rpc-url {self.rpc_url} -- --json'  
            ) 
            self.relay_address = foundry_cli(cmd)
            
        except Exception as e:  
            logger.error(f"获取源链中继信息失败:  - {e}")  
            return None
    def parse_bytes32_address(self, bytes32_addr: str) -> Optional[str]:  
        """  
        解析 bytes32 地址  
        
        :param bytes32_addr: bytes32 格式地址  
        :return: 解析后的地址  
        """  
        try:  
            return foundry_cli(f'cast parse-bytes32-address {bytes32_addr}')  
        except Exception as e:  
            logger.error(f"解析 bytes32 地址失败: {bytes32_addr} - {e}")  
            return None  

    def listen_events(self, start:int, end:int) -> List[dict]:  
        #通过foundry-cli监听合约事件
        """  
        监听合约事件  
        
        :return: 事件列表  
        """  
        try:  
            cmd = (  
                f'cast logs --address {self.relay_address} '  
                f'--rpc-url {self.rpc_url} '  
                f'--from-block {start} '  
                f'--to-block {end} --json'  
            )  
            return foundry_cli(cmd)  
        except Exception as e:  
            logger.error(f"获取合约事件失败: {e}")  
            return []  


    def process_multi(self):  
        """  
        处理合约事件  
         
        """ 
        addr = self.contract_address
        contract_id = 0
        chain_id = 0
        level_id = 0
        state = 2
        manager = self.get_multi_manager_info()
        self.db_manager.upsert_system_contract(  
            contract_id=contract_id,  
            chain_id=chain_id,  
            level_id=level_id,  
            state=state,  
            address=addr,
            manager=manager,
            eventBlockHeight=0,
            option=False
        ) 

    def process_events(self, events: List[dict]):  
        #根据事件的topics处理不同类型的事件
        """  
        处理合约事件  
        
        :param events: 事件列表  
        """  
        for event in events:  
            try:  
                # 检查是否为 UpdateContractInfo 事件 
                #print(event)
                if event['topics'][0] == self.event_signatures["UpdateShadowLedger"]:  
                    # 解析 bytes32 地址  
                    keyShadowBlock = event['topics'][1]
                    rawData = event['data']
                    
                    # 插入或更新数据库  
                    self.db_manager.upsert_relay_data(
                        {
                        'key':keyShadowBlock,
                        'rawData':rawData
                        },
                        contractAddress=self.relay_address,
                        eventHeight=int(event['blockNumber'],16)
                    )  
                    
                    time.sleep(0.1) 
                      
                elif event['topics'][0] == self.event_signatures["OpenOldCommit"]:
                    keyShadowBlock = event['topics'][1]
                    openRelayer = self.parse_bytes32_address(event['topics'][2])
                    openResult = bool(int(event['topics'][3],16))
                    openTx = event['transactionHash']
                    openBlockIndex = int(event['blockNumber'],16)

                    self.db_manager.upsert_relay_data(
                        {
                        'key':keyShadowBlock,
                        'openRelayer':openRelayer,
                        'openResult':openResult,
                        'openTx':openTx,
                        'openBlockIndex':openBlockIndex
                        },
                        contractAddress=self.relay_address,
                        eventHeight=openBlockIndex
                    ) 
                    time.sleep(0.1)
                elif event['topics'][0] == self.event_signatures["SubmitNewCommit"]:
                    keyShadowBlock = event['topics'][1]
                    commitRelayer = self.parse_bytes32_address(event['topics'][3])
                    commitValue = event['data']
                    commitTx = event['transactionHash']
                    commitBlockIndex = int(event['blockNumber'],16)
                    self.db_manager.upsert_relay_data(
                        {
                        'key':keyShadowBlock,
                        'commitRelayer':commitRelayer,
                        'commitValue':commitValue,
                        'commitTx':commitTx,
                        'commitBlockIndex':commitBlockIndex
                        },
                        contractAddress=self.relay_address,
                        eventHeight=commitBlockIndex
                    ) 
                    time.sleep(0.1)
            except Exception as e:  
                logger.error(f"处理事件时发生错误: {e}")  
 

def main():  
    try:  
        # 创建数据库管理器  
        db_manager = DatabaseManager(  
            host='111.119.239.159',  
            port=36036,  
            user='root',  
            password='szl@buaa#1234',  
            database='CrossZone' 
        )  
        
        # 创建事件监听器  
        listener = ContractEventListener(  
            chain_symbol='SSC',  
            db_manager=db_manager  
        ) 
        listener.load_hub_info()
        listener.load_source_info()
        #print(listener.relay_address)
        # 获取事件  
        start =int(listener.db_manager.query_visit_block_height_by_address(listener.relay_address))
        end = start + 20
        events = listener.listen_events(start=start,end=end)  
        
        # 处理事件  
        listener.process_events(events)
        listener.db_manager.update_visit_block_height_by_address(listener.relay_address,end)

    
    except KeyboardInterrupt:  
        logger.info("程序被手动中断")  
    except Exception as e:  
        logger.error(f"主程序发生错误: {e}")  
        sys.exit(1)  

if __name__ == '__main__':  
    main()  