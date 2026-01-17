// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.0;

import "./Types.sol";
import "./RLPEncode.sol";

library Helper {
    //每个以太坊信标链epoch包含的slot数量，固定为32
    uint256 public constant SLOTS_PER_EPOCH = 32;
    //每个同步委员会周期包含的epoch数量，固定为256
    uint256 public constant EPOCHS_PER_SYNC_COMMITTEE_PERIOD = 256;

    //根据指定的slot计算同步委员会周期
    function compute_sync_committee_period(uint256 _slot) internal pure returns (uint256){
        //通过 slot 编号依次除以 “每个 epoch 的 slot 数” 和 “每个周期的 epoch 数”，得到周期序号（整数除法，向下取整）
        return _slot / SLOTS_PER_EPOCH / EPOCHS_PER_SYNC_COMMITTEE_PERIOD;
    }

    //根据区块头数据（Types.BlockHeader类型），通过 RLP 编码 + Keccak256 哈希生成区块哈希。
    function getBlockHash(Types.BlockHeader memory _header)
    internal
    pure
    returns (bytes32)
    {
        uint256 len = 16;
        if (_header.withdrawalsRoot != bytes32(0)) {
            len = 17;
        }
        bytes[] memory list = new bytes[](len);
        list[0] = RLPEncode.encodeBytes(abi.encodePacked(_header.parentHash));
        list[1] = RLPEncode.encodeBytes(abi.encodePacked(_header.sha3Uncles));
        list[2] = RLPEncode.encodeAddress(_header.miner);
        list[3] = RLPEncode.encodeBytes(abi.encodePacked(_header.stateRoot));
        list[4] = RLPEncode.encodeBytes(abi.encodePacked(_header.transactionsRoot));
        list[5] = RLPEncode.encodeBytes(abi.encodePacked(_header.receiptsRoot));
        list[6] = RLPEncode.encodeBytes(_header.logsBloom);
        list[7] = RLPEncode.encodeUint(_header.difficulty);
        list[8] = RLPEncode.encodeUint(_header.number);
        list[9] = RLPEncode.encodeUint(_header.gasLimit);
        list[10] = RLPEncode.encodeUint(_header.gasUsed);
        list[11] = RLPEncode.encodeUint(_header.timestamp);
        list[12] = RLPEncode.encodeBytes(_header.extraData);
        list[13] = RLPEncode.encodeBytes(abi.encodePacked(_header.mixHash));
        list[14] = RLPEncode.encodeBytes(_header.nonce);
        list[15] = RLPEncode.encodeUint(_header.baseFeePerGas);
        if (_header.withdrawalsRoot != bytes32(0)) {
            list[16] = RLPEncode.encodeBytes(abi.encodePacked(_header.withdrawalsRoot));
        }
        return keccak256(RLPEncode.encodeList(list));
    }

    //将交易收据数据（Types.TxReceipt类型）编码为 RLP 格式（兼容以太坊收据标准）
    function encodeReceipt(Types.TxReceipt memory _txReceipt)
    internal
    pure
    returns (bytes memory output)
    {
        bytes[] memory list = new bytes[](4);
        list[0] = RLPEncode.encodeBytes(_txReceipt.postStateOrStatus);
        list[1] = RLPEncode.encodeUint(_txReceipt.cumulativeGasUsed);
        list[2] = RLPEncode.encodeBytes(_txReceipt.bloom);
        bytes[] memory listLog = new bytes[](_txReceipt.logs.length);
        bytes[] memory loglist = new bytes[](3);
        for (uint256 j = 0; j < _txReceipt.logs.length; j++) {
            loglist[0] = RLPEncode.encodeAddress(_txReceipt.logs[j].addr);
            bytes[] memory loglist1 = new bytes[](
                _txReceipt.logs[j].topics.length
            );
            for (uint256 i = 0; i < _txReceipt.logs[j].topics.length; i++) {
                loglist1[i] = RLPEncode.encodeBytes(
                    _txReceipt.logs[j].topics[i]
                );
            }
            loglist[1] = RLPEncode.encodeList(loglist1);
            loglist[2] = RLPEncode.encodeBytes(_txReceipt.logs[j].data);
            listLog[j] = RLPEncode.encodeList(loglist);
        }
        list[3] = RLPEncode.encodeList(listLog);
        output = RLPEncode.encodeList(list);
        if (_txReceipt.receiptType != 0) {
            output = abi.encodePacked(uint8(_txReceipt.receiptType), output);
        }
    }
    //从输入字节数组中截取指定起始位置和长度的片段。
    function getBytesSlice(bytes memory _b, uint256 _start, uint256 _length)
    internal
    pure
    returns (bytes memory) {
        require(_b.length > _start + _length - 1, "invalid bytes length");
        bytes memory out = new bytes(_length);

        for (uint256 i = 0; i < _length; i++) {
            out[i] = _b[_start + i];
        }

        return out;
    }
}