import sys
import json
import rlp
import logging
from dotenv import load_dotenv
from web3 import Web3
from eth_utils import decode_hex
import os

# 日志配置，简单示范
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SepoliaBlockHeader")

# 加载环境变量
load_dotenv()

# Sepolia RPC地址环境变量
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")

def to_hex_str(x):
    # helper: bytes或HexBytes转hex字符串，str保持不变
    # HexBytes需要先import，如果web3>=5,类型是HexBytes
    try:
        from hexbytes import HexBytes
    except ImportError:
        HexBytes = bytes

    if isinstance(x, bytes) or isinstance(x, HexBytes):
        return x.hex() if not x.startswith(b'0x') else x.decode()
    if isinstance(x, str):
        return x
    raise TypeError(f"Unexpected type {type(x)}")

def encode_block_header(block):
    """
    以太坊块头字段按顺序RLP编码
    """
    try:
        header = [
            decode_hex(to_hex_str(block.parentHash)),
            decode_hex(to_hex_str(block.sha3Uncles)),
            decode_hex(block.miner),   # 地址，decode_hex支持
            decode_hex(to_hex_str(block.stateRoot)),
            decode_hex(to_hex_str(block.transactionsRoot)),
            decode_hex(to_hex_str(block.receiptsRoot)),
            decode_hex(to_hex_str(block.logsBloom)),
            block.difficulty,
            block.number,
            block.gasLimit,
            block.gasUsed,
            block.timestamp,
            bytes.fromhex(to_hex_str(block.extraData)[2:]),  # 去掉0x
            decode_hex(to_hex_str(block.mixHash)),
            decode_hex(to_hex_str(block.nonce)),
        ]
        encoded = rlp.encode(header).hex()
        return encoded
    except Exception as e:
        logger.error(f"编码区块头失败: {e}")
        raise

def fetch_block_from_rpc(web3, height):
    """
    从 RPC 获取区块并编码
    """
    block = web3.eth.get_block(height)
    if block is None:
        raise Exception(f"区块 {height} 不存在")
    block_hash = block.hash.hex()
    encoded_header = encode_block_header(block)
    return block_hash, encoded_header

def get_block_header(height: int):
    """
    直接调用RPC获取编码好的区块头
    """
    try:
        w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
        if not w3.is_connected():
            raise Exception("无法连接到Sepolia RPC节点")

        block_hash, encoded_header = fetch_block_from_rpc(w3, height)
        return block_hash, encoded_header

    except Exception as e:
        logger.error(f"获取区块头失败: {e}")
        raise

def main():
    if len(sys.argv) < 2:
        print("用法: python get_SEP_Header.py <区块高度>")
        sys.exit(1)

    height = int(sys.argv[1])
    try:
        block_hash, raw_header = get_block_header(height)
        output = {
            "status": True,
            "hash": block_hash,
            "raw": raw_header,
            "height": height
        }
    except Exception as e:
        output = {
            "status": False,
            "message": str(e)
        }

    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
