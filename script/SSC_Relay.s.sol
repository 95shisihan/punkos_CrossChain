// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  
import "src/SSC/RelayContract.sol";
import "src/HUB/MultiChainManager.sol";
//DEPLOY_ENV=dev forge script script/SSC_Relay.s.sol --rpc-url http://127.0.0.1:8545 --broadcast -vvvv
contract RunScript is Script {  
    string public env;
    uint256 public privateKey;
    address public publicKey;
    string public dataRoot;
    string public myName = "SSC";
    address public myAddress;
    SSC_Relay public myContract;

    string public managerName = "Manager";
    address public managerAddress;
    MultiChain public managerContract;
    function run() public {  
        loadDev();
        publicKey = vm.addr(privateKey);
        vm.startBroadcast(privateKey);
        managerAddress = loadContractAddress(managerName);
        managerContract = MultiChain(managerAddress);
        console.log("Result of check SSC_Relay:", checkIfRelayWork());
        console.log("Result of become relayer of SSC_Relay:", checkIfRelayer());
        //withdrawStake();
        //relayFirstBlock();
        for(uint i = 0; i < 10; i ++){
            relayBlock();
        } 
        
        //console.log("Block Hash:");  
        //console.logBytes32(hash);  
        //console.log("Block Header (first 32 bytes):");  
        //console.logBytes(header); 
        vm.stopBroadcast(); 
    }
    function loadDev() public{
        env = vm.envString("DEPLOY_ENV");       
        if (keccak256(abi.encodePacked(env)) == keccak256(abi.encodePacked("dev"))) {  
            privateKey = vm.envUint("DEV_PRIVATE_KEY");   
            console.log("Deploying to Dev Environment");  
        } 
        else if (keccak256(abi.encodePacked(env)) == keccak256(abi.encodePacked("test"))) {  
            privateKey = vm.envUint("TEST_PRIVATE_KEY");   
            console.log("Deploying to Test Environment");  
        } 
        else {  
            revert("Invalid environment");  
        }
        string memory projectRoot = vm.projectRoot();   
        dataRoot = string(abi.encodePacked(projectRoot, "/data/", env, "/"));   
    }   
    function loadContractAddress(string memory contractName) internal view returns (address){  
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        return vm.parseAddress(vm.readFile(filePath));  
    }
    function checkIfRelayWork() internal returns (bool){
        uint256 myChainID = managerContract.getSourceChainIDBySymbol(myName);
        if(myChainID != 0){
            (,,,uint numContract,address[] memory addresses) = managerContract.getSourceChainInfo(myChainID);
            if (numContract == 1){
                myAddress = addresses[0];
                myContract = SSC_Relay(myAddress);
                if(myContract.getContractState() == 2){
                    return true;
                }  
            }
        }
        return false;
    }
    function checkIfRelayer() internal returns (bool){
        uint256 myStake = myContract.getMyStake();
        uint256 targetStake = 2 * myContract.getRequireStake();
        if(myStake >= targetStake){
            return true;
        }
        else{
            uint newStake = targetStake - myStake;
            myContract.becomeRelayer{value: newStake}();
            myStake = myContract.getMyStake();
            if(myStake >= targetStake){
                return true;
            }
        }
        return false;
    }
    function relayBlock() internal returns (bool){
        bytes32 topKey = myContract.getTopKeyFromShadowLedger();
        console.log("TopKey:",uint256(topKey));
        bytes32 genesisKey = myContract.getGenesisKey();
        if(topKey == genesisKey){
            console.log("I am the first relayer");
            relayNewBlock(topKey);
            relayNewBlock(bytes32(uint256(topKey)+1));

        }
        else{
            console.log("I am not the first relayer");
            relayNewBlock(bytes32(uint256(topKey)+1));
        }   
    }
    function relayNewBlock(bytes32 topKey) internal returns (bool){
        bytes memory rawPrev = abi.encode(topKey);
        bytes32 newKey = bytes32(uint256(topKey) + 1);
        bytes memory raw = abi.encode(newKey);
        bytes32 commit = keccak256(abi.encodePacked(raw, publicKey));
        myContract.updateShadowLedgerByRelayer{gas:1000000}(rawPrev,newKey,commit);  
    }
    function withdrawStake() internal returns (bool){
        uint256 myStake = myContract.getMyStake();
        myContract.withdrawStake(myStake);
        console.log("My stake is:", myContract.getMyStake());
    }   
}  