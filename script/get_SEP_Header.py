import os
import sys
import json
import rlp
import logging
from dotenv import load_dotenv
from web3 import Web3
from eth_utils import decode_hex, to_bytes
from hexbytes import HexBytes 
import mysql.connector
from mysql.connector import Error

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SepoliaBlockHeader")

# 加载环境变量
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset='utf8mb4'  # 避免中文/特殊字符乱码
        )
        if conn.is_connected():
            logger.info("✅ 数据库连接成功")
        return conn
    except Error as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def to_hex_str(x):
    if isinstance(x, (bytes, HexBytes)):
        return x.hex() if not x.startswith(b'0x') else x.decode()
    if isinstance(x, str):
        return x
    if isinstance(x, int):
        return hex(x)
    if x is None:
        return "0x"
    raise TypeError(f"Unexpected type {type(x)}")

def get_block_header_fields(block):
    """
    构造区块头字段列表（List），但不进行 RLP 编码。
    返回的是一个 Python List，里面包含 byte strings。
    """
    try:
        # 1. 基础 15 个字段 (Legacy)
        extra_data = decode_hex(to_hex_str(block.extraData))
        
        header = [
            decode_hex(to_hex_str(block.parentHash)),       # [0]
            decode_hex(to_hex_str(block.sha3Uncles)),       # [1]
            decode_hex(to_hex_str(block.miner)),            # [2]
            decode_hex(to_hex_str(block.stateRoot)),        # [3]
            decode_hex(to_hex_str(block.transactionsRoot)), # [4]
            decode_hex(to_hex_str(block.receiptsRoot)),     # [5]
            decode_hex(to_hex_str(block.logsBloom)),        # [6]
            block.difficulty,                               # [7]
            block.number,                                   # [8]
            block.gasLimit,                                 # [9]
            block.gasUsed,                                  # [10]
            block.timestamp,                                # [11]
            extra_data,                                     # [12]
            decode_hex(to_hex_str(block.mixHash)),          # [13] (合约 getKeyFromShadowBlock 读取这里)
            decode_hex(to_hex_str(block.nonce)),            # [14]
        ]

        # 2. 补全字段适配 EVM 升级 (EIP-1559, Shanghai, Cancun)
        # 虽然合约里 getKey 只读到索引 13，但为了完整性我们尽量补全
        
        # [15] BaseFee
        base_fee = getattr(block, 'baseFeePerGas', 0)
        if base_fee is None: base_fee = 0
        header.append(base_fee)

        # [16] WithdrawalsRoot
        empty_root = b'\x00' * 32
        w_root = getattr(block, 'withdrawalsRoot', None)
        if w_root:
            header.append(decode_hex(to_hex_str(w_root)))
        else:
            header.append(empty_root)
        
        # [17] BlobGasUsed
        blob_gas = getattr(block, 'blobGasUsed', 0)
        if blob_gas is None: blob_gas = 0
        header.append(blob_gas)
        
        # [18] ExcessBlobGas
        excess_blob = getattr(block, 'excessBlobGas', 0)
        if excess_blob is None: excess_blob = 0
        header.append(excess_blob)
            
        # [19] ParentBeaconBlockRoot
        beacon_root = getattr(block, 'parentBeaconBlockRoot', None)
        if beacon_root:
            header.append(decode_hex(to_hex_str(beacon_root)))
        else:
            header.append(empty_root)

        return header

    except Exception as e:
        logger.error(f"构造区块头字段失败: {e}")
        import traceback
        traceback.print_exc()
        raise

def build_beacon_layer_data(block):
    """
    构造Beacon层数据（RLP列表类型，包含至少5个核心字段）
    字段对应合约解析：
    [0] slot (区块高度，对应newSlot)
    [1] proposerIndex (固定为0，测试用)
    [2] parentRoot (区块parentHash)
    [3] stateRoot (区块stateRoot)
    [4] bodyRoot (区块transactionsRoot)
    """
    try:
        beacon_data = [
            block.number,  # [0] slot (核心！对应合约的newSlot)
            0,             # [1] proposerIndex (测试用，固定为0)
            decode_hex(to_hex_str(block.parentHash)),  # [2] parentRoot
            decode_hex(to_hex_str(block.stateRoot)),   # [3] stateRoot
            decode_hex(to_hex_str(block.transactionsRoot)),  # [4] bodyRoot
        ]
        return beacon_data
    except Exception as e:
        logger.error(f"构造Beacon层数据失败: {e}")
        raise


def fetch_block_payload(web3, height):
    """
    获取区块并包装成合约需要的双层 RLP 结构
    Structure: RLP( [ BeaconBytes, [HeaderField1, HeaderField2, ...] ] )
    """
    block = web3.eth.get_block(height)
    if block is None:
        raise Exception(f"区块 {height} 不存在")
    
    block_hash = block.hash.hex()
    
    # 1. 构造Beacon层数据（RLP列表类型，5个核心字段）
    beacon_layer = build_beacon_layer_data(block)
    # 2. 构造执行层数据（RLP列表类型，14个核心字段）
    exec_layer = get_block_header_fields(block)

    payload_list = [beacon_layer, exec_layer]
    
    # 4. RLP编码整体（确保是bytes类型）
    encoded_payload = rlp.encode(payload_list)
    encoded_payload_hex = "0x" + encoded_payload.hex()
    
    return block_hash, encoded_payload_hex

def save_to_database(block_hash, height, raw_data):
    """将区块数据存入 SepoliaRawData 表"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先检查是否已存在该高度的区块（避免重复插入）
        check_sql = "SELECT id FROM SepoliaRawData WHERE height = %s"
        cursor.execute(check_sql, (height,))
        exists = cursor.fetchone()
        
        if exists:
            # 已存在则更新
            update_sql = """
                UPDATE SepoliaRawData 
                SET hash = %s, rawData = %s 
                WHERE height = %s
            """
            cursor.execute(update_sql, (block_hash, raw_data, height))
            logger.info(f"📝 区块 {height} 数据已更新到数据库")
        else:
            # 不存在则插入
            insert_sql = """
                INSERT INTO SepoliaRawData (hash, height, rawData)
                VALUES (%s, %s, %s)
            """
            cursor.execute(insert_sql, (block_hash, height, raw_data))
            logger.info(f"📝 区块 {height} 数据已插入到数据库")
        
        conn.commit()
    except Error as e:
        logger.error(f"❌ 写入数据库失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_block_header(height: int):
    conn = None
    cursor = None
    try:
        # 这里暂时不从数据库读，确保生成的是新格式
        # conn = get_db_connection() ...
        
        logger.info(f"直接调用 RPC 获取区块 {height} 并构造 Genesis Payload...")
        w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
        if not w3.is_connected():
            raise Exception("无法连接到Sepolia RPC节点")

        block_hash, raw_payload = fetch_block_payload(w3, height)

        # 如果需要，可以在这里把 encoded_payload 存回数据库
        # 2. 确保raw_payload格式正确
        if not raw_payload.startswith("0x"):
            raw_payload = "0x" + raw_payload
        # 3. 写入数据库
        save_to_database(block_hash, height, raw_payload)

        return block_hash, raw_payload

    except Exception as e:
        logger.error(f"获取区块头失败: {e}")
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def main():
    if len(sys.argv) < 2:
        print("用法: python get_SEP_Header.py <区块高度>")
        sys.exit(1)

    try:
        height = int(sys.argv[1])
    except ValueError:
        print(json.dumps({"status": False, "message": "Height must be an integer"}))
        sys.exit(1)

    if height == -1 or height == 0:
        # 获取最新区块
        try:
            w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
            height = w3.eth.block_number
        except:
            print(json.dumps({"status": False, "message": "Cannot connect to RPC"}))
            sys.exit(1)

    try:
        # 1. 获取符合 setGenesisShadowBlock 要求的 rawData
        block_hash, raw_payload = get_block_header(height)

        if not raw_payload.startswith("0x"):
            raw_payload = "0x" + raw_payload

        # 2. 生成 params (uint256)
        # 合约代码: lastSlot = abi.decode(params, (uint256));
        # 我们需要将 height 编码为 32 字节的大端序 Hex
        # 对应 Solidity 的 abi.encode(uint256(height))
        params_bytes = height.to_bytes(32, byteorder='big')
        encoded_params = "0x" + params_bytes.hex()
            
        output = {
            "status": True,
            "hash": block_hash,
            "raw": raw_payload,           # 对应 Solidity 的 _rawGenesisShadowBlock
            "rawValidators": encoded_params, # 对应 Solidity 的 _params (实际上是 lastSlot)
            "height": height
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        output = {
            "status": False,
            "message": str(e)
        }

    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
