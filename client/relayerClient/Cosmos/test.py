import base64
import hashlib
import proto.TendermintLight_pb2 as tm

import hashlib
import base58

def calculate_cosmos_address(public_key):
    # 解码 Base64 编码的公钥为二进制格式
    decoded_public_key = base64.b64decode(public_key)

    # 计算公钥的 SHA256 哈希值
    hashed_public_key = hashlib.sha256(decoded_public_key).digest()

    # 计算 SHA256 哈希值的 RIPEMD160 哈希值
    ripemd160_hash = hashlib.new('ripemd160')
    ripemd160_hash.update(hashed_public_key)
    hashed_ripemd160 = ripemd160_hash.digest()

    # 添加地址前缀并进行 Base58 编码
    cosmos_address = "cosmos" + base58.b58encode(hashed_ripemd160).decode()

    return cosmos_address

print(calculate_cosmos_address("LtiHVLCcE+oFII0vpIl9mfkGDmk9BpPg1eUkvKnO4xw="))

# prefix = bytes.fromhex("000a220a20")
ed25519_28 = [119,198,146,235,33,246,5,2,212,34,21,243,254,119,90,111,118,160,155,161,114,56,69,34,19,77,229,243,106,160,4,208]
# backfix = bytes.fromhex("1086f5da04")
# print(backfix.hex())
# byte_array = prefix + bytes(integer_list)


simpleValidator = tm.SimpleValidator()

simpleValidator.pub_key.ed25519 = bytes(ed25519_28)
simpleValidator.voting_power = 100000
res  = simpleValidator.SerializeToString()
print("ed25519_28: " + bytes(ed25519_28).hex())
print("ed25519_28 SerializeDString: " + res.hex())

leafPrefix = b'\x00'
hash_object = hashlib.sha256(leafPrefix + res)
hash_value = hash_object.digest()

print("output hash: " + hash_value.hex())


validatorset_hash = [18,158,139,169,58,185,247,69,87,175,61,30,24,13,132,76,219,211,187,70,244,141,214,35,173,8,84,175,121,103,254,242]
print("validatorset_hash: " + bytes(validatorset_hash).hex())

evidence_hash = [227,176,196,66,152,252,28,20,154,251,244,200,153,111,185,36,39,174,65,228,100,155,147,76,164,149,153,27,120,82,184,85]
print("evidence_hash: " + bytes(evidence_hash).hex())

cosmos_address = calculate_cosmos_address(base64.b64encode(bytes(ed25519_28)))
print("cosmos_address: " + cosmos_address)

print("-----\n")

hash_object = hashlib.sha256(b"")
hash_value = hash_object.digest()
print("empty_hash: " +hash_value.hex())
expect_res = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
print("expect_res: " + expect_res)

print("-----\n")

simpleValidator = tm.SimpleValidator()

simpleValidator.pub_key.ed25519 = bytes(ed25519_28)
simpleValidator.voting_power = 100000
res  = simpleValidator.SerializeToString()
print("ed25519_28: " + bytes(ed25519_28).hex())
print("ed25519_28 SerializeDString: " + res.hex())

leafPrefix = b'\x00'
hash_object = hashlib.sha256(leafPrefix + res)
hash_value = hash_object.digest()

print("output hash: " + hash_value.hex())


validatorset_hash = [18,158,139,169,58,185,247,69,87,175,61,30,24,13,132,76,219,211,187,70,244,141,214,35,173,8,84,175,121,103,254,242]
print("validatorset_hash: " + bytes(validatorset_hash).hex())

evidence_hash = [227,176,196,66,152,252,28,20,154,251,244,200,153,111,185,36,39,174,65,228,100,155,147,76,164,149,153,27,120,82,184,85]
print("evidence_hash: " + bytes(evidence_hash).hex())
