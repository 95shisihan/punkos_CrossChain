// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

library SimpleSourceChain{
    function generateNextTrueBlock(bytes32 topKey) external pure returns (bytes memory rawBlock){
        bytes32 newKey;
        newKey = bytes32(uint256(topKey) + 1);
        rawBlock = abi.encode(newKey);
    }
}