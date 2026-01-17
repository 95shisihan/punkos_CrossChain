from bitcoinrpc.authproxy import AuthServiceProxy
import requests
from bitcoinlib.services.bitcoind import BitcoindClient
from cryptos import *
from web3 import Web3
from foundrycli import foundry_cli
import json
from ..HUB.General_Plugin import GeneralSourcePlugin
class BitcoinPlugin(GeneralSourcePlugin):
    def __init__(self,mainnet_or_regtest:int,api_or_rpc:int,privateDataPath:str):
        chainTypes = ['Mainnet','Regtest']
        self.chainType = chainTypes[mainnet_or_regtest]
        self.name = 'Bitcoin'
        self.fullName = self.name + ' ' + self.chainType
        self.symbol = 'BTC'
        if api_or_rpc == 0:
            self.rpc = None
        else:
            with open(privateDataPath,'r') as result_file:
                save_dict = json.load(result_file)
            source_rpc = save_dict['bitcoinRPC'][self.fullName]
            source_rpc_user = source_rpc['user']
            source_rpc_password = source_rpc['password']
            source_rpc_host = source_rpc['host']
            source_rpc_port = source_rpc['port']
            self.rpc = setRPCConnection(source_rpc_user,source_rpc_password,source_rpc_host,source_rpc_port)
    @staticmethod
    def setRPCConnection(user,password,host,port)-> AuthServiceProxy:
        #rpc_connection = AuthServiceProxy(f"http://{user}:{password}@{host}:{port}")
        return BitcoindClient(base_url=f"http://{user}:{password}@{host}:{port}").proxy
    def getTopBlockHeight(self) -> int:
        if self.rpc == None:
            return getTopBlockHeight_API()
        else:
            return getTopBlockHeight_RPC(self.rpc)
    def getBlockHeaderByHeight(self,height:int) -> tuple[str,str]:
        if self.rpc == None:
            return getBlockHeaderFromHeight_API(height)
        else:
            return getBlockHeaderFromHeight_RPC(self.rpc,height)
    def getGenesisHeight(self) -> int:
        if self.chainType == 'Regtest':
            return 0
        else:
            topHeight = self.getTopBlockHeight()
            genesisHeight = topHeight - topHeight % 2016
            return (genesisHeight)
    def getGenesisData(self) -> tuple[str,str]:
        heightGenesis = self.getGenesisHeight()
        hashGenesis,hexGenesis = self.getBlockHeaderByHeight(heightGenesis)
        genesisParams = foundry_cli(f'cast --to-uint256 {heightGenesis}')
        return hexGenesis,genesisParams
    def getTxListByBlockHash(self,blockHash) -> tuple[str,list]:
        """
        Query the root and all leaf nodes of a tx merkle tree.

        Args:
            blockHash: the hash of the BTC block
        
        Returns: 
            hashMerkleRoot: hash of the tx merkle tree root recorded by block header
            txList: list of txids of all txs recorded by block body
        """
        if self.rpc == None:
            return getTxListFromHash_API(blockHash)
        else:
            return getTxListFromHash_RPC(self.rpc,blockHash)
    def getRawTxByTxId(self,txid:str,verbose:bool) -> tuple[bool,Union[dict,str]]:
        """
        Query the detailed infomation of a tx.
        
        Args:
            txid: the txid of transaction
            verbose: set true for json tx while false for hex-encoded tx

        Returns:
            data: a JSON string of tx detailed infomation or a hex string of rawTx
        """
        if self.rpc == None:
            return (False,"Bitcoin Plugin Offchain ERROR: getRawTxByTxid: Don't Support API !")
        else:
            return getRawTxFromHash_RPC(self.rpc,txid,verbose)
    def generateTxProof(self,keyHeader,keyTx) -> tuple[str,str,str]:
        if isinstance(keyHeader,int):
            heightHeader = keyHeader
            (hashHeader,hexHeader) = self.getBlockHeaderByHeight(heightHeader)
        else:
            hashHeader = keyHeader
            (txRoot,txList) = self.getTxListByBlockHash(hashHeader)
        if isinstance(keyTx,int):
            indexTx = keyTx
        else:
            hashTx = keyTx
            indexTx = txList.index(hashTx)
        txHash,merkleProof = compactTxProof(txRoot,txList,indexTx)
        return (txHash,merkleProof,hashHeader)
    def sendRawTx(self,txid:str,rawTx:str) -> bool:
        if self.rpc == None:
            return False
        try:
            res = self.rpc.sendrawtransaction(rawTx)
            return (res == txid)
        except Exception as e:
            print("Bitcoin Plugin Onchain ERROR: sendRawTx: %s !" % e)
            return(False)
    def waitTxRecorded(self,txid:str)-> tuple[bool,str,int]:
        try:
            rawTx = self.getRawTxByTxId(txid,True)
            confirm = rawTx['confirmations']
            print("Confirmations of source tx %s is %d !" % (txid,confirm))
            if confirm == None:
                if self.chainType == 'Mainnet':
                    time.sleep(300)
                elif self.chainType == 'Regtest':
                    self.rpc.generate(1)
                else:
                    return (False,'',0)
                return self.waitTxRecorded(txid)
            else:
                return (True,rawTx['blockhash'],confirm)
        except Exception as e:
            print("Bitcoin Plugin Onchain ERROR: waitTxRecorded: %s !" % e)
            return(False,'',0)
    def waitNewBlock(self,blockNum: int) -> bool:
        try:
            currentHeight = self.getTopBlockHeight()
            targetHeight = currentHeight + blockNum
            if self.chainType == 'Mainnet':
                while (currentHeight <= targetHeight):
                    time.sleep(300)
                    currentHeight = self.getTopBlockHeight()
            elif self.chainType == 'Regtest':
                while (currentHeight <= targetHeight):
                    self.rpc.generate(1)
                    currentHeight = self.getTopBlockHeight()
            else:
                return False
            return True
        except Exception as e:
            print("Bitcoin Plugin Onchain ERROR: waitNewBlock: %s !" % e)
            return False
# 1: read or write data only from bitcoind rpc
# 1.1 read methods
def setRPCConnection(user,password,host,port):
        #rpc_connection = AuthServiceProxy(f"http://{user}:{password}@{host}:{port}")
        rpc_connection = BitcoindClient(base_url=f"http://{user}:{password}@{host}:{port}").proxy
        return rpc_connection
def getBlockHeaderFromHeight_RPC(rpc_connection: AuthServiceProxy, height: int):
    """
    向源链全节点查询某高度对应的区块头
    
    :param rpc_connection: 
    :param height: Block number

    :return hashBlock: 
    :return hexHeader:
    """
    hashBlock = rpc_connection.getblockhash(height)
    hexHeader = rpc_connection.getblockheader(hashBlock,False)
    return (hashBlock,hexHeader)
def getBlockHashFromHeight_RPC(rpc_connection,height):
    """
    向源链全节点查询某高度对应的区块哈希
    
    :param rpc_connection: 
    :type rpc_connection: BitcoindClient.proxy
    :param height: Block number
    :type height: int

    :return hashBlock: 
    """
    hashBlock = rpc_connection.getblockhash(height)
    return hashBlock
def getTopBlockHeight_RPC(rpc_connection):
    """
    向源链全节点查询主链高度
    
    返回值：
    最大高度
    """
    topHeight = rpc_connection.getblockchaininfo()['headers']
    return topHeight
def getGenesisHeight_RPC(rpc_connection):
    topHeight = getTopBlockHeight_RPC(rpc_connection)
    genesisHeight = topHeight - topHeight % 2016
    return (genesisHeight)
def getTxListFromHash_RPC(rpc_connection,blockHash):
    """
    向源链全节点查询某高度对应的区块头
    
    参数：
    h -- 区块高度

    返回值：
    默克尔根,交易列表
    """
    block = rpc_connection.getblock(blockHash)
    return (block['merkleroot'],block['tx'])

def getRawTxFromIndex_RPC(rpc_connection,blockHeight,txIndex):
    """
    测试时快速获取源链交易
    
    参数：
    blockHeight -- 区块高度
    txIndex --交易序号
    
    返回值：
    源交易
    """
    hashBlock = rpc_connection.getblockhash(blockHeight)
    hashTx = rpc_connection.getblock(hashBlock)['tx'][txIndex]
    return hashTx
def getRawTxFromHash_RPC(rpc_connection:AuthServiceProxy,txid:str,verbose:bool)-> tuple[bool,Union[dict,str]]:
    """
    向源链全节点查询交易哈希对应的区块头
    
    参数：
    txHash -- 交易哈希

    返回值：
    默克尔根,交易列表
    """
    try:
        res = rpc_connection.getrawtransaction(txid,verbose)
        return (True,res)
    except Exception as e:
        return (False,e)

def generateTxProof_RPC(rpc_connection,keyHeader,keyTx):
    try:
        if isinstance(keyHeader,int):
            heightHeader = keyHeader
            hashHeader = getBlockHashFromHeight_RPC(rpc_connection,heightHeader)
        else:
            hashHeader = keyHeader
        (txRoot,txList) = getTxListFromHash_RPC(rpc_connection,hashHeader)
        if isinstance(keyTx,int):
            indexTx = keyTx
        else:
            hashTx = keyTx
            indexTx = txList.index(hashTx)
        txHash,merkleProof = compactTxProof(txRoot,txList,indexTx)
        return (txHash,merkleProof,hashHeader)
    except Exception as e:
        print(e)
# write methods
def sendRawTx(rpc_connection,rawTx):
    try:
        res = rpc_connection.sendrawtransaction(rawTx)
        return (True,res)
    except Exception as e:
        return (False,e)
#2: read data from blockchair.com
def getBlockHeaderFromHeight_API(height):
    """
    向区块链浏览器查询某高度对应的区块头
    
    参数：
    h -- 区块高度

    返回值：
    区块头
    """
    url = "https://api.blockchair.com/bitcoin/raw/block/"+str(height)
    response = requests.get(url)
    result = response.json()['data']
    if height == 0 :
        hashBlock = result[0]['decoded_raw_block']['hash']
        hexHeader = result[0]['raw_block'][0:160]
    else:
        hashBlock = result[str(height)]['decoded_raw_block']['hash']
        hexHeader = result[str(height)]['raw_block'][0:160]
    return (hashBlock,hexHeader)
def getBlockHashFromHeight_API(height):
    """
    向区块链浏览器查询某高度对应的区块哈希
    
    参数：
    height -- 区块高度

    返回值：
    区块哈希
    """
    url = "https://api.blockchair.com/bitcoin/raw/block/"+str(height)
    response = requests.get(url)
    result = response.json()['data']
    if height == 0 :
        return result[0]['decoded_raw_block']['hash']
    else:
        return result[str(height)]['decoded_raw_block']['hash']
def getTopBlockHeight_API():
    """
    向区块链浏览器查询主链高度

    返回值：
    最大高度
    """
    url = "https://api.blockchair.com/bitcoin/stats"
    response = requests.get(url)
    result = response.json()['data']
    return result['best_block_height']
def getGenesisHeight_API():
    topHeight = getTopBlockHeight_API()
    genesisHeight = topHeight - topHeight % 2016
    return (genesisHeight)
def getTxListFromHash_API(blockHash):
    url = "https://api.blockchair.com/bitcoin/raw/block/"+blockHash
    response = requests.get(url)
    result = response.json()['data'][blockHash]['decoded_raw_block']
    txRoot = result['merkleroot']
    txList = result['tx']   
    return (txRoot,txList)
def generateTxProof_API(keyHeader: Union[int,str], keyTx: Union[int,str]):
    try:
        if isinstance(keyHeader,int):
            heightHeader = keyHeader
            hashHeader = getBlockHashFromHeight_API(heightHeader)
        else:
            hashHeader = keyHeader
        (txRoot,txList) = getTxListFromHash_API(hashHeader)
        if isinstance(keyTx,int):
            indexTx = keyTx
        else:
            hashTx = keyTx
            indexTx = txList.index(hashTx)
        txHash,merkleProof = compactTxProof(txRoot,txList,indexTx)
        return (txHash,merkleProof,hashHeader)
    except Exception as e:
        print(e)
def getRawTxFromHash_API(txHash):
    url = "https://api.blockchair.com/bitcoin/raw/transaction/"+txHash
    response = requests.get(url)
    result = response.json()['data'][txHash]
    rawTx = result['raw_transaction']
    return rawTx
def getRawTxFromIndex_API(height,txIndex):
    """
    测试时快速获取源链交易
    
    参数：
    blockHeight -- 区块高度
    txIndex --交易序号
    
    返回值：
    源交易
    """
    url = "https://api.blockchair.com/bitcoin/raw/block/"+str(height)
    response = requests.get(url)
    result = response.json()['data']
    if height == 0 :
        txHash = result[0]['decoded_raw_block']['tx'][txIndex]
    else:
        txHash = result[str(height)]['decoded_raw_block']['tx'][txIndex]
    rawTx = getRawTxFromHash_API(txHash)
    return txHash,rawTx
#3: read data from bitcond RPC or blockchair API according to param
def getBlockHeaderFromHeight(rpc_connection: Union[None,AuthServiceProxy], height: int):
    if rpc_connection is None:
        return getBlockHeaderFromHeight_API(height)
    else:
        return getBlockHeaderFromHeight_RPC(rpc_connection,height)
def getBlockHashFromHeight(rpc_connection: Union[None,AuthServiceProxy], height: int):
    if rpc_connection is None:
        return getBlockHashFromHeight_API(height)
    else:
        return getBlockHashFromHeight_RPC(rpc_connection,height)
def getTopBlockHeight(rpc_connection: Union[None,AuthServiceProxy]) -> int:
    print("This is getTopBlockHeight!")
    if rpc_connection is None:
        return getTopBlockHeight_API()
    else:
        return getTopBlockHeight_RPC(rpc_connection)
def getTxListFromHash(rpc_connection,blockHash):
    if rpc_connection is None:
        return getTxListFromHash_API(blockHash)
    else:
        return getTxListFromHash_RPC(rpc_connection, blockHash)

#4: process bitcoin data off-chain
def generateTxProofFromListToStr(siblings):
    str=''
    if len(siblings) == 0:
        return (str)
    else:
        depth = len(siblings)    
    for i in range(depth):
        str = str + siblings[i]    
    return (str)
def compactTxProof(txRoot,txList,indexTx):
    tree = mk_merkle_proof(txRoot,txList,indexTx) 
    leafNode = foundry_cli(f'cast --to-uint256 {Web3.to_hex(indexTx)}')
    merkleProof = leafNode + generateTxProofFromListToStr(tree['siblings'])
    return tree['tx_hash'],merkleProof