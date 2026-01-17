import os
import sys 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from typing import List, Tuple, Optional, Dict, Any, Union
import mysql.connector  
from mysql.connector import Error
from basic_db import BasicDatabaseManager
class CrosschainZoneDatabaseManager(BasicDatabaseManager):  
    def __init__(self,  
        host: str,  
        port: str,  
        user: str,  
        password: str,  
        database_name: str,  
        logger: CrosschainZoneLogger  
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

    def create_hub_info_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if Hub_Info table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_hub_info_table',  
                    'database': database_name,  
                    'table': 'Hub_Info',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'Hub_Info'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE Hub_Info")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_hub_info_table',  
                        'database': database_name,  
                        'table': 'Hub_Info',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_hub_info_table',  
                        'database': database_name,  
                        'table': 'Hub_Info',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_hub_info_table',  
                    'database': database_name,  
                    'table': 'Hub_Info',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS Hub_Info (  
                `chain_id` INT PRIMARY KEY DEFAULT 0,  
                `symbol` TEXT,  
                `name` TEXT,  
                `rpc` TEXT,  
                `multi_addr` VARCHAR(42),  
                `source_num` INT,  
                `contract_num` INT  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_hub_info_table',  
                    'database': database_name,  
                    'table': 'Hub_Info',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_hub_info_table',  
                    'database': database_name,  
                    'table': 'Hub_Info',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_hub_info_table',  
                'database': database_name,  
                'table': 'Hub_Info',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_hub_info_table',  
                'database': database_name,  
                'table': 'Hub_Info',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()
    
    def create_source_info_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if Source_Info table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_source_info_table',  
                    'database': database_name,  
                    'table': 'Source_Info',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'Source_Info'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE Source_Info")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_source_info_table',  
                        'database': database_name,  
                        'table': 'Source_Info',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_source_info_table',  
                        'database': database_name,  
                        'table': 'Source_Info',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_source_info_table',  
                    'database': database_name,  
                    'table': 'Source_Info',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS Source_Info (  
                `chain_id` INT PRIMARY KEY DEFAULT 1,  
                `symbol` TEXT,  
                `name` TEXT,  
                `state` INT,  
                `relay_addr` VARCHAR(42),  
                `tx_rule_addr` VARCHAR(42),  
                `transport_addr` VARCHAR(42)  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_source_info_table',  
                    'database': database_name,  
                    'table': 'Source_Info',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_source_info_table',  
                    'database': database_name,  
                    'table': 'Source_Info',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_source_info_table',  
                'database': database_name,  
                'table': 'Source_Info',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_source_info_table',  
                'database': database_name,  
                'table': 'Source_Info',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close() 
    
    def create_system_contract_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if System_Contract table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_system_contract_table',  
                    'database': database_name,  
                    'table': 'System_Contract',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'System_Contract'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE System_Contract")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_system_contract_table',  
                        'database': database_name,  
                        'table': 'System_Contract',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_system_contract_table',  
                        'database': database_name,  
                        'table': 'System_Contract',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_system_contract_table',  
                    'database': database_name,  
                    'table': 'System_Contract',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS System_Contract (  
                `contract_id` INT PRIMARY KEY,  
                `contract_addr` VARCHAR(42) UNIQUE,  
                `manager_addr` VARCHAR(42),  
                `state` INT,  
                `chain_id` INT,  
                `level_id` INT,  
                `visit_block_index` BIGINT DEFAULT 0  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_system_contract_table',  
                    'database': database_name,  
                    'table': 'System_Contract',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_system_contract_table',  
                    'database': database_name,  
                    'table': 'System_Contract',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_system_contract_table',  
                'database': database_name,  
                'table': 'System_Contract',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_system_contract_table',  
                'database': database_name,  
                'table': 'System_Contract',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()
    
    def create_relay_basic_info_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if Relay_Basic_Info table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_relay_basic_info_table',  
                    'database': database_name,  
                    'table': 'Relay_Basic_Info',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'Relay_Basic_Info'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE Relay_Basic_Info")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_relay_basic_info_table',  
                        'database': database_name,  
                        'table': 'Relay_Basic_Info',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_relay_basic_info_table',  
                        'database': database_name,  
                        'table': 'Relay_Basic_Info',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_relay_basic_info_table',  
                    'database': database_name,  
                    'table': 'Relay_Basic_Info',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS Relay_Basic_Info (  
                `chain_id` INT PRIMARY KEY,  
                `genesis_key` VARCHAR(66),  
                `gas_bound` VARCHAR(66),  
                `commit_time_out` VARCHAR(66),  
                `require_stake` VARCHAR(66),  
                `total_penalty` VARCHAR(66),  
                `un_processed_penalty` VARCHAR(66)  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci AUTO_INCREMENT=1  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_relay_basic_info_table',  
                    'database': database_name,  
                    'table': 'Relay_Basic_Info',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_relay_basic_info_table',  
                    'database': database_name,  
                    'table': 'Relay_Basic_Info',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_relay_basic_info_table',  
                'database': database_name,  
                'table': 'Relay_Basic_Info',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_relay_basic_info_table',  
                'database': database_name,  
                'table': 'Relay_Basic_Info',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()
    
    def create_relay_shadow_info_table(  
        self,  
        database_name: str,  
        chain_id: int,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if Relay_Shadow_Info table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            chain_id: Chain ID to be used in table name  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        table_name = f"Relay_Shadow_Info_{chain_id}"  

        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_relay_shadow_info_table',  
                    'database': database_name,  
                    'table': table_name,  
                    'chain_id': chain_id,  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = %s  
                )  
            """, (database_name, table_name))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute(f"DROP TABLE {table_name}")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_relay_shadow_info_table',  
                        'database': database_name,  
                        'table': table_name,  
                        'chain_id': chain_id,  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_relay_shadow_info_table',  
                        'database': database_name,  
                        'table': table_name,  
                        'chain_id': chain_id,  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_relay_shadow_info_table',  
                    'database': database_name,  
                    'table': table_name,  
                    'chain_id': chain_id,  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = f"""  
            CREATE TABLE IF NOT EXISTS {table_name} (  
                `id` INT AUTO_INCREMENT PRIMARY KEY,  
                `key` VARCHAR(66),  
                `parent_key` VARCHAR(66),  
                `commit_tx` VARCHAR(66),  
                `commit_block` BIGINT,  
                `commit_relayer` VARCHAR(42),  
                `commit_value` VARCHAR(66),  
                `open_tx` VARCHAR(66),  
                `open_block` BIGINT,  
                `open_relayer` VARCHAR(42),  
                `open_result` TINYINT(1),  
                `raw_data` TEXT  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci AUTO_INCREMENT=1  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_relay_shadow_info_table',  
                    'database': database_name,  
                    'table': table_name,  
                    'chain_id': chain_id,  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_relay_shadow_info_table',  
                    'database': database_name,  
                    'table': table_name,  
                    'chain_id': chain_id,  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_relay_shadow_info_table',  
                'database': database_name,  
                'table': table_name,  
                'chain_id': chain_id,  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_relay_shadow_info_table',  
                'database': database_name,  
                'table': table_name,  
                'chain_id': chain_id,  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()
    
    def restart_database(
        self,   
        database_name: str
    ) -> Optional[bool]:
        self.create_hub_info_table(database_name,force_recreate=True)
        self.create_source_info_table(database_name,force_recreate=True)
        self.create_system_contract_table(database_name,force_recreate=True)
        self.create_relay_basic_info_table(database_name,force_recreate=True)
        for index in range(4):
            #table_name = f"Relay_Shadow_Info_{index}"
            self.create_relay_shadow_info_table(database_name,index,force_recreate=True)
        return True
    
    def create_btc_raw_data_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if BTCRawData table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_btc_raw_data_table',  
                    'database': database_name,  
                    'table': 'BTCRawData',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'BTCRawData'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE BTCRawData")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_btc_raw_data_table',  
                        'database': database_name,  
                        'table': 'BTCRawData',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_btc_raw_data_table',  
                        'database': database_name,  
                        'table': 'BTCRawData',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_btc_raw_data_table',  
                    'database': database_name,  
                    'table': 'BTCRawData',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS BTCRawData (  
                `hash` VARCHAR(66) PRIMARY KEY,  
                `height` INT,  
                `rawData` TEXT  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_btc_raw_data_table',  
                    'database': database_name,  
                    'table': 'BTCRawData',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_btc_raw_data_table',  
                    'database': database_name,  
                    'table': 'BTCRawData',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_btc_raw_data_table',  
                'database': database_name,  
                'table': 'BTCRawData',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_btc_raw_data_table',  
                'database': database_name,  
                'table': 'BTCRawData',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close() 
    
    def create_eth_raw_data_table(  
        self,  
        database_name: str,  
        force_recreate: bool = False  
    ) -> Optional[bool]:  
        """  
        Check if ETHRawData table exists, create if not exists  
        Optionally force recreate the table  

        Args:  
            database_name: Name of the database to check/create table in  
            force_recreate: If True, drop and recreate the table  

        Returns:  
            Optional[bool]:  
            - True if table is successfully force recreated  
            - False if table is created normally or already exists  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'create_eth_raw_data_table',  
                    'database': database_name,  
                    'table': 'ETHRawData',  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if table exists  
            cursor.execute("""  
                SELECT EXISTS (  
                    SELECT 1   
                    FROM information_schema.TABLES   
                    WHERE TABLE_SCHEMA = %s   
                    AND TABLE_NAME = 'ETHRawData'  
                )  
            """, (database_name,))  
            
            table_exists = cursor.fetchone()[0]  

            # Handle force recreate  
            if force_recreate and table_exists:  
                try:  
                    cursor.execute("DROP TABLE ETHRawData")  
                    connection.commit()  

                    extra = {  
                        'operation': 'create_eth_raw_data_table',  
                        'database': database_name,  
                        'table': 'ETHRawData',  
                        'action': 'drop',  
                        'status': 'success'  
                    }  
                    self.logger.info(f"Existing table dropped successfully | {extra}")  

                except mysql.connector.Error as drop_error:  
                    extra = {  
                        'operation': 'create_eth_raw_data_table',  
                        'database': database_name,  
                        'table': 'ETHRawData',  
                        'action': 'drop',  
                        'error_code': drop_error.errno,  
                        'error_message': str(drop_error),  
                        'status': 'error'  
                    }  
                    self.logger.error(f"Table drop failed | {extra}")  
                    return None  

            # Return if table exists and not force recreating  
            if table_exists and not force_recreate:  
                extra = {  
                    'operation': 'create_eth_raw_data_table',  
                    'database': database_name,  
                    'table': 'ETHRawData',  
                    'action': 'check',  
                    'status': 'success'  
                }  
                self.logger.info(f"Table already exists | {extra}")  
                return True  

            # Create table  
            create_table_query = """  
            CREATE TABLE IF NOT EXISTS ETHRawData (  
                `hash` VARCHAR(66) PRIMARY KEY,  
                `height` INT,  
                `rawData` TEXT  
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci  
            """  
            
            try:  
                cursor.execute(create_table_query)  
                connection.commit()  

                extra = {  
                    'operation': 'create_eth_raw_data_table',  
                    'database': database_name,  
                    'table': 'ETHRawData',  
                    'action': 'create',  
                    'force_recreate': force_recreate,  
                    'status': 'success'  
                }  
                self.logger.info(f"Table created successfully | {extra}")  
                return force_recreate  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_eth_raw_data_table',  
                    'database': database_name,  
                    'table': 'ETHRawData',  
                    'action': 'create',  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Table creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_eth_raw_data_table',  
                'database': database_name,  
                'table': 'ETHRawData',  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_eth_raw_data_table',  
                'database': database_name,  
                'table': 'ETHRawData',  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during table operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()