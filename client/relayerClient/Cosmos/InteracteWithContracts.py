from web3 import Web3


w3 = Web3(Web3.HTTPProvider('http://192.168.1.2:8545'))


# Configure w3, e.g., w3 = Web3(...)
address = '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F988'
abi = '[{"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"address","name":"minter_","type":"address"},...'
contract_instance = w3.eth.contract(address=address, abi=abi)

# read state:
contract_instance.functions.storedValue().call()
# 42

# update state:
tx_hash = contract_instance.functions.updateValue(43).transact()

# bytes 传 b'\xab\x00\x00\x00'

deployed_contract.functions.update({'s1': ['0x0000000000000000000000000000000000000001', '0x0000000000000000000000000000000000000002'], 's2': [b'0'*32, b'1'*32], 'users': []}).transact()
