from foundrycli import foundry_cli
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
import json
import requests
import hashlib
import json
import binascii
from cryptos import *
from web3 import Web3

from bitcoinlib.services.bitcoind import BitcoindClient
from bitcoinlib.transactions import *

from foundrycli import foundry_cli


bdc = BitcoindClient(base_url='http://bob:bob@localhost:18334')
#print("Current blockheight is %d" % bdc.proxy.getblockcount())
#blockhash = bdc.proxy.getblockchaininfo()
#blockhash = bdc.proxy.getbestblockhash()
#blockhash = bdc.proxy.listunspent()
#print(blockhash)
#bestblock = bdc.proxy.getblock(blockhash)
#blockhash = bdc.proxy.generate(91)
res = bdc.proxy.listunspent()
print(res)
txid='16ed68eb9785779346098e59d32e9c2c716feecf0359dbd6f5051de22bab09d4'
vout=0
address='mymhZsG8GJxY7eKpRFMTVfW8pj8Ukui46k'
input = Input(prev_txid=txid,output_n=0)
print(input)
output=Output(value=4999900000,address=address,network='testnet')
print(output)
tx=Transaction(inputs=[input],outputs=[output]).raw_hex()
print(tx)

#input="[{'txid':'16ed68eb9785779346098e59d32e9c2c716feecf0359dbd6f5051de22bab09d4','vout':0}]"
#output="{'mymhZsG8GJxY7eKpRFMTVfW8pj8Ukui46k':49.99}"
#rawtx="0200000001d409ab2be21d05f5d6db5903cfee6f712c9c2ed3598e094693778597eb68ed160000000000ffffffff01c0aff629010000001976a914c83c35b2a7448ecb24603f4b45089257f050ce0288ac00000000"
signtx = bdc.proxy.signrawtransaction(tx)['hex']
res = bdc.proxy.sendrawtransaction(signtx)
print(res)