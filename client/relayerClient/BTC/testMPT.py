#from web3 import Web3
#from trie import HexaryTrie
#import rlp
#import requests
#import json
#w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
#block = w3.eth.get_block('latest')
#print(block.number)
#print(block.transactionsRoot)
#print(block.receiptsRoot)
from bitcoinlib.services.bitcoind import BitcoindClient
from bitcoinlib.transactions import *
from foundrycli import foundry_cli
bdc = BitcoindClient(base_url='http://gyf:gyf@localhost:18443')
#print("Current blockheight is %d" % bdc.proxy.getblockcount())
blockhash = bdc.proxy.getbestblockhash()
bestblock = bdc.proxy.getblock(blockhash)
ct = len(bestblock['tx'])
rpc_url = 'http://127.0.0.1:8545'
with open('./client/infoBTC.json','r') as result_file:
    save_dict = json.load(result_file)
relay_contract_address = save_dict['deployedTo']
rt = '0100000001c997a5e56e104102fa209c6a852dd90660a20b2d9c352423edce25857fcd3704000000004847304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901ffffffff0200ca9a3b00000000434104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac00286bee0000000043410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac00000000'
#print(double_sha256(to_bytes(rt),True))
t = Transaction.parse_hex(rt)
#print(t)
#print(t.version)
#print(t.inputs)
print(t.outputs)
#print(t.locktime)
#print(to_bytes(t.inputs))
#txid = '763979d0bd2311041fdcb81edddb1a19983a2b83f5ff7ec06d6c8e4d7d31085a'
#res = foundry_cli(f'cast call {relay_contract_address} "testHashTx(bytes)(bytes32)" {rt} --rpc-url {rpc_url}')
res = foundry_cli(f'cast call {relay_contract_address} "parseTx(bytes,uint)(bytes)" {rt} {1} --rpc-url {rpc_url}')
print(res)





