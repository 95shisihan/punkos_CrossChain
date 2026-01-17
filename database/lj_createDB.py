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
        # ========== 新增：测试数据库连接并执行 SHOW DATABASES ==========
        # 手动测试连接（调用数据库管理器的底层连接方法，或直接创建连接）
        connection = None
        try:
            # 尝试建立数据库连接（使用配置的参数）
            import mysql.connector  # 确保导入mysql模块
            connection = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT')),  # 端口需转为整数
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASS')
            )
            if connection.is_connected():
                print("✅ 数据库连接成功！")
                
                # 执行 SHOW DATABASES 并输出结果
                cursor = connection.cursor()
                cursor.execute("SHOW DATABASES;")
                databases = cursor.fetchall()
                print("\n📋 当前数据库列表：")
                for db in databases:
                    print(f" - {db[0]}")
                cursor.close()
        except mysql.connector.Error as e:
            print(f"❌ 数据库连接失败：{e}")
            return
        finally:
            if connection and connection.is_connected():
                connection.close()
        # ========== 新增结束 ==========

        # 数据库名称  
        DATABASE_NAME = os.getenv('DB_NAME')    

        # 检查数据库是否存在，不存在则创建    
        if db_manager.create_database(DATABASE_NAME) is None:  
            print("数据库创建失败，程序退出")  
            return  

        print("\n📊 目标数据库中的表列表：")
        print(db_manager.get_database_all_tables(DATABASE_NAME))  

    except Exception as e:  
        print(f"发生错误: {e}")  

if __name__ == '__main__':  
    main()