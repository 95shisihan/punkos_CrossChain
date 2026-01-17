from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from eth_account import Account
import time
import sys

# 初始化 Web3 实例
web3 = Web3(HTTPProvider('http://localhost:8545'))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# 获取区块头信息
def getBlockHeaderFromHeight(height):
    """
    从以太坊全节点查询某高度对应的区块头
    
    参数：
    height -- 区块高度

    返回值：
    区块头
    """
    block = web3.eth.get_block(height)
    return block['header']

def getBlockHashFromHeight(height):
    """
    从以太坊全节点查询某高度对应的区块哈希
    
    参数：
    height -- 区块高度

    返回值：
    区块哈希
    """
    block = web3.eth.get_block(height)
    return block.hash

def getTopBlockHeight():
    """
    查询以太坊主链高度
    
    返回值：
    最大高度
    """
    return web3.eth.block_number

# 提交区块头并生成承诺值
def commitNewHeader(hexHeader, relayerAddress):
    """
    生成搬运工对区块头的承诺
    
    参数：
    hexHeader -- 区块头
    relayerAddress -- 搬运工账户

    返回值：
    承诺值
    """
    # 构建类型列表和值列表
    typeList = ['bytes', 'address']
    valueList = [
        Web3.to_bytes(hexstr=hexHeader),  # 将十六进制字符串转换为字节数组
        relayerAddress
    ]

    # 计算 keccak256 哈希值
    hashBytes = web3.solidityKeccak(typeList, valueList)

    # 返回十六进制格式的哈希值
    return Web3.toHex(hashBytes)

# 启动搬运工并执行操作
def startRelayer(relayContractAddress, relayContractAbi):
    # 生成随机私钥
    privateKey = Account.create().privateKey.hex()

    heightToRelay = 1234  # 假设是固定值
    #heightToRelay = getTopBlockHeight()  # 获取当前最新区块高度
    print("当前最新区块高度:", heightToRelay)
    heightToCommit = heightToRelay + 1
    hexHeaderToRelay = getBlockHeaderFromHeight(heightToRelay)
    hexHeaderToCommit = getBlockHeaderFromHeight(heightToCommit)
    print("成功获取源链数据！")

    # 生成承诺值
    relayerAddress = Account.privateKeyToAccount(privateKey).address
    value = commitNewHeader(hexHeaderToCommit, relayerAddress)
    print("准备向链上提交数据！")
    #curHash = Web3.to_hex(hexstr=getBlockHashFromHeight(heightToCommit,param))
    # curHash = foundry_cli(f'cast --to-uint256 {getBlockHashFromHeight(heightToCommit,param)}')
    curHash = getBlockHashFromHeight(heightToCommit)
    # 发送交易提交数据到链上
    #relayContractAbi = [...]  # 替换为合约 ABI
    contract = web3.eth.contract(address=relayContractAddress, abi=relayContractAbi)

    nonce = web3.eth.getTransactionCount(relayerAddress)
    tx = contract.functions.submitCommitedHeaderByRelayer(hexHeaderToRelay, curHash, value).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('40', 'gwei'),
        'nonce': nonce,
    })

    signedTx = web3.eth.account.signTransaction(tx, privateKey)
    txHash = web3.eth.sendRawTransaction(signedTx.rawTransaction)
    print("提交成功！Tx Hash:", txHash.hex())

def queryCurEpoch(relayContractAddress, relayContractAbi):
    # 初始化合约实例
    contract = web3.eth.contract(address=relayContractAddress, abi=relayContractAbi)

    # 调用智能合约方法
    curEpoch = contract.functions.getCurEpoch().call()

    return curEpoch

def relayClient(relayContractAddress, relayContractAbi):
    while True:
        try:
            curEpoch = queryCurEpoch(relayContractAddress, relayContractAbi)
            startRelayer(relayContractAddress, relayContractAbi)
            newEpoch = queryCurEpoch(relayContractAddress, relayContractAbi)
            if newEpoch > curEpoch:
                time.sleep(2)
        except Exception as e:
            print("错误：", e)
            print("5秒后重试")
            time.sleep(5)

def testRelayClient(relayContractAddress, relayContractAbi):
    while True:
        try:
            startRelayer(relayContractAddress, relayContractAbi)
        except Exception as e:
            print("错误：", e)
            print("5秒后重试")
            time.sleep(5)

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("请输入参数！")
#         sys.exit(1)
#     if sys.argv[1] == '1':
#         testRelayClient(relayContractAddress, relayContractAbi)
#     else:
#         print("输入参数错误！")
#         sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <relayContractAddress> <relayContractAbi>")
        sys.exit(1)

    relayContractAddress = sys.argv[1]

    try:
        with open(sys.argv[2], 'r') as abiFile:
            relayContractAbi = eval(abiFile.read())
    except (IOError, ValueError):
        print("Error: Invalid ABI file or format.")
        sys.exit(1)

    testRelayClient(relayContractAddress, relayContractAbi)

# # 示例用法
# relayContractAddress = '0x1234567890abcdef1234567890abcdef12345678'  # 替换为搬运工智能合约地址
# relayContractAbi = [...]  # 替换为搬运工智能合约 ABI
