// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "./RLPReader.sol";
import "forge-std/Script.sol";  
import {SourceConsensusRules as SCR} from "bridge-std/AbstractSourceRules.sol";

contract SEP_OLC is SCR {
    using RLPReader for bytes;
    using RLPReader for RLPReader.RLPItem;

    /// @notice 存储最新区块的区块哈希
    bytes32 private latestHash;

    // 添加存储上一个slot的变量
    uint256 private lastSlot;

    // 存储所有从RLP解析出的区块头参数
    struct BeaconParams {
        uint256 slot;
        uint256 proposerIndex; 
        bytes32 parentRoot;
        bytes32 stateRoot;
        bytes32 bodyRoot;
    }

    struct ExecParams {
        bytes32 parentHash;
        bytes32 uncleHash;
        address feeRecipient;
        bytes32 stateRoot;
        bytes32 receiptsRoot;
        bytes32 logsBloom;
        bytes32 difficulty;
        uint256 blockNumber;
        uint256 gasLimit;
        uint256 gasUsed;
        uint256 timestamp;
        bytes extraData;
        bytes32 baseFeePerGas;
        bytes32 blockHash;
    }

    BeaconParams private latestBeaconParams;
    ExecParams private latestExecParams;

    /// @notice 实现设置初始区块头接口
    function setGenesisShadowBlock(bytes calldata rawGenesisShadowBlock, bytes calldata params) 
        internal  
        override 
        returns(bool success) 
    {
        // 解码原始数据
        RLPReader.RLPItem[] memory items = rawGenesisShadowBlock.toRlpItem().toList();
        
        // 验证格式,如果无效返回false
        if(items.length != 2) {
            return false;
        }

        // 解析beacon和execution参数
        bytes memory beaconData = items[0].toBytes();
        bytes memory execData = items[1].toBytes();
        
        // 调用LightNode合约的初始化函数
        // 这里需要根据实际情况解析参数并传入
        // initialize(...);
        latestHash = getKeyFromShadowBlock(rawGenesisShadowBlock);
        lastSlot = abi.decode(params,(uint256));
        return true;
    }

    /// @notice 实现提交新区块头接口
    function submitNewShadowBlock(bytes calldata rawNewShadowBlock) 
        internal 
        override 
        returns(RelayerLabel relayerLabel, bytes32 keyPrevShadowBlock) 
    {
        console.log("Entering submitNewShadowBlock");
        // 解码原始数据
        RLPReader.RLPItem[] memory items = rawNewShadowBlock.toRlpItem().toList();
        console.log("Number of items in RLP:", items.length);
        // 验证格式,如果无效返回Invalid_Honest
        if(items.length != 2) {
            return (RelayerLabel.Dishonest, bytes32(0));
        }
        console.log("RLP format valid");
        // 解析beacon参数
        RLPReader.RLPItem[] memory beaconItems = items[0].toList();
        // ========== 调试日志4：Beacon层列表解码结果 ==========
        console.log("=== Beacon of RLP resulte ===");
        console.log("Beacon length  ", beaconItems.length);
        
        if(beaconItems.length < 5) {
            return (RelayerLabel.Dishonest, bytes32(0));
        }
        
        uint256 newSlot = beaconItems[0].toUint();
        console.log("New slot:", newSlot);
        // 检查slot连续性
        if(lastSlot != 0) {  // 不是第一次提交
            if(newSlot <= lastSlot) {  // slot重复或回退
                return (RelayerLabel.Invalid_Honest, bytes32(0));
            }
            //暂时先不处理跳过slot的情况，一般是认为出错的，现在不报错了
            else if (newSlot > lastSlot + 1){
                return (RelayerLabel.Dishonest, bytes32(0));
            }
        }
        
        // 更新状态变量
        latestBeaconParams.proposerIndex = beaconItems[1].toUint();
        latestBeaconParams.parentRoot = bytes32(beaconItems[2].toBytes());
        latestBeaconParams.stateRoot = bytes32(beaconItems[3].toBytes());
        latestBeaconParams.bodyRoot = bytes32(beaconItems[4].toBytes());

        // 解析execution参数
        RLPReader.RLPItem[] memory execItems = items[1].toList();
        if(execItems.length < 14) {
            return (RelayerLabel.Dishonest, bytes32(0));
        }

        latestExecParams.parentHash = bytes32(execItems[0].toBytes());
        latestExecParams.uncleHash = bytes32(execItems[1].toBytes());
        latestExecParams.feeRecipient = address(bytes20(execItems[2].toBytes()));
        latestExecParams.stateRoot = bytes32(execItems[3].toBytes());
        latestExecParams.receiptsRoot = bytes32(execItems[4].toBytes());
        latestExecParams.logsBloom = bytes32(execItems[5].toBytes());
        latestExecParams.difficulty = bytes32(execItems[6].toBytes());
        latestExecParams.blockNumber = execItems[7].toUint();
        latestExecParams.gasLimit = execItems[8].toUint();
        latestExecParams.gasUsed = execItems[9].toUint();
        latestExecParams.timestamp = execItems[10].toUint();
        latestExecParams.extraData = execItems[11].toBytes();
        latestExecParams.baseFeePerGas = bytes32(execItems[12].toBytes());
        latestExecParams.blockHash = bytes32(execItems[13].toBytes());

        // 存储父区块哈希用于getTopKeyFromShadowLedger
        latestHash = latestExecParams.blockHash;
        keyPrevShadowBlock = latestExecParams.parentHash;
        lastSlot = newSlot;
        return (RelayerLabel.Valid, keyPrevShadowBlock);
    }

    /// @notice 实现查询当前最新区块的区块哈希
    function getTopKeyFromShadowLedger() 
        external 
        view 
        override 
        returns(bytes32 key) 
    {
        return latestHash;
    }
    /// @notice 实现查询当前最新区块的slot
    function getTopKeyFromShadowLedger_slot() 
        external 
        view 
        returns(bytes32 key) 
    {
        return bytes32(lastSlot);
    }
    function checkIfOldFork(bytes32 keyShadowBlock) override public view returns(bool res){
        return false;
    }
    function getKeyFromShadowBlock(bytes calldata rawShadowBlock) override public pure returns(bytes32 keyShadowBlock){
        RLPReader.RLPItem[] memory items = rawShadowBlock.toRlpItem().toList();
        RLPReader.RLPItem[] memory execItems = items[1].toList();
        return bytes32(execItems[13].toUint());
    }
    function verifyTxByShadowLedger (bytes calldata leafNode, bytes calldata proof, bytes32 rootKey, uint delay) override public view returns (bool success){
        return true;
    }
}
