// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {SourceConsensusRules as SCR} from "bridge-std/AbstractSourceRules.sol";

contract SimpleChainLightClient is SCR{
    bytes32 public keyGenesis;
    bytes32 public keyTopBlock;
    struct ShadowBlock{
        uint256 index;
        bytes32 data;
    }
    mapping(bytes32 => ShadowBlock) public blockTree;

    function setGenesisShadowBlock (bytes calldata rawGenesisShadowBlock, bytes calldata params) override internal returns(bool success){
        if(keyGenesis != bytes32(0)){
            return false;
        }
        bytes32 keyGenesisBlock = abi.decode(rawGenesisShadowBlock,(bytes32));
        uint256 indexGenesis = abi.decode(params,(uint256));
        blockTree[keyGenesisBlock] = ShadowBlock({
            index: indexGenesis,
            data: keyGenesisBlock
        });
        keyGenesis = keyGenesisBlock;
        keyTopBlock = keyGenesisBlock;
        return true;
    }
    function submitNewShadowBlock(bytes calldata rawNewShadowBlock) override internal returns(RelayerLabel relayerLabel, bytes32 keyParentShadowBlock){
        if(keyGenesis == bytes32(0)){
            relayerLabel = RelayerLabel.Dishonest;
        }
        else{
            bytes32 keyNewBlock = abi.decode(rawNewShadowBlock,(bytes32));
            if (blockTree[keyNewBlock].data != bytes32(0)){
                relayerLabel = RelayerLabel.Invalid_Honest;
            }
            else{
                keyParentShadowBlock = bytes32(uint256(keyNewBlock) - 1);
                if (blockTree[keyParentShadowBlock].data == bytes32(0)){
                    relayerLabel = RelayerLabel.Dishonest;
                }
                else{
                    blockTree[keyNewBlock] = ShadowBlock({
                        index: blockTree[keyParentShadowBlock].index + 1,
                        data: keyNewBlock
                    }); 
                    keyTopBlock = keyNewBlock;
                    relayerLabel = RelayerLabel.Valid;
                }
            }
        }
    }
    
    
    function verifyTxByShadowLedger (bytes calldata leafNode, bytes calldata proof, bytes32 rootKey, uint delay) override public view returns (bool success){
        return false;
    }
    function getKeyFromShadowBlock(bytes calldata rawShadowBlock) override public pure returns (bytes32 keyShadowBlock){
        keyShadowBlock = abi.decode(rawShadowBlock,(bytes32));
    }

    function checkIfOldFork(bytes32 keyShadowBlock) override public view returns(bool res){
        res = false;
    }
    function getTopKeyFromShadowLedger() override public view returns(bytes32 key){
        key = keyTopBlock;
    }   
}
