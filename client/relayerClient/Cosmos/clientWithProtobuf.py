import proto.TendermintLight_pb2 as pb2
import proto.any_pb2 as any_pb2
import getCosmosData

def get_encoded_initial_clientState(height):
    clientSate = pb2.ClientState()
    # string chain_id = 1;
    clientSate.chain_id = "cosmoshub-4"

    # Fraction trust_level = 2;
    trust_level = pb2.Fraction()
    trust_level.numerator = 1
    trust_level.denominator = 3
    clientSate.trust_level.CopyFrom(trust_level)

    # Duration trusting_period = 3;
    trusting_period = pb2.Duration()
    trusting_period.seconds = 100000000000
    trusting_period.nanos = 0
    clientSate.trusting_period.CopyFrom(trusting_period)

    # Duration unbonding_period = 4;
    unbonding_period = pb2.Duration()
    unbonding_period.seconds = 100000000000
    unbonding_period.nanos = 0
    clientSate.unbonding_period.CopyFrom(unbonding_period)

    # Duration max_clock_drift = 5;
    max_clock_drift = pb2.Duration()
    max_clock_drift.seconds = 100000000000
    max_clock_drift.nanos = 0
    clientSate.max_clock_drift.CopyFrom(max_clock_drift)

    # int64 frozen_height = 6;
    clientSate.frozen_height = 0

    # int64 latest_height = 7;
    clientSate.latest_height = height

    # bool allow_update_after_expiry = 8;
    clientSate.allow_update_after_expiry = True

    # bool allow_update_after_misbehaviour = 9;
    clientSate.allow_update_after_misbehaviour = True

    return clientSate


def get_encoded_ConsensusState(lightheader, ConsensusState_hash):
    consensusState = pb2.ConsensusState()

    # Timestamp timestamp = 1;
    timestamp = pb2.Timestamp()
    timestamp.seconds = lightheader['time']['seconds']
    timestamp.nanos = lightheader['time']['nanos']
    consensusState.timestamp.CopyFrom(timestamp)

    # MerkleRoot root = 2;
    root = pb2.MerkleRoot()
    root.hash = ConsensusState_hash
    consensusState.root.CopyFrom(root)

    # bytes next_validators_hash = 3;
    consensusState.next_validators_hash = lightheader['next_validators_hash']

    return consensusState

def get_encoded_TmHeader(signed_header, validator_set, trusted_height, trusted_validators): 
    TmHeader = pb2.TmHeader()

  # SignedHeader signed_header = 1;
    TmHeader.signed_header.CopyFrom(signed_header)

  # ValidatorSet validator_set = 2;
    TmHeader.validator_set.CopyFrom(validator_set)

  # int64 trusted_height = 3;
    TmHeader.trusted_height = trusted_height

  # ValidatorSet trusted_validators = 4;
    TmHeader.trusted_validators.CopyFrom(trusted_validators)

    return TmHeader

def get_encoded_SignedHeader(header, commit):
    signed_header = pb2.SignedHeader()

  # Header header = 1;
    signed_header.header.CopyFrom(header)

  # Commit commit = 2;
    signed_header.commit.CopyFrom(commit)

    return signed_header


def get_encode_LightHeader(lightheader):
    LightHeader = pb2.LightHeader()

    # Consensus version  = 1;
    version = pb2.Consensus()
    version.block = lightheader['version']['block']
    version.app = lightheader['version']['app']
    LightHeader.version.CopyFrom(version)

    # string chain_id = 2;
    LightHeader.chain_id = lightheader['chain_id']

    # int64 height = 3;
    LightHeader.height = lightheader['height']
    
    # Timestamp time = 4;
    time = pb2.Timestamp()
    time.seconds = lightheader['time']['seconds']
    time.nanos = lightheader['time']['nanos']
    LightHeader.time.CopyFrom(time)

    # BlockID last_block_id = 5;
    last_block_id = pb2.BlockID()
    last_block_id.hash = lightheader['last_block_id']['hash']

    partSetHeader = pb2.PartSetHeader()
    partSetHeader.total = lightheader['last_block_id']['parts']['total']
    partSetHeader.hash = lightheader['last_block_id']['parts']['hash']
    last_block_id.part_set_header.CopyFrom(partSetHeader)
    LightHeader.last_block_id.CopyFrom(last_block_id)

    # bytes last_commit_hash = 6;  // commit from validators from the last block
    LightHeader.last_commit_hash = lightheader['last_commit_hash']
    
    # bytes data_hash = 7;  // transactions
    LightHeader.data_hash = lightheader['data_hash']

    # bytes validators_hash = 8;   // validators for the current block
    LightHeader.validators_hash = lightheader['validators_hash']
    
    # bytes next_validators_hash = 9;   // validators for the next block
    LightHeader.next_validators_hash = lightheader['next_validators_hash']
    
    # bytes consensus_hash = 10;  // consensus params for current block
    LightHeader.consensus_hash = lightheader['consensus_hash']
    
    # bytes app_hash = 11;  // state after txs from the previous block
    LightHeader.app_hash = lightheader['app_hash']
    
    # bytes last_results_hash = 12;  // root hash of all results from the txs from the previous block
    LightHeader.last_results_hash = lightheader['last_results_hash']
    
    # bytes evidence_hash = 13;  // evidence included in the block
    LightHeader.evidence_hash = lightheader['evidence_hash']
    
    # bytes proposer_address = 14;  // original proposer of the block
    LightHeader.proposer_address = lightheader['proposer_address']

    return LightHeader

def get_encoded_Commit(commit):
    Commit = pb2.Commit()

    # int64 height = 1;
    Commit.height = commit['height']

    # Round round = 2;
    Commit.round = commit['round']

    # BlockID block_id = 3;
    block_id = pb2.BlockID()
    block_id.hash = commit['block_id']['hash']

    partSetHeader = pb2.PartSetHeader()
    partSetHeader.total = commit['block_id']['parts']['total']
    partSetHeader.hash = commit['block_id']['parts']['hash']
    block_id.part_set_header.CopyFrom(partSetHeader)
    Commit.block_id.CopyFrom(block_id)

    # repeated CommitSig signatures = 4;
    
    for signature in commit['signatures']:
        CommitSig = pb2.CommitSig()
        CommitSig.block_id_flag = signature['block_id_flag']
        CommitSig.validator_address = signature['validator_address']

        timestamp = pb2.Timestamp()
        timestamp.seconds = signature['timestamp']['seconds']
        timestamp.nanos = signature['timestamp']['nanos']
        CommitSig.timestamp.CopyFrom(timestamp)

        CommitSig.signature = signature['signature']
        Commit.signatures.extend([CommitSig])

    return Commit


def get_encoded_ValidatorSet(validator_set):
    ValidatorSet = pb2.ValidatorSet()

    # repeated Validator validators = 1;
    for validator in validator_set['validators']:
        encode_Validator = get_encode_Validator(validator)
        ValidatorSet.validators.extend([encode_Validator])

    # Validator proposer = 2;
    encode_Validator = get_encode_Validator(validator_set['proposer'])
    ValidatorSet.proposer.CopyFrom(encode_Validator)

    # int64 total_voting_power = 2;
    ValidatorSet.total_voting_power = validator_set['total_voting_power']

    return ValidatorSet


def get_encode_Validator(validator):
    Validator = pb2.Validator()

    # bytes address = 1;
    Validator.address = validator['address']

    # PublicKey pub_key = 2;
    PublicKey = pb2.PublicKey()
    PublicKey.ed25519 = validator['pub_key']['value']
    Validator.pub_key.CopyFrom(PublicKey)

    # int64 voting_power = 3;
    Validator.voting_power = validator['voting_power']

    # int64 proposer_priority = 4;
    Validator.proposer_priority = validator['proposer_priority']

    return Validator




def get_serialized_string(value, type_url):
    any = any_pb2.Any()
    any.value = value.SerializeToString()
    any.type_url = type_url
    return any.SerializeToString()


def get_encoded_initial_clientState_bytes_at_height(height):
    clientSate = get_encoded_initial_clientState(height)
    return get_serialized_string(clientSate, "/tendermint.types.ClientState")


def get_encoded_ConsensusState_bytes_at_height(height):
    signed_header, ok = getCosmosData.getSignedHeader(height)
    lightheader = getCosmosData.toLightHeader(signed_header["header"])
    commit = getCosmosData.toCommit(signed_header["commit"])
    ConsensusState_hash = commit["block_id"]["hash"]
    consensusState = get_encoded_ConsensusState(lightheader, ConsensusState_hash)
    return get_serialized_string(consensusState, "/tendermint.types.ConsensusState")

def get_encoded_TmHeader_bytes_at_height(trust_height, height):
    signed_header, ok = getCosmosData.getSignedHeader(height)
    lightHeader = getCosmosData.toLightHeader(signed_header["header"])
    encoded_lightHeader = get_encode_LightHeader(lightHeader)
    commit = getCosmosData.toCommit(signed_header["commit"])
    encoded_Commit = get_encoded_Commit(commit)
    encoded_SignedHeader = get_encoded_SignedHeader(encoded_lightHeader, encoded_Commit)

    validators, ok = getCosmosData.getValidators(height)
    validator_set = getCosmosData.toValidatorSet(validators, lightHeader["proposer_address"])
    encoded_ValidatorSet = get_encoded_ValidatorSet(validator_set)

    trusted_height = trust_height

    signed_header, ok = getCosmosData.getSignedHeader(trusted_height)
    lightHeader = getCosmosData.toLightHeader(signed_header["header"])
    validators, ok = getCosmosData.getValidators(trusted_height)
    validator_set = getCosmosData.toValidatorSet(validators, lightHeader["proposer_address"])
    trusted_validators = get_encoded_ValidatorSet(validator_set)
    
    TmHeader = get_encoded_TmHeader(encoded_SignedHeader, encoded_ValidatorSet, trusted_height, trusted_validators)
    return get_serialized_string(TmHeader, "/tendermint.types.TmHeader")
    
def get_params_bytes(height, clientStateBytes):
    bytes8 = height.to_bytes(8, byteorder='big')
    return bytes8 + clientStateBytes

if __name__ == "__main__":
    trust_height = 16828912
    height = 16828913
    clientStateBytes = get_encoded_initial_clientState_bytes_at_height(trust_height)
    print("initial_clientState_bytes: \n" + clientStateBytes.hex())
    consensusStateBytes = get_encoded_ConsensusState_bytes_at_height(trust_height)
    print("encoded_ConsensusState_bytes_trust: \n" + consensusStateBytes.hex())
    consensusStateBytes = get_encoded_ConsensusState_bytes_at_height(height)
    print("encoded_ConsensusState_bytes: \n" + consensusStateBytes.hex())
    TmHeaderBytes = get_encoded_TmHeader_bytes_at_height(trust_height,height)
    print("encoded_TmHeader_bytes: \n" + TmHeaderBytes.hex())
    paramsBytes = get_params_bytes(trust_height, clientStateBytes)
    print("params_bytes: \n" + paramsBytes.hex())