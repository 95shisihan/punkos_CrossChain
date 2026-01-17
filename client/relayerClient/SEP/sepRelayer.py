import os
import sys
import time
import json
from dotenv import load_dotenv
from web3 import Web3, HTTPProvider
# 【修改点1】Web3.py v7+ 使用 ExtraDataToPOAMiddleware
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# 1. 加载 .env 文件
# 确保脚本运行时能找到 .env 文件，如果不在当前目录，可以在 load_dotenv() 中指定路径
load_dotenv()

# 2. 获取环境变量配置
RPC_URL = os.getenv("DEV_RPC_URL")
# 如果是 Sepolia 测试，你可能想用 SEPOLIA_RPC_URL，这里默认用 DEV
# RPC_URL = os.getenv("SEPOLIA_RPC_URL") 
PRIVATE_KEY = os.getenv("DEV_PRIVATE_KEY")

if not RPC_URL or not PRIVATE_KEY:
    print("❌ 错误: 未在 .env 文件中找到 RPC_URL 或 PRIVATE_KEY")
    sys.exit(1)

print(f"✅ 正在连接 RPC: {RPC_URL}")

# 3. 初始化 Web3
web3 = Web3(HTTPProvider(RPC_URL))

# 【修改点2】注入 PoA 中间件 (适配 Sepolia/BSC 等测试网)
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# 检查连接
if not web3.is_connected():
    print("❌ 无法连接到 RPC 节点，请检查网络或 .env 配置")
    sys.exit(1)

# 获取链信息
try:
    CHAIN_ID = web3.eth.chain_id
    CURRENT_BLOCK = web3.eth.block_number
    print(f"✅ 已连接! Chain ID: {CHAIN_ID}, 当前高度: {CURRENT_BLOCK}")
except Exception as e:
    print(f"❌ 获取链信息失败: {e}")
    sys.exit(1)

# 加载账户
try:
    account = Account.from_key(PRIVATE_KEY)
    print(f"👤 Relayer 账户地址: {account.address}")
except Exception as e:
    print(f"❌ 私钥格式错误: {e}")
    sys.exit(1)


def getBlockHeaderFromHeight(height):
    """
    获取区块头
    注意：标准 Web3.py get_block 不返回 RLP 编码的 header 字段。
    这里假设节点返回了 header，或者如果不存在则返回 hash 用于测试。
    """
    try:
        block = web3.eth.get_block(height)
        if 'header' in block:
            return block['header']
        else:
            # 如果节点不返回 raw header，这里是一个 fallback，
            # 实际生产中可能需要自行组装 RLP 或使用 debug_getRawBlock
            # 这里为了不报错，暂且返回 hash (注意：这在合约校验时可能会失败)
            return block.hash.hex()
    except Exception as e:
        print(f"获取区块头失败: {e}")
        return "0x00"

def getBlockHashFromHeight(height):
    """获取区块哈希"""
    block = web3.eth.get_block(height)
    return block.hash

def commitNewHeader(hexHeader, relayerAddress):
    """生成承诺值 (Commitment)"""
    # 确保 hexHeader 是 bytes 类型
    if isinstance(hexHeader, str):
        if hexHeader.startswith('0x'):
            header_bytes = Web3.to_bytes(hexstr=hexHeader)
        else:
            # 简单的字符串转bytes，视具体业务数据格式而定
            header_bytes = bytes(hexHeader, 'utf-8')
    else:
        header_bytes = hexHeader

    typeList = ['bytes', 'address']
    valueList = [header_bytes, relayerAddress]

    # 计算 keccak256 (Web3 v6/v7 写法)
    hashBytes = web3.solidity_keccak(typeList, valueList)
    return Web3.to_hex(hashBytes)

def startRelayer(relayContractAddress, relayContractAbi):
    """执行搬运逻辑"""
    
    # 获取当前高度
    current_height = web3.eth.block_number
    
    # 示例：搬运当前高度前 10 个区块 (避免重组风险)，或者固定值
    # heightToRelay = 1234 # 固定值测试
    heightToRelay = current_height - 10 
    
    print(f"\n🔄 [Start] 准备搬运高度: {heightToRelay}")
    
    heightToCommit = heightToRelay + 1
    
    # 获取数据
    hexHeaderToRelay = getBlockHeaderFromHeight(heightToRelay)
    hexHeaderToCommit = getBlockHeaderFromHeight(heightToCommit)

    # 生成承诺
    commit_val = commitNewHeader(hexHeaderToCommit, account.address)
    print(f"🔐 生成承诺值: {commit_val}")

    # 获取当前区块哈希
    curHash = getBlockHashFromHeight(heightToCommit)

    # 初始化合约
    contract = web3.eth.contract(address=relayContractAddress, abi=relayContractAbi)

    # 构建交易
    try:
        nonce = web3.eth.get_transaction_count(account.address)
        
        # 估算 Gas Price
        gas_price = web3.eth.gas_price
        
        # 构建 Contract Function
        # 请根据实际 ABI 确认参数顺序和类型
        tx_func = contract.functions.submitCommitedHeaderByRelayer(
            hexHeaderToRelay, 
            curHash, 
            commit_val
        )
        
        # 尝试估算 Gas
        try:
            gas_estimate = tx_func.estimate_gas({'from': account.address})
            gas_limit = int(gas_estimate * 1.2) # 增加 20% 缓冲
        except Exception as e:
            print(f"⚠️ Gas 估算失败，使用默认值: {e}")
            gas_limit = 2000000

        # 构建交易字典
        tx_data = tx_func.build_transaction({
            'chainId': CHAIN_ID,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'from': account.address
        })

        # 签名交易
        signed_tx = web3.eth.account.sign_transaction(tx_data, PRIVATE_KEY)
        
        # 发送交易
        print("🚀 发送交易中...")
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"✅ 交易已发送! Hash: {tx_hash.hex()}")
        
        # 等待回执
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            print(f"🎉 交易成功上链! 区块: {receipt.blockNumber}")
        else:
            print("⚠️ 交易失败 (Reverted)")

    except Exception as e:
        print(f"❌ 交易执行失败: {e}")
        # 这里不抛出异常，以便主循环继续重试
        pass

def testRelayClient(relayContractAddress, relayContractAbi):
    """守护进程循环"""
    print("🤖 Relayer 客户端已启动，按 Ctrl+C 停止")
    while True:
        try:
            startRelayer(relayContractAddress, relayContractAbi)
            # 避免过于频繁请求
            print("⏳ 休眠 10 秒...")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 用户停止程序")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️ 全局错误: {e}")
            print("5秒后重试...")
            time.sleep(5)

if __name__ == "__main__":
    # --- 修改开始 ---
    
    # 方式 A: 直接在这里写死地址和文件路径 (测试最方便)
    # 请替换为你真实的合约地址
    relay_addr_input = "0x05361a6F8C778ebD1695487c178603F3887768ef" 
    
    # 请替换为你真实的 ABI 文件绝对路径
    abi_path_input = "/Users/liujian/Desktop/sepCross/client/relayerClient/SEP/Relay.abi" 
    
    # 如果你想保留命令行传参的功能，可以写成这样：
    if len(sys.argv) >= 3:
        relay_addr_input = sys.argv[1]
        abi_path_input = sys.argv[2]
        
    print(f"🎯 目标合约: {relay_addr_input}")
    print(f"📄 ABI 文件: {abi_path_input}")

    # --- 修改结束 ---

    # 校验地址
    if not Web3.is_address(relay_addr_input):
        print("❌ 错误: 合约地址格式无效，请检查代码中的 relay_addr_input")
        sys.exit(1)
    
    relay_contract_address = Web3.to_checksum_address(relay_addr_input)

    # 读取 ABI
    try:
        with open(abi_path_input, 'r') as abi_file:
            content = abi_file.read()
            try:
                relay_contract_abi = json.loads(content)
            except json.JSONDecodeError:
                relay_contract_abi = eval(content)
    except Exception as e:
        print(f"❌ ABI 文件读取失败: {e}")
        print("💡 请检查 abi_path_input 路径是否正确")
        sys.exit(1)

    testRelayClient(relay_contract_address, relay_contract_abi)
