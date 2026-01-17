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
class CrosschainZoneDatabaseManager(BasicDatabaseManager):  
    def __init__(self,  
        host: str,  
        port: str,  
        user: str,  
        password: str,  
        database_name: str,
        logger: CrosschainZoneLogger,
        table_schema_path: str = 'database/table_schema.json'  
    ):  
        BasicDatabaseManager.__init__(
            self,
            host=host,
            port=port,
            user=user,
            password=password,
            database_name=database_name,
            logger=logger
        )
        self.table_schema_path = table_schema_path
        self.table_schemas = self._load_table_schemas()   
    
    def _load_table_schemas(self) -> Optional[dict]:  
        """  
        Load all table schemas from configuration file during initialization  

        Returns:  
            Optional[dict]: Dictionary containing all table schemas if successful, None if failed  
        """  
        try:  
            with open(self.table_schema_path, 'r') as schema_file:  
                schemas = json.load(schema_file)  
                return schemas  
        except (json.JSONDecodeError, FileNotFoundError) as e:  
            extra = {  
                'operation': '_load_table_schemas',  
                'params': {'file_path': self.table_schema_path},  
                'error_type': type(e).__name__,  
                'message': str(e),    
            }  
            self.logger.error(f"Operation failed | {extra}")  
            return None
    
    def get_table_schema(self, table_name: str, table_type: str = 'single_tables') -> Optional[str]:  
        """  
        Get table schema from loaded schemas  
        
        Args:  
            table_name: Name of the table to get schema for  
            table_type: Type of the table ('single_tables' or 'template_tables')  
            
        Returns:  
            Optional[str]: Table creation SQL string if exists, None if not found  
        """  
        if not self.table_schemas:  
            extra = {  
                'operation': 'get_table_schema',  
                'params': {'table_name': table_name, 'table_type': table_type},  
                'error_type': 'SchemaNotLoaded',  
                'message': 'No schemas loaded'  
            }  
            self.logger.error(f"Operation failed | {extra}")  
            return None  

        schemas = self.table_schemas.get(table_type, {})  
        if table_type == 'template_tables':    
            base_name = '_'.join(table_name.split('_')[:-1])  
        else:  
            base_name = table_name   
        
        if base_name not in schemas:  
            extra = {  
                'operation': 'get_table_schema',  
                'params': {'table_name': table_name, 'table_type': table_type},  
                'error_type': 'SchemaNotFound',  
                'message': f'Schema not found for table'  
            }  
            self.logger.error(f"Operation failed | {extra}")  
            return None  

        schema = schemas[base_name]  
        if table_type == 'template_tables':  
            schema = schema.format(table_name=table_name)  
        return schema 
    
    def table_exists(self, table_name: str) -> Optional[bool]:  
        """  
        Check if table exists in database  

        Args:  
            table_name: Name of the table to check  

        Returns:  
            Optional[bool]: True if exists, False if not exists, None if check fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(self.database_name)  
            if not connection:  
                return None  

            cursor = connection.cursor()  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = %s  
                )  
            """, (self.database_name, table_name))  
            
            return cursor.fetchone()[0]  

        except Exception as e:  
            extra = {  
                'operation': 'table_exists',  
                'params': {'table_name': table_name},  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            self.logger.error(f"Operation failed | {extra}")  
            return None  
        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  

    def create_template_table(self, template_name: str, param: str, force_recreate: bool = False) -> Optional[bool]:  
        """  
        Create a table from template with parameter  
        
        Args:  
            template_name: Base name of the template  
            param: Parameter to append to the table name  
            force_recreate: If True, drop and recreate the table  
            
        Returns:  
            Optional[bool]: Creation result  
        """  
        table_name = f"{template_name}_{param}"  
        return self.create_table(  
            table_name=table_name,  
            force_recreate=force_recreate,  
            table_type='template_tables'  
        )

    def create_table(self, table_name: str, force_recreate: bool = False, table_type: str = 'single_tables') -> Optional[bool]:  
        """  
        Create table based on schema  
        
        Args:  
            table_name: Name of the table to create  
            force_recreate: If True, drop and recreate the table  
            table_type: Type of the table ('single_tables' or 'template_tables')  
            
        Returns:  
            Optional[bool]: Creation result  
        """ 
        connection = None  
        cursor = None  
        error_info = None  

        try:  
            create_table_query = self.get_table_schema(table_name, table_type)  
            if not create_table_query:  
                return None  

            connection = self._connect_to_mysql(self.database_name)  
            if not connection:  
                error_info = {  
                    'error_type': 'ConnectionError',  
                    'message': 'Database connection failed'  
                }  
                return None  

            cursor = connection.cursor()  
            table_exists = self.table_exists(table_name)  
            
            if table_exists is None:  
                error_info = {  
                    'error_type': 'CheckExistenceError',  
                    'message': 'Failed to check table existence'  
                }  
                return None  

            if force_recreate and table_exists:  
                cursor.execute(f"DROP TABLE {table_name}")  
                connection.commit()  
                cursor.execute(create_table_query)  
                connection.commit()
                return True  

            if table_exists and not force_recreate:  
                return False  
            cursor.execute(create_table_query)  
            connection.commit() 
            return True  

        except mysql.connector.Error as e:  
            error_info = {  
                'error_type': 'MySQLError',  
                'message': str(e)  
            }  
        except Exception as e:  
            error_info = {  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  
            if error_info:  
                extra = {  
                    'operation': 'create_table',  
                    'params': {'table_name': table_name, 'force_recreate': force_recreate},  
                    **error_info  
                }  
                self.logger.error(f"Operation failed | {extra}")  
                return None

def main():  
    # MySQL连接配置  
    load_dotenv() 

    # 创建数据库管理器  
    db_manager = CrosschainZoneDatabaseManager(  
        host=os.getenv('DB_HOST'),  
        port=os.getenv('DB_PORT'),  
        user=os.getenv('DB_USER'),  
        password=os.getenv('DB_PASS'),
        database_name=os.getenv('DB_NAME'),
        logger=CrosschainZoneLogger.setup_logging(console_output=True),
    )
    table_name_list = [  
        'crosschainzone_info',      # 跨链区信息表  
        'hub_chain_info',          # 中继链信息表  
        'source_chain_info',       # 源链信息表  
        'system_contract_info',    # 系统合约信息表  
        'event_type',             # 中继链事件类型表
        'event_info',           # 中继链事件信息表（引用hub_tx_info） 
        'hub_block_info',         # 中继链区块信息表（被hub_tx_info引用）  
        'hub_tx_info',           # 中继链交易信息表（引用hub_block_info）  
    ] 
    # for table_name in table_name_list:
    #     print(db_manager.create_table(table_name,force_recreate=True))
    # print(db_manager.table_schemas[table_name])  
    # print(db_manager.create_table('hub_tx_info',force_recreate=True))
    # print(db_manager.create_template_table("source_shadow_info", str(50)))
    for chain_id in range(1,4):
        print(db_manager.create_template_table("source_shadow_info", str(chain_id)))
      

if __name__ == '__main__':  
    main()
#