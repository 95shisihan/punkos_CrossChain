from dotenv import load_dotenv  
import os
import sys 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  
sys.path.insert(0, project_root)
from log.log_config import CrosschainZoneLogger
from crosschainzone_db import CrosschainZoneDatabaseManager as DatabaseManager

def main():  
    # MySQL连接配置  
    load_dotenv() 

    # 创建数据库管理器  
    db_manager = DatabaseManager(  
        host=os.getenv('DB_HOST'),  
        port=os.getenv('DB_PORT'),  
        user=os.getenv('DB_USER'),  
        password=os.getenv('DB_PASS'),
        database_name=os.getenv('DB_NAME'),
        logger=CrosschainZoneLogger.setup_logging(console_output=True),
    )  

    try:  
        # 数据库名称  
        DATABASE_NAME = os.getenv('DB_NAME')    

        # 检查数据库是否存在，不存在则创建    
        if db_manager.create_database(DATABASE_NAME) is None:  
            print("数据库创建失败，程序退出")  
            return  
        #db_manager.restart_database(DATABASE_NAME)

        print(db_manager.get_database_all_tables(DATABASE_NAME)) 
        
        #db_manager.create_btc_raw_data_table(DATABASE_NAME,force_recreate=False)
        #db_manager.create_eth_raw_data_table(DATABASE_NAME,force_recreate=False)  
        #print("数据库和表检查完成") 
        #db_manager.print_table_data(DATABASE_NAME, 'Hub_Info') 
        #db_manager.print_table_data(DATABASE_NAME, 'Source_Info')
        #db_manager.print_table_data(DATABASE_NAME, 'System_Contract')
        #b_manager.print_table_data(DATABASE_NAME, 'Relay_Basic_Info')
        #chain_id = 0
        #table_name = f"Relay_Shadow_Info_{chain_id}"
        #db_manager.print_table_data(DATABASE_NAME, table_name)
    except Exception as e:  
        print(f"发生错误: {e}")  

if __name__ == '__main__':  
    main()