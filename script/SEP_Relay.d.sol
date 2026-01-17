// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  
import "src/SEP/RelayContract.sol";
import "src/HUB/MultiChainManager.sol";
//forge script script/SSC_Relay.d.sol:DeployScript --rpc-url http:127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast -vvvv
contract DeployScript is Script {  
    string public env;
    uint256 public privateKey;
    string public dataRoot;
    string public myName = "SEP";
    address public myAddress;
    SEP_Relay public myContract;

    string public managerName = "Manager";
    address public managerAddress;
    MultiChain public managerContract;
    function run() public {
        loadDev();
        console.log("=============== Starting Deployment ===============");
        console.log("Current timestamp:", block.timestamp);
        
        vm.startBroadcast(privateKey);
        console.log("Broadcasting started with address:", msg.sender);
        
        // 加载管理合约地址
        managerAddress = loadContractAddress(managerName);
        console.log("Manager contract loaded at:", managerAddress);
        
        managerContract = MultiChain(managerAddress);
        console.log("MultiChain manager initialized");
        
        // 查询链ID
        console.log("\n--- Querying Chain ID ---");
        uint256 myChainID = managerContract.getSourceChainIDBySymbol(myName);
        console.log("Chain symbol:", myName);
        console.log("Queried chain ID:", myChainID);
        
        if(myChainID == 0) {
            console.log("[ERROR] Chain ID is 0, symbol not found!");
            revert();
        }
        console.log("[SUCCESS] Chain ID found:", myChainID);
        
        // 查询链上的合约信息
        console.log("\n--- Querying Source Chain Info ---");
        (,,,uint numContract,address[] memory addresses) = managerContract.getSourceChainInfo(myChainID);
        console.log("Number of contracts on chain:", numContract);
        
        // ======================== 分支 1：存在多于 1 个合约 ========================
        if (numContract > 1) {
            console.log("[ERROR] More than 1 contract found on chain!");
            console.log("Expected: 0 or 1, Got:", numContract);
            revert();
        }
        
        // ======================== 分支 2：存在 1 个合约 ========================
        else if (numContract == 1) {
            console.log("\n--- Branch: Contract Already Exists ---");
            myAddress = addresses[0];
            console.log("Existing relay contract found at:", myAddress);
            console.log("Loading existing SEP_Relay contract...");
            
            myContract = SEP_Relay(myAddress);
            console.log("[SUCCESS] SEP_Relay contract loaded");
            console.log("Contract manager:", myContract.getContractManager());
            console.log("Contract chain ID:", myContract.getChainID());
            
            vm.stopBroadcast();
            console.log("\nBroadcast stopped before generateGenesis()");
            console.log("--- Generating Genesis Data ---");
            
            bool genResult = generateGenesis();
            console.log("[Genesis Generation Result]:", genResult);
            console.log("=============== Deployment Complete (Existing Contract) ===============\n");
        }
        
        // ======================== 分支 3：不存在合约，需要新部署 ========================
        else {
            console.log("\n--- Branch: Deploying New Contract ---");
            console.log("No relay contract found, deploying new SEP_Relay...");
            
            // 部署新合约
            myContract = new SEP_Relay();
            myAddress = address(myContract);
            console.log("[SUCCESS] New SEP_Relay deployed at:", myAddress);
            console.log("Deployment transaction cost: ~2,000,000 gas");
            
            // 保存合约地址
            console.log("Saving contract address to file...");
            saveContractAddress(myName, myAddress);
            console.log("[SUCCESS] Contract address saved");
            
            // 设置管理合约
            console.log("Setting MultiChain manager...");
            myContract.updateContractManager(managerAddress);
            
            bool managerCheckResult = myContract.getContractManager() == managerAddress;
            console.log("Manager verification:", managerCheckResult);
            console.log("Contract manager address:", myContract.getContractManager());
            console.log("Expected manager address:", managerAddress);
            
            if (!managerCheckResult) {
                console.log("[WARNING] Manager address mismatch!");
            } else {
                console.log("[SUCCESS] Manager set correctly");
            }
            
            console.log("--- Generating Genesis Data ---");
            bool genResult = generateGenesis();
            console.log("[Genesis Generation Result]:", genResult);
            
            vm.stopBroadcast();
            console.log("Broadcast stopped after deployment");
            console.log("=============== Deployment Complete (New Contract) ===============\n");
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
    function generateGenesis() public returns (bool) {  
        // 准备 Python 脚本调用  
        string[] memory inputs = new string[](3);  
        //inputs[0] = "python3";  
        string memory pythonPath = vm.envString("PYTHON_PATH");
        inputs[0] = pythonPath;
        inputs[1] = "./script/get_SEP_Header.py";
        inputs[2] = "-1";   
        
        // 执行脚本  
        string memory result = string(vm.ffi(inputs));
        bool res = vm.parseJsonBool(result,".status");
        if (!res){
            return false;
        }
        //bytes32 hashGenesis = vm.parseJsonBytes32(result,".hash");
        // bytes memory rawGenesis = vm.parseJsonBytes(result,".raw");
        //uint heightGenesis = vm.parseJsonUint(result,".height");
        // 从 JSON 获取两个 RLP 编码好的 bytes
        bytes memory rlpHeader = vm.parseJsonBytes(result, ".raw");
        bytes memory rlpValidators = vm.parseJsonBytes(result, ".rawValidators"); // 确保这是 RLP 格式！
        // 解析 JSON 结果  
        //console.logBytes32(hashGenesis);
        //console.logBytes(rawGenesis);
        //console.logUint(heightGenesis);
        //bytes memory param = abi.encode(heightGenesis);
        //bytes memory payload = abi.encodeWithSignature("setGenesisShadowLedgerByManager(bytes,bytes)", rawGenesis,param);
        // 直接传入这两个 RLP bytes，不要再用 abi.encode 再次包装它们
        bytes memory payload = abi.encodeWithSignature(
            "setGenesisShadowLedgerByManager(bytes,bytes)", 
            rlpHeader,
            rlpValidators
        );
        string memory projectRoot = vm.projectRoot();   
        string memory filePath = string(abi.encodePacked(dataRoot, "SEP.genesis"));   
        string memory data = vm.toString(payload);  
        vm.writeFile(filePath, data);  
        console.log("Genesis payload saved to", filePath); 
        return true;  
    }
    // function generateGenesis() public returns (bool) {
    //     // 准备 Python 脚本调用
    //     string[] memory inputs = new string[](3);
    //     string memory pythonPath = vm.envString("PYTHON_PATH");
    //     inputs[0] = pythonPath;
    //     inputs[1] = "./script/get_SEP_Header.py";
    //     inputs[2] = "-1";
        
    //     // 执行脚本
    //     string memory result = string(vm.ffi(inputs));
    //     bool res = vm.parseJsonBool(result, ".status");
    //     if (!res) {
    //         return false;
    //     }
        
    //     // 从 JSON 解析数据
    //     bytes memory rawGenesis = vm.parseJsonBytes(result, ".raw");
    //     uint256 heightGenesis = vm.parseJsonUint(result, ".height");
        
    //     // ============ 关键修复：正确构造两个 uint256[] 数组 ============
        
    //     // 解析 rawGenesis 获取账户列表
    //     // 假设 rawGenesis 包含多个账户ID，需要解析成数组
    //     uint256[] memory accountList = new uint256[](2);
    //     accountList[0] = heightGenesis;  // 第1个账户/ID
    //     accountList[1] = 0;               // 第2个账户/ID（需要确定实际值）
        
    //     // 解析 rawGenesis 获取余额/值列表
    //     uint256[] memory balanceList = new uint256[](2);
    //     balanceList[0] = 0;               // 第1个账户的余额
    //     balanceList[1] = 0;               // 第2个账户的余额（需要确定实际值）
        
    //     // ============ 使用正确的函数签名和参数 ============
    //     bytes memory payload = abi.encodeWithSignature(
    //         "setGenesisShadowLedgerByManager(uint256[],uint256[])",
    //         accountList,
    //         balanceList
    //     );
        
    //     // 保存到文件
    //     string memory projectRoot = vm.projectRoot();
    //     string memory filePath = string(abi.encodePacked(dataRoot, "SEP.genesis"));
    //     string memory data = vm.toString(payload);
    //     vm.writeFile(filePath, data);
        
    //     console.log("Genesis payload saved to", filePath);
    //     return true;
    // }
}  