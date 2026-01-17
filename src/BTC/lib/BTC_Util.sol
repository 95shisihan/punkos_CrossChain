// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

library Util {
    /* decompress 32-bit bits to 256-bit target */
    function bitsToTarget(uint32 bits) internal pure returns(uint256){
        //uint bits = 0x1b0404cb;
        uint factor = bits & 0x00ffffff;
        uint power = bits / 2 ** 24;
        uint256 target = factor * 2 **(8*(power - 3));
        return target;
    }
    function targetToBits(uint256 target) internal pure returns(uint){

        // convert target to 256-number
        uint[32] memory tmp;
        uint i;
        for(i = 0; i < 32; i ++){
            tmp[i] = target % 256;
            target = target / 256;
            if(target == 0){
                break;
            }
        }
        i ++;
        //left add 0 if the first < 127
        if(tmp[i-1] > 127){
            tmp[i] = 0;
            i ++;
        }

        uint power = i; //length of 256-number target
        uint[3] memory factor; // the first three numbers of 256-number target
        
        //right add 0 if length < 3
        if(i > 3){
            for(uint j = 0; j < 3; j ++){
                factor[j] = tmp[i-1-j];
            }
        }
        else{
            uint j;
            for(j = 0; j < i; j ++){
                factor[j] = tmp[i-1-j];
            }
            while(j < 3){
                factor[j] = 0;
                j ++;
            }
        }
        uint bits = 256**3*power + 256**2*factor[0] + 256*factor[1] + factor[2];

        return (bits);
    }
    
    function dSha256(bytes memory input) internal pure returns (bytes32){
        return sha256(abi.encodePacked(sha256(input)));
    }
    function concatDSHA256(bytes memory left, bytes memory right) internal pure returns (bytes32) {
        return dSha256(abi.encodePacked(left, right));
    }
    /// @notice          Changes the endianness of a byte array
    /// @dev             Returns a new, backwards, bytes
    /// @param _b        The bytes to reverse
    /// @return          The reversed bytes
    function reverseEndianness(bytes memory _b) internal pure returns (bytes memory) {
        bytes memory _newValue = new bytes(_b.length);

        for (uint i = 0; i < _b.length; i++) {
            _newValue[_b.length - i - 1] = _b[i];
        }

        return _newValue;
    }
    /// @notice          Changes the endianness of a uint256
    /// @dev             https://graphics.stanford.edu/~seander/bithacks.html#ReverseParallel
    /// @param _b        The unsigned integer to reverse
    /// @return v        The reversed value
    function reverseUint256(uint256 _b) internal pure returns (uint256 v) {
        v = _b;
        // swap bytes
        v = ((v >> 8) & 0x00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF) |
        ((v & 0x00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF) << 8);
        // swap 2-byte long pairs
        v = ((v >> 16) & 0x0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF) |
        ((v & 0x0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF) << 16);
        // swap 4-byte long pairs
        v = ((v >> 32) & 0x00000000FFFFFFFF00000000FFFFFFFF00000000FFFFFFFF00000000FFFFFFFF) |
        ((v & 0x00000000FFFFFFFF00000000FFFFFFFF00000000FFFFFFFF00000000FFFFFFFF) << 32);
        // swap 8-byte long pairs
        v = ((v >> 64) & 0x0000000000000000FFFFFFFFFFFFFFFF0000000000000000FFFFFFFFFFFFFFFF) |
        ((v & 0x0000000000000000FFFFFFFFFFFFFFFF0000000000000000FFFFFFFFFFFFFFFF) << 64);
        // swap 16-byte long pairs
        v = (v >> 128) | (v << 128);
    }
    function reverseBytes32(bytes32 _b) internal pure returns (bytes32 v) {
        v = bytes32(reverseUint256(uint256(_b)));
    }
    
    function sliceBytes(bytes memory bs, uint start, uint size) internal pure returns (bytes memory){
        require(bs.length >= start + size, "slicing out of range");
        //uint x;
        bytes memory x = new bytes(size);
        for(uint i = 0; i < size; i ++){
            x[i] = bs[start + size - i - 1];
        }
        return x;
    }
    function slice(bytes memory bs, uint start, uint size) internal pure returns (bytes memory){
        require(bs.length >= start + size, "slicing out of range");
        //uint x;
        bytes memory x = new bytes(size);
        for(uint i = 0; i < size; i ++){
            x[i] = bs[start + i];
        }
        return x;
    }

    function bytesToUint256(bytes memory bs) internal pure returns (uint256)
    {
        require(bs.length >= 32, "slicing out of range");
        uint256 x;
        assembly {
            x := mload(add(bs, add(0x20, 0)))
        }
        return x;
    }
    function bytesToBytes32(bytes memory bs) internal pure returns (bytes32)
    {
        require(bs.length >= 32, "slicing out of range");
        bytes32 x;
        assembly {
            x := mload(add(bs, add(0x20, 0)))
        }
        return x;
    }
    function bytesToUint64(bytes memory bs) internal pure returns (uint64)
    {
        require(bs.length >= 8, "slicing out of range");
        uint64 x;
        assembly {
            x := mload(add(bs, add(0x8, 0)))
        }
        return x;
    }
    function bytesToUint32(bytes memory bs) internal pure returns (uint32)
    {
        require(bs.length >= 4, "slicing out of range");
        uint32 x;
        assembly {
            x := mload(add(bs, add(0x4, 0)))
        }
        return x;
    }
    function bytesToUint16(bytes memory bs) internal pure returns (uint16)
    {
        require(bs.length >= 2, "slicing out of range");
        uint16 x;
        assembly {
            x := mload(add(bs, add(0x2, 0)))
        }
        return x;
    }
    function bytesToAddress(bytes memory bs) internal pure returns (address)
    {
        //require(bs.length >= 20, "slicing out of range");
        address x;
        assembly {
            x := mload(add(bs, 20))
        }
        return x;
    }
    function addressToBytes(address input) internal pure returns (bytes memory){
        bytes memory output = new bytes(20);
        uint160 tmp = uint160(input);
        assembly{
            mstore(add(output, 20), tmp)
        }
        return output;
    }
}
