// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  
import "src/BTC/TxRule.sol";
import "src/HUB/MultiChainManager.sol";
//forge script script/BTC_Relay.d.sol:DeployScript --rpc-url http:127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast -vvvv
contract DeployScript is Script {  
    string public env;
    uint256 public privateKey;
    string public dataRoot;
    string public myName = "BTC";
    address public myAddress;
    BTC_TR public myContract;

    string public managerName = "Manager";
    address public managerAddress;
    MultiChain public managerContract;
    function run() public {  
        vm.txGasPrice(tx.gasprice);
        loadDev();
        vm.startBroadcast(privateKey);
        managerAddress = loadContractAddress(managerName);
        managerContract = MultiChain(managerAddress);
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
    function saveContractAddress(string memory contractName, address contractAddress) internal {    
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        string memory data = vm.toString(contractAddress);  
        vm.writeFile(filePath, data);  
        console.log("Contract address saved to", filePath);  
    }   
    function loadContractAddress(string memory contractName) internal view returns (address){    
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        return vm.parseAddress(vm.readFile(filePath));  
    }
}  