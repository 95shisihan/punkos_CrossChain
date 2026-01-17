// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  
import "src/SSC/RelayContract.sol";
import "src/HUB/MultiChainManager.sol";
//forge script script/SSC_Relay.d.sol:DeployScript --rpc-url http:127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast -vvvv
contract DeployScript is Script {  
    string public env;
    uint256 public privateKey;
    string public dataRoot;
    string public myName = "SSC";
    address public myAddress;
    SSC_Relay public myContract;

    string public managerName = "Manager";
    address public managerAddress;
    MultiChain public managerContract;
    function run() public {  
        vm.txGasPrice(tx.gasprice);
        loadDev();
        vm.startBroadcast(privateKey);
        managerAddress = loadContractAddress(managerName);
        managerContract = MultiChain(managerAddress);
        //向多链管理合约查询中继合约是否创建，若创建返回部署地址，若未创建则部署新合约并注册
        uint256 myChainID = managerContract.getSourceChainIDBySymbol(myName);
        if(myChainID == 0){
            revert();
        }
        (,,,uint numContract,address[] memory addresses) = managerContract.getSourceChainInfo(myChainID);
        if (numContract > 1){
            revert();
        }
        else if (numContract == 1){
            myAddress = addresses[0];
            myContract = SSC_Relay(myAddress);
            vm.stopBroadcast();
            generateGenesis(myName);
        }
        else{
            myContract = new SSC_Relay();
            myAddress =  address(myContract);
            saveContractAddress(myName, myAddress); 
            myContract.updateContractManager(managerAddress);
            console.log("Result of setting multiChainContract as manager of SSC_Relay:", myContract.getContractManager() == managerAddress);
            generateGenesis(myName);
            vm.stopBroadcast();  
        } 
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
    function generateGenesis(string memory contractName) internal returns (bool){
        uint256 genesisKey = 2024;
        uint256 genesisIndex = 0;
        bytes memory rawGenesis = abi.encode(genesisKey);
        bytes memory param = abi.encode(genesisIndex);
        bytes memory payload = abi.encodeWithSignature("setGenesisShadowLedgerByManager(bytes,bytes)", rawGenesis,param);
        string memory projectRoot = vm.projectRoot();   
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".genesis"));   
        string memory data = vm.toString(payload);  
        vm.writeFile(filePath, data);  
        console.log("Genesis payload saved to", filePath); 
    } 
}  