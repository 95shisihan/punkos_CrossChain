import os
import sys 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from typing import List, Tuple, Optional, Dict, Any, Union
import mysql.connector  
from mysql.connector import Error  
class BasicDatabaseManager:  
    def __init__(self,  
        host: str,  
        port: str,  
        user: str,  
        password: str,  
        database_name: str,  
        logger: CrosschainZoneLogger  
    ):  
        self.host = host  
        self.port = port  
        self.user = user  
        self.password = password  
        self.database_name = database_name  
        self.logger = logger  

    def _connect_to_mysql(  
        self,  
        database: Optional[str] = None  
    ) -> Optional[mysql.connector.connection.MySQLConnection]:  
        try:  
            # Establish connection  
            connection = mysql.connector.connect(  
                host=self.host,  
                port=self.port,  
                user=self.user,  
                password=self.password,  
                database=database if database else None,  
                connect_timeout=10,  # Connection timeout in seconds  
                buffered=True,  
                charset='utf8mb4'  
            )  
            return connection      
        except Exception as e:  
            return None  

    def create_database(  
        self,  
        database_name: str  
    ) -> Optional[bool]:  
        """  
        Check if database exists, create if not exists  

        Args:  
            database_name: Name of the database to check/create  

        Returns:  
            Optional[bool]:  
            - True if database already exists  
            - False if database is successfully created  
            - None if database creation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql()  
            if not connection:  
                extra = {  
                    'operation': 'create_database',  
                    'database': database_name,  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor()  

            # Check if database exists  
            cursor.execute("SHOW DATABASES LIKE %s", (database_name,))  
            result = cursor.fetchone()  

            # If database exists, return True  
            if result:  
                extra = {  
                    'operation': 'create_database',  
                    'database': database_name,  
                    'action': 'check',  
                    'exists': True,  
                    'status': 'success'  
                }  
                self.logger.info(f"Database already exists | {extra}")  
                return True  

            # If database does not exist, attempt to create  
            try:  
                cursor.execute(f"CREATE DATABASE {database_name}")  
                connection.commit()  

                extra = {  
                    'operation': 'create_database',  
                    'database': database_name,  
                    'action': 'create',  
                    'status': 'success'  
                }  
                self.logger.info(f"Database created successfully | {extra}")  
                return False  

            except mysql.connector.Error as create_error:  
                extra = {  
                    'operation': 'create_database',  
                    'database': database_name,  
                    'error_code': create_error.errno,  
                    'error_message': str(create_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Database creation failed | {extra}")  
                return None  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'create_database',  
                'database': database_name,  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return None  

        except Exception as e:  
            extra = {  
                'operation': 'create_database',  
                'database': database_name,  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.critical(f"Unexpected error during database operation | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()

    def upsert_generic(  
            self,  
            table_name: str,  
            key_columns: Dict[str, Any],  
            data: Dict[str, Any]  
        ) -> Optional[bool]:  
        """  
        Generic method for inserting or updating records with composite key support  

        Args:  
            table_name: Target database table  
            key_columns: Dictionary of key columns and their values, supports single or composite keys  
                Example: {'id': 1} or {'year': 2024, 'month': 1}  
            data: Dictionary of column names and values to upsert  

        Returns:  
            Optional[bool]:  
            - True: Successful insertion  
            - False: Successful update  
            - None: Operation failed or multiple records found  
        """  
        connection = None  
        cursor = None  
        error_info = None  

        try:  
            connection = self._connect_to_mysql(self.database_name)  
            if not connection:  
                error_info = {  
                    'error_type': 'ConnectionError',  
                    'message': 'Database connection failed'  
                }  
                return None  

            cursor = connection.cursor(dictionary=True)  

            # Build where conditions using parameterized queries  
            where_conditions = ' AND '.join([f"{col} = %s" for col in key_columns])  
            where_values = list(key_columns.values())  

            # Check record count  
            check_sql = f"SELECT COUNT(*) as count FROM {table_name} WHERE {where_conditions}"  
            cursor.execute(check_sql, where_values)  
            result = cursor.fetchone()  
            record_count = result['count']  

            if record_count > 1:  
                error_info = {  
                    'error_type': 'MultipleRecordsError',  
                    'message': f'Found {record_count} records for keys: {key_columns}'  
                }  
                return None  

            record_exists = record_count == 1  

            # Prepare SQL with parameterized queries  
            if not record_exists:  
                all_data = {**key_columns, **data}  
                columns = list(all_data.keys())  
                placeholders = ', '.join(['%s'] * len(all_data))  
                values = list(all_data.values())  
                
                upsert_sql = f"""  
                INSERT INTO {table_name}  
                ({', '.join(columns)})  
                VALUES ({placeholders})  
                """  
            else:  
                set_clause = ', '.join([f"{col} = %s" for col in data.keys()])  
                values = list(data.values()) + where_values  
                
                upsert_sql = f"""  
                UPDATE {table_name}  
                SET {set_clause}  
                WHERE {where_conditions}  
                """  

            cursor.execute(upsert_sql, values)  
            connection.commit()  
            return not record_exists  

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
                    'operation': 'upsert_generic',  
                    'params': {  
                        'table_name': table_name,  
                        'key_columns': key_columns,  
                        'data': data  
                    },  
                    **error_info  
                }  
                self.logger.error(f"Operation failed | {extra}")  
                return None
    
    def get_specific_columns_by_key(  
        self,  
        table_name: str,  
        key_columns: Dict[str, Any],  
        columns_to_retrieve: List[str]  
    ) -> Optional[Dict[str, Any]]:  
        """  
        Retrieve specific columns and handle single record case  

        Args:  
            table_name: Name of the table to query  
            key_columns: Dictionary of key columns and their values  
                Example: {'id': 1} or {'year': 2024, 'month': 1}  
            columns_to_retrieve: List of column names to retrieve  

        Returns:  
            Optional[Dict[str, Any]]:  
            - Dict: Record data if exactly one record found  
            - False: No record found  
            - None: Multiple records found or query failed  
        """  
        connection = None  
        cursor = None  
        error_info = None  

        try:  
            connection = self._connect_to_mysql(self.database_name)  
            if not connection:  
                error_info = {  
                    'error_type': 'ConnectionError',  
                    'message': 'Database connection failed'  
                }  
                return None  

            cursor = connection.cursor(dictionary=True)  

            # 构建查询  
            where_conditions = ' AND '.join([f"{col} = %s" for col in key_columns])  
            where_values = list(key_columns.values())  
            columns_str = ', '.join(columns_to_retrieve)  
            
            query = f"""  
            SELECT {columns_str}  
            FROM {table_name}  
            WHERE {where_conditions}  
            """  

            # 执行查询  
            cursor.execute(query, where_values)  
            results = cursor.fetchall()  

            # 根据记录数返回相应结果  
            if len(results) == 0:  
                return False  
            elif len(results) == 1:  
                return results[0]  # 返回唯一记录的数据  
            else:  
                error_info = {  
                    'error_type': 'MultipleRecordsError',  
                    'message': f'Found {len(results)} records, expected 0 or 1'  
                }  
                return None  

        except mysql.connector.Error as e:  
            error_info = {  
                'error_type': 'MySQLError',  
                'message': str(e)  
            }  
            return None  

        except Exception as e:  
            error_info = {  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return None  

        finally:  
            # 关闭资源  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  

            # 记录错误日志（仅在发生错误或发现多条记录时）  
            if error_info:  
                extra = {  
                    'operation': 'get_specific_columns_by_key',  
                    'params': {  
                        'table_name': table_name,  
                        'key_columns': key_columns,  
                        'columns_to_retrieve': columns_to_retrieve  
                    },  
                    **error_info  
                }  
                self.logger.error(f"Operation failed | {extra}") 
    
    def get_database_all_tables(  
        self,  
        database_name: str  
    ) -> Optional[List[str]]:  
        """  
        Retrieve all table names from specified database  

        Args:  
            database_name: Name of the database to query  

        Returns:  
            Optional[List[str]]:  
            - List of table names if successful  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'get_all_tables',  
                    'database': database_name,  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor(dictionary=True)  
            cursor.execute("SHOW TABLES")  
            tables = cursor.fetchall()  
            
            table_names = [list(table.values())[0] for table in tables]  
            
            extra = {  
                'operation': 'get_all_tables',  
                'database': database_name,  
                'table_count': len(table_names),  
                'status': 'success'  
            }  
            self.logger.info(f"Tables retrieved successfully | {extra}")  
            return table_names  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'get_all_tables',  
                'database': database_name,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Failed to retrieve tables | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  

    def check_table_exists(  
        self,  
        database_name: str,  
        table_name: str  
    ) -> Optional[bool]:  
        """  
        Check if specified table exists in database  

        Args:  
            database_name: Name of the database to check  
            table_name: Name of the table to verify  

        Returns:  
            Optional[bool]:  
            - True if table exists  
            - False if table doesn't exist  
            - None if operation fails  
        """  
        connection = None  
        cursor = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'check_table_exists',  
                    'database': database_name,  
                    'table': table_name,  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return None  

            cursor = connection.cursor(dictionary=True)  
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))  
            result = cursor.fetchone()  

            exists = bool(result)  
            extra = {  
                'operation': 'check_table_exists',  
                'database': database_name,  
                'table': table_name,  
                'exists': exists,  
                'status': 'success'  
            }  
            self.logger.info(f"Table existence check completed | {extra}")  
            return exists  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'check_table_exists',  
                'database': database_name,  
                'table': table_name,  
                'error': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Failed to check table existence | {extra}")  
            return None  

        finally:  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close() 

    def print_table_data(  
        self,  
        database_name: str,  
        table_name: str,  
        limit: Optional[int] = None  
    ) -> bool:  
        """  
        Print all data from specified table  

        Args:  
            database_name: Name of the database  
            table_name: Name of the table to query  
            limit: Optional limit for number of records to return  

        Returns:  
            bool:  
            - True if data printed successfully  
            - False if operation fails  
        """  
        connection = None  
        try:  
            connection = self._connect_to_mysql(database_name)  
            if not connection:  
                extra = {  
                    'operation': 'print_table_data',  
                    'database': database_name,  
                    'table': table_name,  
                    'status': 'failed'  
                }  
                self.logger.error(f"Database connection failed | {extra}")  
                return False  

            try:  
                with connection.cursor(dictionary=True) as cursor:  
                    # Build query with parameterized input  
                    query = "SELECT * FROM %s" % table_name  
                    if limit is not None:  
                        query += " LIMIT %s"  
                        cursor.execute(query, (limit,))  
                    else:  
                        cursor.execute(query)  

                    results = cursor.fetchall()  

                    if not results:  
                        extra = {  
                            'operation': 'print_table_data',  
                            'database': database_name,  
                            'table': table_name,  
                            'status': 'success',  
                            'record_count': 0  
                        }  
                        self.logger.info(f"No data found in table | {extra}")  
                        return True  

                    # Print table headers  
                    headers = list(results[0].keys())  
                    print("\n" + "=" * 50)  
                    print(f"Table: {table_name} Data")  
                    print("=" * 50)  

                    header_format = " | ".join(["{:<20}"] * len(headers))  
                    print(header_format.format(*headers))  
                    print("-" * 50)  

                    # Print data rows  
                    for row in results:  
                        row_values = [str(row[header]) for header in headers]  
                        print(header_format.format(*row_values))  

                    print("=" * 50)  
                    print(f"Total Records: {len(results)}\n")  

                    extra = {  
                        'operation': 'print_table_data',  
                        'database': database_name,  
                        'table': table_name,  
                        'status': 'success',  
                        'record_count': len(results),  
                        'columns': headers  
                    }  
                    self.logger.info(f"Table data printed successfully | {extra}")  
                    return True  

            except mysql.connector.Error as query_error:  
                extra = {  
                    'operation': 'print_table_data',  
                    'database': database_name,  
                    'table': table_name,  
                    'error_code': query_error.errno,  
                    'error_message': str(query_error),  
                    'status': 'error'  
                }  
                self.logger.error(f"Query execution failed | {extra}")  
                return False  

        except mysql.connector.Error as e:  
            extra = {  
                'operation': 'print_table_data',  
                'database': database_name,  
                'table': table_name,  
                'error_code': e.errno,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Database operation failed | {extra}")  
            return False  

        except Exception as e:  
            extra = {  
                'operation': 'print_table_data',  
                'database': database_name,  
                'table': table_name,  
                'error_type': type(e).__name__,  
                'error_message': str(e),  
                'status': 'error'  
            }  
            self.logger.error(f"Unexpected error during table data printing | {extra}")  
            return False  

        finally:  
            if connection:  
                connection.close()

    def get_all_records_by_conditions(  
        self,  
        table_name: str,  
        conditions: Optional[Dict[str, Any]] = None,  
        columns_to_retrieve: Optional[List[str]] = None,  
        order_by: Optional[Dict[str, str]] = None,  
        limit: Optional[int] = None  
    ) -> Optional[List[Dict[str, Any]]]:  
        """  
        Retrieve all records that match the given conditions  

        Args:  
            table_name: Name of the table to query  
            conditions: Dictionary of conditions and their values  
                Example: {'status': 'active'} or {'year': 2024, 'amount': 1000}  
            columns_to_retrieve: List of column names to retrieve, None for all columns  
            order_by: Dictionary specifying order  
                Example: {'created_at': 'DESC', 'id': 'ASC'}  
            limit: Maximum number of records to return  

        Returns:  
            Optional[List[Dict[str, Any]]]:  
            - List[Dict]: List of records if query successful  
            - None: Query failed  
        """  
        connection = None  
        cursor = None  
        error_info = None  

        try:  
            connection = self._connect_to_mysql(self.database_name)  
            if not connection:  
                error_info = {  
                    'error_type': 'ConnectionError',  
                    'message': 'Database connection failed'  
                }  
                return None  

            cursor = connection.cursor(dictionary=True)  

            # 构建查询  
            columns_str = '*' if not columns_to_retrieve else ', '.join(columns_to_retrieve)  
            query = f"SELECT {columns_str} FROM {table_name}"  

            # 处理WHERE条件  
            where_values = []  
            if conditions:  
                where_conditions = []  
                for col, val in conditions.items():  
                    if val is None:  
                        where_conditions.append(f"{col} IS NULL")  
                    else:  
                        where_conditions.append(f"{col} = %s")  
                        where_values.append(val)  
                
                if where_conditions:  
                    query += f" WHERE {' AND '.join(where_conditions)}"  

            # 处理ORDER BY  
            if order_by:  
                order_clauses = [  
                    f"{col} {direction}"   
                    for col, direction in order_by.items()  
                ]  
                query += f" ORDER BY {', '.join(order_clauses)}"  

            # 处理LIMIT  
            if limit:  
                query += f" LIMIT %s"  
                where_values.append(limit)  

            # 执行查询  
            cursor.execute(query, where_values)  
            results = cursor.fetchall()  

            return results  

        except mysql.connector.Error as e:  
            error_info = {  
                'error_type': 'MySQLError',  
                'message': str(e)  
            }  
            return None  

        except Exception as e:  
            error_info = {  
                'error_type': type(e).__name__,  
                'message': str(e)  
            }  
            return None  

        finally:  
            # 关闭资源  
            if cursor:  
                cursor.close()  
            if connection:  
                connection.close()  

            # 记录错误日志（仅在发生错误时）  
            if error_info:  
                extra = {  
                    'operation': 'get_all_records_by_conditions',  
                    'params': {  
                        'table_name': table_name,  
                        'conditions': conditions,  
                        'columns_to_retrieve': columns_to_retrieve,  
                        'order_by': order_by,  
                        'limit': limit  
                    },  
                    **error_info  
                }  
                self.logger.error(f"Operation failed | {extra}") 