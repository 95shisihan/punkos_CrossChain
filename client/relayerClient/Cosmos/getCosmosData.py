import requests
import json
from base64 import b64decode
from datetime import datetime
from dateutil.parser import isoparse


rpc_poxy = "https://rpc-cosmoshub.mms.team/"
headers = {"accept": "application/json"}
s = requests.session()


def getTimestamp(timestamp):
    dt = isoparse(timestamp)
    seconds = int(dt.timestamp())
    nanoseconds = int(timestamp.split('.')[1].rstrip('Z')) * 10**(9 - len(timestamp.split('.')[1].rstrip('Z')))
    return seconds, nanoseconds


def toLightHeader(header):
    header["version"]["block"] = int(header["version"].get("block", 0))
    header["version"]["app"] = int(header["version"].get("app", 0))
    header["height"] = int(header["height"])
    seconds, nanos = getTimestamp(header["time"])
    header["time"] = {"seconds": seconds, "nanos": nanos}
    header["last_block_id"]["hash"] = bytes.fromhex(header["last_block_id"]["hash"])
    header["last_block_id"]["parts"]["total"] = int(
        header["last_block_id"]["parts"].get("total", 0)
    )
    header["last_block_id"]["parts"]["hash"] = bytes.fromhex(
        header["last_block_id"]["parts"]["hash"]
    )

    for key in header:
        if "hash" in key or "address" in key:
            header[key] = bytes.fromhex(header[key])

    return header


def toCommit(commit):
    commit["height"] = int(commit.get("height", 0))
    commit["round"] = int(commit.get("round", 0))
    commit["block_id"]["hash"] = bytes.fromhex(commit["block_id"]["hash"])
    commit["block_id"]["parts"]["total"] = int(
        commit["block_id"]["parts"].get("total", 0)
    )
    commit["block_id"]["parts"]["hash"] = bytes.fromhex(
        commit["block_id"]["parts"]["hash"]
    )
    for i in range(len(commit["signatures"])):
        commit["signatures"][i]["block_id_flag"] = int(
            commit["signatures"][i]["block_id_flag"]
        )
        
        
        if commit["signatures"][i]["block_id_flag"] != 1:
            commit["signatures"][i]["signature"] = b64decode(
                commit["signatures"][i]["signature"]
            )
            commit["signatures"][i]["validator_address"] = bytes.fromhex(
            commit["signatures"][i]["validator_address"]
        )
            seconds, nanos = getTimestamp(commit["signatures"][i]["timestamp"])
            commit["signatures"][i]["timestamp"] = {"seconds": seconds, "nanos": nanos}
        else:
            commit["signatures"][i]["signature"] = bytes()
            commit["signatures"][i]["validator_address"] = bytes()
            commit["signatures"][i]["timestamp"] = {"seconds": 0, "nanos": 0}

    return commit


def toValidatorSet(validators, proposer_addr):
    validator_set = {"proposer": None}
    total_voting_power = 0
    for i in range(len(validators)):
        validators[i]["address"] = bytes.fromhex(validators[i]["address"])
        validators[i]["pub_key"]["type"] = validators[i]["pub_key"]["type"]
        validators[i]["pub_key"]["value"] = b64decode(validators[i]["pub_key"]["value"])
        #print(validators[i]["pub_key"]["value"].hex())
        validators[i]["voting_power"] = int(validators[i]["voting_power"])
        validators[i]["proposer_priority"] = int(validators[i]["proposer_priority"])
        total_voting_power += validators[i]["voting_power"]
        if validators[i]["address"] == proposer_addr:
            validator_set["proposer"] = validators[i]

    validator_set["validators"] = validators
    validator_set["total_voting_power"] = total_voting_power

    return validator_set


def getBlock(height):
    response = s.get(rpc_poxy + f"block?height={height}", headers=headers)
    ok = False
    if response.status_code == 200:
        ok = True
        result_data = response.json()["result"]
        block = result_data["block"]
        return block, ok
    else:
        print(f"Request failed with status code {response.status_code}")
        return None, ok


def getSignedHeader(height):
    response = s.get(rpc_poxy + f"commit?height={height}", headers=headers)
    ok = False
    if response.status_code == 200:
        ok = True
        result_data = response.json()["result"]
        signed_header = result_data["signed_header"]
        return signed_header, ok
    else:
        print(f"Request failed with status code {response.status_code}")
        return None, ok


def getValidators(height):
    response = s.get(rpc_poxy + f"validators?height={height}&page=1&per_page=100", headers=headers)
    ok = False
    validators = []
    if response.status_code == 200:
        ok = True
        result_data = response.json()["result"]
        total = int(result_data["total"])
        page = 1
        while total > 0:
            response = s.get(rpc_poxy + f"validators?height={height}&page={page}&per_page=100", headers=headers)
            result_data = response.json()["result"]
            validators.extend(result_data["validators"]) 
            total -= 100
            page += 1
        
        print(len(validators))
        return validators, ok
    else:
        print(f"Request failed with status code {response.status_code}")
        return None, ok


if __name__ == "__main__":
    signed_header, ok = getSignedHeader(16828913)
    # signed_header, ok = getSignedHeader(8619997)
    #print(signed_header)
    lightheader = toLightHeader(signed_header["header"])
    commit = toCommit(signed_header["commit"])
    validators, ok = getValidators(16828913)
    print(lightheader["proposer_address"].hex())
    validator_set = toValidatorSet(validators, lightheader["proposer_address"])
    print(validator_set['proposer']['address'].hex())