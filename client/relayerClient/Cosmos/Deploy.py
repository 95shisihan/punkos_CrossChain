from foundrycli import foundry_cli
import time
import sys
import json
import clientWithProtobuf
from web3 import Web3

private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
target_rpc_url = 'http://127.0.0.1:8545'
with open('client/relaycontract.json','r') as result_file:
        save_dict = json.load(result_file)
relay_contract_address = save_dict['deployedTo']
def deployRelayContract():
    relay_contract_path = 'src/TM_RelayContract.sol:TM_RelayContract'
    global relay_contract_address
    res = foundry_cli(f'forge create {relay_contract_path} --rpc-url {target_rpc_url} --private-key {private_key}')
    relay_contract_address = res['deployedTo']
    with open('client/relaycontract.json','w') as result_file:
        json.dump(res, result_file)
def submitGenesis(trust_height):
    encoded_ConsensusState_bytes_trust = clientWithProtobuf.get_encoded_initial_clientState_bytes_at_height(trust_height)
    paramsBytes = clientWithProtobuf.get_params_bytes(trust_height, encoded_ConsensusState_bytes_trust)
    res = foundry_cli(f'cast send {relay_contract_address} "setGenesisByUnion(bytes,bytes)" {Web3.to_hex(encoded_ConsensusState_bytes_trust)} {Web3.to_hex(paramsBytes)} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def startRelayer(trust_height):
    print(trust_height)
    height = trust_height + 1
    encoded_TmHeader_bytes = clientWithProtobuf.get_encoded_TmHeader_bytes_at_height(trust_height,height)
    res = foundry_cli(f'cast send {relay_contract_address} "submitNewHeaderByRelayer(bytes)" {Web3.to_hex(encoded_TmHeader_bytes)} --rpc-url {target_rpc_url} --private-key {private_key}')
    print(res)
def testRelayClient(trust_height):
    h = 0
    while True:
        try:
            startRelayer(trust_height+h)
            h += 1
        except Exception as e:
            print("错误：",e)
            time.sleep(5)    
if __name__ == "__main__":
    #print(sys.argv[1])
    if sys.argv[1]=='1':
        print("目前不支持RPC连接")
    elif sys.argv[1]=='0': 
        deployRelayContract()
        trust_height = 16828912
        #submitGenesis(trust_height)
        #testRelayClient(trust_height)
    else:
        print("输入参数错误")

