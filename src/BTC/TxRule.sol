// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import  "./lib/BTC_Util.sol";
import  {SourceTransactionRules as STR} from "bridge-std/AbstractSourceRules.sol";

contract BTC_TR is STR{
    using Util for *;
    enum TxType {
        Legacy, 
        Segwit
    }
    struct BTC_Tx{
        TxType tx_type;
        bytes4 version;
        bytes1 marker;
        bytes1 flag;
        bytes inputs;
        bytes outputs;
        bytes witness;
        bytes4 locktime;
    }
    function checkIfPayloadMatchTx(bytes memory _payload, bytes memory _rawTx, uint256 _matchType) override external pure returns (bool res){
        if(_matchType == 0){
            return keccak256(_payload) == keccak256(_rawTx);
        }
        else{
            revert();
        }
    }
    function getKeyFromRawTx(bytes memory _rawTx) override external pure returns (bytes32 keyTx){
        return hashRawTx(_rawTx);
    }
    function checkIfLeafNodeMatchTx(bytes memory _leafNode, bytes memory _rawTx) override external pure returns (bool res){
        return hashRawTx(_rawTx) == _leafNode.bytesToBytes32();
    }
    function hashRawTx(bytes memory rawTx) internal pure returns(bytes32 txid){
        (bytes memory version,bytes memory n_inputs,bytes memory n_outputs,bytes memory locktime) = parseTx(rawTx);
        txid = abi.encodePacked(version,n_inputs,n_outputs,locktime).dSha256().reverseBytes32();
    }
    function parseTx(bytes memory rawTx) internal pure returns(
        bytes memory version,
        bytes memory n_inputs,
        bytes memory n_outputs,
        bytes memory locktime
        ){
        version = Util.slice(rawTx, 0, 4);
        locktime = Util.slice(rawTx, rawTx.length - 4, 4);
        uint offset = 4;
        if (uint8(rawTx[4])== 0){
            //TxType tx_type = TxType.Segwit;
            //bytes1 marker = rawTx[4];
            //bytes1 flag = rawTx[5];
            offset += 2;
        }
        uint inputsStartOffset = offset;
        (uint stepCountInput,uint64 countInput) = compactSizeToUint(rawTx,offset);
        offset = offset + stepCountInput;
        //Input[] memory inputs = new Input[](countInput);
        for(uint i = 0; i < countInput; i++){
            (uint stepInputScript,uint64 sizeScript) = compactSizeToUint(rawTx,offset+36);
            uint inputLength = 36 + stepInputScript + uint256(sizeScript) + 4;
            //bytes memory newInput = Util.slice(bytesTx, offset, inputLength);
            //inputs[i] = Input(newInput);
            offset += inputLength;
        }
        n_inputs = Util.slice(rawTx, inputsStartOffset, offset - inputsStartOffset);
        uint outputsStartOffset = offset;
        (uint stepCountOutput,uint64 countOutput) = compactSizeToUint(rawTx,offset);
        offset = offset + stepCountOutput;
        for(uint i = 0; i < countOutput; i++){
            (uint stepOutputScript,uint64 sizeScript) = compactSizeToUint(rawTx,offset+8);
            uint outputLength = 8 + stepOutputScript + uint256(sizeScript);
            offset += outputLength;
        }
        n_outputs = Util.slice(rawTx, outputsStartOffset, offset - outputsStartOffset);
        //uint32 locktime = Util.sliceBytes(bytesTx, offset, 4).bytesToUint32();

    }
    function compactSizeToUint(bytes memory bs, uint offset) internal pure returns (uint, uint64){
        uint8 signal = uint8(bs[offset]);
        if(signal <= 252){
            uint step = 1;
            uint64 length = uint64(signal);
            return(step,length);
        }
        else if(signal == 253){
            uint step = 3;
            uint64 length = uint64(Util.slice(bs, offset+1, 2).bytesToUint16());
            return(step,length);
        }
        else if(signal == 254){
            uint step = 5;
            uint64 length = uint64(Util.slice(bs, offset+1, 4).bytesToUint32());
            return(step,length);
        }
        else if(signal == 255){
            uint step = 9;
            uint64 length = Util.slice(bs, offset+1, 8).bytesToUint64();
            return(step,length);
        }
        
    }
    

}