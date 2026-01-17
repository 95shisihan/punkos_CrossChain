from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()  # 载入 .env 文件

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
print(f"SEPOLIA_RPC_URL={SEPOLIA_RPC_URL}")

w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

if w3.is_connected():
    latest_height = w3.eth.block_number
    print(f"最新区块高度: {latest_height}")
else:
    print("节点连接失败")
