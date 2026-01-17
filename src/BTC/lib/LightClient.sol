// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import  "./BTC_Util.sol";
//import  "src/cross-std/OnchainLightClient.sol";
import {SourceConsensusRules as SCR} from "bridge-std/AbstractSourceRules.sol";
import "forge-std/console.sol";

contract BTC_OLC is SCR
{
    using Util for *;
    uint public mainnet;
    bytes32 public genesisHash;
    bytes32 public heaviestHash;
    //uint256 public latestConfirmHash
    struct RawHeader {
        uint32 version;
        uint32 time;
        uint32 bits;
        uint32 nonce;
        bytes32 hashPrevBlock;
        bytes32 hashMerkleRoot;
    }
    struct ShadowHeader {
        uint256 height;
        bytes32 hashEpochStartBlock;
        bytes32 hashPrevBlock;
        bytes32 hashMerkleRoot;
    }
    struct EpochStartHeader {
        uint32 time;
        uint32 bits;
    }
    struct EpochEndHeader {
        uint32 time;
    }
    mapping (bytes32 => ShadowHeader) public shadowTree;
    mapping (bytes32 => EpochStartHeader) public epochStartHeaders;
    mapping (bytes32 => EpochEndHeader) public epochEndHeaders;
    mapping (uint256 => bytes32) public confirmChain;

    /*3. Bitcoin CONSTANTS */ 
    uint256 public constant DIFFICULTY_ADJUSTMENT_INVETVAL = 2016;
    uint256 public constant TARGET_TIMESPAN = 14 * 24 * 60 * 60; // 2 weeks 
    uint256 public constant UNROUNDED_MAX_TARGET = 2**224 - 1; 
    uint256 public constant TARGET_TIMESPAN_DIV_4 = TARGET_TIMESPAN / 4; // store division as constant to save costs
    uint256 public constant TARGET_TIMESPAN_MUL_4 = TARGET_TIMESPAN * 4; // store multiplucation as constant to save costs
    uint public constant CONFIRM = 6;

    constructor(uint _mainnet) {
        mainnet = _mainnet;
        require(_mainnet < 2,"Wrong mainnet!");
    }
    /*
    *  Part 1st: override functions
    */
    function setGenesisShadowBlock(bytes calldata rawGenesisShadowBlock, bytes calldata params) internal override returns (bool success){
        uint256 heightGenesis = params.bytesToUint256();
        return setGenesis(rawGenesisShadowBlock, heightGenesis);
    }
    function submitNewShadowBlock(bytes calldata rawNewShadowBlock) internal override returns (RelayerLabel relayerLabel,bytes32 hashPrevHeader){
        (relayerLabel,hashPrevHeader) = submitNewHeader(rawNewShadowBlock);
    }
    function verifyTxByShadowLedger (bytes calldata leafNode, bytes calldata proof, bytes32 rootKey, uint delay) public override view returns (bool success){
        return verifyTx(leafNode,proof,rootKey,delay);
    }
    function getKeyFromShadowBlock(bytes calldata rawShadowBlock) public override pure returns(bytes32 keyShadowBlock){
        keyShadowBlock = computeHeaderHash(rawShadowBlock);
    }
    function getTopKeyFromShadowLedger() external override view returns(bytes32 key){
        //key = bytes32(getTopHeight());
        return heaviestHash;
    }
    /*
    * Part 2nd: detailed functions
    */
    function verifyTx (bytes calldata leafNode, bytes calldata proof, bytes32 hashHeader, uint256 delay) internal view returns (bool success){
        if(checkIfConfirm(hashHeader,delay) != 1){
            console.log("The block header does not exist or is not confirmed!");
            return false;
        }
        bytes32 txRoot = getHeaderTxRoot(hashHeader);
        bytes32 txHash = leafNode.bytesToBytes32();
        if(verifyTx(txHash,proof,txRoot)){
            return true;
        }
        else{
            console.log("The tx proof is wrong!");
            return false;
        }
    }
    function checkIfConfirm(bytes32 hashHeader, uint confirmParam) public view returns (uint res){
        uint height = shadowTree[hashHeader].height;
        if(uint256(confirmChain[height + confirmParam]) == 0){// new blocks
            console.log("The block header is new and not confirmed!");
            return 2;
        }
        else if ((confirmChain[height] == hashHeader)){//confirm
            return 1;
        }
        else{
            if(height == 0){
                console.log("The block header does not exist!");
            }
            else{
                console.log("The block header is on a fork!");
            }
            return 0;
        }
    }
    function computeHeaderHash(bytes calldata bytesHeader) public pure returns (bytes32 hashHeader){
        return bytesHeader.dSha256().reverseBytes32();
    }
    function checkIfOldFork(bytes32 hashHeader) public override view returns(bool){
        if(uint256(shadowTree[hashHeader].hashMerkleRoot) == 0){//block not exists
            return false;
        }
        else if(checkIfConfirm(hashHeader,CONFIRM) == 1){//block has been confirmed
            return true;
        }
        else{
            return false;
        }
    }
    function verifyTx(bytes32 txHash, bytes calldata merkleProof, bytes32 txRoot) internal view returns (bool success){
        //txRoot will be replaced by reading block header submitted by relayers indexed by hash
        require(merkleProof.length % 32 == 0, "ERR_MERKLE_PROOF_LENGTH!");
        bytes32 merkleRoot;
        if (merkleProof.length == 32){
            merkleRoot = txHash;
        } 
        else{
            merkleRoot = calculateMeekleRoot(txHash, merkleProof);
        }
        return (txRoot == merkleRoot);
    }
    function calculateMeekleRoot(bytes32 txHash, bytes memory merkleProof) internal view returns(bytes32){
        uint256 txIndex = merkleProof.slice(0, 32).bytesToUint256();
        //bytes32 resultHash = merkleProof.sliceBytes(0, 32).bytesToBytes32();
        bytes32 resultHash = txHash.reverseBytes32();
        uint256 idx = txIndex;
        for (uint i = 1; i < merkleProof.length / 32; i ++){
            if (idx % 2 == 1){
                bytes32 left = merkleProof.sliceBytes(i * 32, 32).bytesToBytes32();
                bytes32 right = resultHash;
                resultHash = _merkleStep(left, right);
            }
            else{
                bytes32 left = resultHash;
                bytes32 right = merkleProof.sliceBytes(i * 32, 32).bytesToBytes32();
                resultHash = _merkleStep(left, right);
            }
            idx = idx >> 1;
        }
        return resultHash.reverseBytes32();
    }
    
    // @notice          Concatenates and hashes two inputs for merkle proving
    // @dev             Not recommended to call directly.
    // @param _a        The first hash
    // @param _b        The second hash
    // @return          The double-sha256 of the concatenated hashes
    function _merkleStep(bytes32 _a, bytes32 _b) internal view returns (bytes32 digest) {
        assembly {
            let ptr := mload(0x40)
            mstore(ptr, _a)
            mstore(add(ptr, 0x20), _b)
            pop(staticcall(gas(), 2, ptr, 0x40, ptr, 0x20)) // sha2 #1
            pop(staticcall(gas(), 2, ptr, 0x20, ptr, 0x20)) // sha2 #2
            digest := mload(ptr)
        }
    }
    
    
    function setGenesis(bytes calldata bytesGenesis, uint heightGenesis) internal returns (bool success){
        bytes32 hashGenesis =  computeHeaderHash(bytesGenesis);
        //require(bytesGenesis.length == 80, "ERROR: Failed Parse Genesis!");
        if(bytesGenesis.length != 80){
            console.log("ERROR: Failed Parse Genesis!");
            return false;
        }
        RawHeader memory rawGenesis = parseHeader(bytesGenesis);
        //require(headerValidationCheck(rawGenesis,hashGenesis), "ERROR: Failed Header Validation Check For Genesis!");
        if(!headerValidationCheck(rawGenesis,hashGenesis)){
            console.log("ERROR: Failed Header Validation Check For Genesis!");
            return false;
        }
        //require(storeGenesis(rawGenesis,hashGenesis,heightGenesis,relayer), "ERROR: Something Wrong Happened While Storing Genesis");
        if(!storeGenesis(rawGenesis,hashGenesis,heightGenesis)){
            console.log("ERROR: Something Wrong Happened While Storing Genesis");
            return false;
        }
        return true;
    }
    function submitNewHeader(bytes calldata bytesHeader) internal returns (RelayerLabel relayerLabel,bytes32 hashPrevHeader){
        bytes32 hashHeader =  computeHeaderHash(bytesHeader);
        //require(bytesHeader.length == 80, "Failed Parse New Header!");
        //bytes32 hashPrevHeader;
        if(bytesHeader.length != 80){
            console.log("ERROR: Failed Parse New Header!");
            return (RelayerLabel.Dishonest,hashPrevHeader);
        }
        RawHeader memory rawHeader = parseHeader(bytesHeader); 
        //require(headerConnectionCheck_1(hashHeader), "Failed Header Connection Check Stage 1 For New Header!");
        if(!headerConnectionCheck_1(hashHeader)){
            console.log("WARNING: Failed Header Connection Check Stage 1 For New Header!");
            return (RelayerLabel.Invalid_Honest,hashPrevHeader);
        }   
        //require(headerValidationCheck(rawHeader,hashHeader), "Failed Header Validation Check For New Header!");
        if(!headerValidationCheck(rawHeader,hashHeader)){
            console.log("ERROR: Failed Header Validation Check For New Header!");
            return (RelayerLabel.Dishonest,hashPrevHeader);
        }
        //require(headerConnectionCheck_2(rawHeader), "Failed Header Connection Check Stage 2 For New Header!");
        if(!headerConnectionCheck_2(rawHeader)){
            console.log("ERROR: Failed Header Connection Check Stage 2 For New Header!");
            return (RelayerLabel.Dishonest,hashPrevHeader);
        }
        //require(storeNewHeader(rawHeader,hashHeader,relayer), "Something Wrong Happened While Storing New Header");
        if(!storeNewHeader(rawHeader,hashHeader)){
            console.log("ERROR: Something Wrong Happened While Storing New Header!");
            return (RelayerLabel.Dishonest,hashPrevHeader);
        }
        hashPrevHeader = rawHeader.hashPrevBlock;
        return (RelayerLabel.Valid,hashPrevHeader);
    }
    function headerConnectionCheck_1(bytes32 hashHeader) internal view returns (bool){
        if (uint256(shadowTree[hashHeader].hashMerkleRoot) != 0 ){
            console.log("Submitted Header Already Exists!");
            return false;
        }
        return true;    
    }
    function headerConnectionCheck_2(RawHeader memory rawHeader) internal view returns (bool){
        if (uint256(shadowTree[rawHeader.hashPrevBlock].hashMerkleRoot) == 0){
            console.log("Parent Header Does Not Exists!");
            return false;
        }
        if (!checkBits(rawHeader.bits,rawHeader.hashPrevBlock)){
            console.log("Bits of Submitted Header is Wrong!");
            return false;
        }
        return true;    
    }
    function headerValidationCheck(RawHeader memory rawHeader, bytes32 hashHeader) internal pure returns (bool){
        //check if blockHash < target
        if (uint256(hashHeader) >= rawHeader.bits.bitsToTarget())
            //console.log("Hash Header is Larger Than Target!");
            return false;
        return true;
    }
    function storeGenesis(RawHeader memory rawGenesis, bytes32 hashGenesis, uint heightGenesis) internal returns (bool){
        shadowTree[hashGenesis] = headerRawToShadow(rawGenesis,heightGenesis,hashGenesis);
        genesisHash = hashGenesis;
        heaviestHash = hashGenesis;
        epochStartHeaders[hashGenesis] = recordEpochStartHeader(rawGenesis);
        confirmChain[heightGenesis] = hashGenesis;
        //console.log("Relay Union %s sets the initial block header with height = %s && hash = %s",relayer,heightGenesis,hashGenesis);
        //emit NewHeader(hashGenesis,relayer,heightGenesis);
        return true;
    }
    function storeNewHeader(RawHeader memory rawHeader, bytes32 hashHeader) internal returns (bool){
        ShadowHeader memory parent = shadowTree[rawHeader.hashPrevBlock];
        uint height = parent.height + 1;
        if(shouldRetarget(height)){
            shadowTree[hashHeader] = headerRawToShadow(rawHeader,height,hashHeader);
            epochStartHeaders[hashHeader] = recordEpochStartHeader(rawHeader);
        }
        else if(shouldRetarget(height + 1)){
            shadowTree[hashHeader] = headerRawToShadow(rawHeader,height,parent.hashEpochStartBlock);
            epochEndHeaders[hashHeader] = recordEpochEndHeader(rawHeader);
        }
        else{
            shadowTree[hashHeader] = headerRawToShadow(rawHeader,height,parent.hashEpochStartBlock);
        }
        //console.log("Relayer %s submits a new block header with height = %s && hash = %s",relayer,height,hashHeader);
        ShadowHeader memory top = shadowTree[heaviestHash];
        if(height > top.height){
            heaviestHash = hashHeader;
            confirmChain[height] = hashHeader;
            uint256 tmpHeight = height - 1;
            bytes32 tmpHash = shadowTree[hashHeader].hashPrevBlock;
            while(confirmChain[tmpHeight] != tmpHash){
                confirmChain[tmpHeight] = tmpHash;
                tmpHeight -= 1;
                tmpHash = shadowTree[tmpHash].hashPrevBlock;
            }
        } 
        return true;
    }
    function parseHeader(bytes calldata bytesHeader) internal pure returns (RawHeader memory)
    {
        uint VERSION_BYTES               = 4;
        uint HASHPREVBLOCK_BYTES         = 32;
        uint HASHMERKLEROOT_BYTES        = 32;
        uint TIME_BYTES                  = 4;
        uint BITS_BYTES                  = 4;
        uint NONCE_BYTES                 = 4;
        uint offset = 0;
        RawHeader memory header;
        header.version = Util.sliceBytes(bytesHeader, offset, VERSION_BYTES).bytesToUint32();
        offset = offset + VERSION_BYTES;
        header.hashPrevBlock = Util.sliceBytes(bytesHeader, offset, HASHPREVBLOCK_BYTES).bytesToBytes32();
        offset = offset + HASHPREVBLOCK_BYTES;
        header.hashMerkleRoot = Util.sliceBytes(bytesHeader, offset, HASHMERKLEROOT_BYTES).bytesToBytes32();
        offset = offset + HASHMERKLEROOT_BYTES;
        header.time = Util.sliceBytes(bytesHeader, offset, TIME_BYTES).bytesToUint32();
        offset = offset + TIME_BYTES;
        header.bits = Util.sliceBytes(bytesHeader, offset, BITS_BYTES).bytesToUint32();
        offset = offset + BITS_BYTES;
        header.nonce = Util.sliceBytes(bytesHeader, offset, NONCE_BYTES).bytesToUint32();
        offset = offset + NONCE_BYTES;
        return header;
    }
    function headerRawToShadow(RawHeader memory raw, uint height, bytes32 hashEpochStartBlock) internal pure returns (ShadowHeader memory){
        ShadowHeader memory shadow;
        shadow.hashPrevBlock = raw.hashPrevBlock;
        shadow.hashMerkleRoot= raw.hashMerkleRoot;
        shadow.height = height;
        shadow.hashEpochStartBlock = hashEpochStartBlock;
        return shadow;
    }

    function recordEpochStartHeader(RawHeader memory raw) internal pure returns (EpochStartHeader memory){
        EpochStartHeader memory es;
        es.time = raw.time;
        es.bits = raw.bits;
        return es;
    }
    function recordEpochEndHeader(RawHeader memory raw) internal pure returns (EpochEndHeader memory){
        EpochEndHeader memory ee;
        ee.time = raw.time;
        return ee;
    }
    function checkBits(uint32 bits, bytes32 hashParent) internal view returns (bool){      
        ShadowHeader memory parent = shadowTree[hashParent];
        EpochStartHeader memory es = epochStartHeaders[parent.hashEpochStartBlock];
        
        if((mainnet == 0) && shouldRetarget(parent.height + 1)) {// need to adjust difficulty
            EpochEndHeader memory ee = epochEndHeaders[hashParent];
            uint256 prevTime = ee.time;
            uint256 prevTarget = es.bits.bitsToTarget();
            uint256 startTime = es.time;
            // check bits of current header according to function reTarget 
            return(bits == reTarget(prevTime,startTime,prevTarget));
        }
        else{// do not need to adjust difficulty
            // bits of current header should be equal to that of previous header
            return (bits == es.bits);
        }
        //return false;
    }
    function shouldRetarget(uint height) internal pure returns (bool){
        return ((height % DIFFICULTY_ADJUSTMENT_INVETVAL) == 0);
    }
    function reTarget(uint256 prevTime, uint256 startTime, uint256 prevTarget) internal pure returns (uint){
        uint256 actualTimeSpan = prevTime - startTime;
        // limit timespan if too long or too short
        if(actualTimeSpan < TARGET_TIMESPAN_DIV_4){
            actualTimeSpan = TARGET_TIMESPAN_DIV_4;
        } 
        if(actualTimeSpan > TARGET_TIMESPAN_MUL_4){
            actualTimeSpan = TARGET_TIMESPAN_MUL_4;
        }
        //uint256 newTarget = SafeMath.div(SafeMath.mul(actualTimeSpan, prevTarget),TARGET_TIMESPAN);
        uint256 newTarget = actualTimeSpan * prevTarget / TARGET_TIMESPAN;
        // new target should not be easier than genesis block
        if(newTarget > UNROUNDED_MAX_TARGET){
            newTarget = UNROUNDED_MAX_TARGET;
        }
        return newTarget.targetToBits();
    }
    function getGenesis() public view returns(uint,bytes32){
        ShadowHeader memory H = shadowTree[genesisHash];
        return (H.height,genesisHash);
    }
    function getGenesisHash() public view returns(bytes32){
        return genesisHash;
    }
    function getGenesisHeight() public view returns(uint){
        return shadowTree[genesisHash].height;
    }
    function getTopHeader() public view returns(uint,bytes32){
        ShadowHeader memory H = shadowTree[heaviestHash];
        return (H.height,genesisHash);
    }
    function getTopHeight() public view returns(uint){
        return shadowTree[heaviestHash].height;
    }
    function getTopHash() public view returns(bytes32){
        return heaviestHash;
    }
    function getHeaderTxRoot(bytes32 hashHeader) public view returns(bytes32){
        return shadowTree[hashHeader].hashMerkleRoot;
    }
    function getHeaderPrevhash(bytes32 hashHeader) public view returns(bytes32){
        return shadowTree[hashHeader].hashPrevBlock;
    }
    function getHeaderHeight(bytes32 hashHeader) public view returns(uint){
        return shadowTree[hashHeader].height;
    }
    function getIfConfirm(bytes32 headerHash) public view returns(bool){
        if(checkIfConfirm(headerHash,CONFIRM) == 1){
            return true;
        }
        else{
            return false;
        }
    }
    function getMainChainHeaderHash(uint height) public view returns(bytes32){
        return confirmChain[height];
    }
    function getMainnet() public view returns(uint){
        return mainnet;
    }
}
