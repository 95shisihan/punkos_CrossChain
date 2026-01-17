// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  //导入 foundry 脚本工具库
import "src/BTC/RelayContract.sol";//导入 BTC 中继合约
import "src/HUB/MultiChainManager.sol";//导入多链管理器合约
//forge script script/BTC_Relay.d.sol:DeployScript --rpc-url http:127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast -vvvv
contract DeployScript is Script {  
    string public env;//部署环境
    uint256 public privateKey;//部署者私钥
    string public dataRoot;//数据文件根目录(存储地址,创世数据)
    string public myName = "BTC";//当前中继合约标识(与多链管理器中源链符号对应)
    address public myAddress;//BTC_Relay合约部署地址
    BTC_Relay public myContract;//BTC_Relay 合约实例

    string public managerName = "Manager";//多链管理器合约标识
    address public managerAddress;//多链管理器合约地址
    MultiChain public managerContract;//多链管理器合约实例
    function run() public {  
        vm.txGasPrice(tx.gasprice);//动态设置交易 gas 价格
        loadDev();//加载环境配置(私钥,数据路径等)
        vm.startBroadcast(privateKey);//开始广播交易(用部署者私钥签名)
        //加载多链管理器合约(必须先部署,否则脚本会报错)
        managerAddress = loadContractAddress(managerName);
        managerContract = MultiChain(managerAddress);
        //校验 BTC 源链是否已在管理器中注册
        uint256 myChainID = managerContract.getSourceChainIDBySymbol(myName);
        if(myChainID == 0){//若未注册(链 ID 为 0),直接回滚
            revert();
        }
        //校验该源链下的中继合约数量(限制最多 1 个,避免重复部署)
        (,,,uint numContract,address[] memory addresses) = managerContract.getSourceChainInfo(myChainID);
        if (numContract > 1){//合约数量超过一个,回滚防止异常
            console.log("Error: More than one BTC_Relay contract exists!");
            revert();
        }
        else if (numContract == 1){//合约存在,无需部署,停止广播
            //myAddress = addresses[0];
            //myContract = BTC_Relay(myAddress);
            console.log("The BTC_Relay contract already exists at address:", addresses[0]);
            vm.stopBroadcast();
        }
        else{   //不存在新合约,进行部署
            if(generateGenesis()){//先生成创世数据(生成失败则不部署)
                //部署 BTC_Relay 合约(构造函数参数为 0,需结合合约逻辑确认含义)
                myContract = new BTC_Relay(0);
                myAddress =  address(myContract);//获取部署地址
                saveContractAddress(myName, myAddress); //保存地址到文件(供后续脚本使用)
                //将多链管理器设为中继合约的管理员(权限控制)
                myContract.updateContractManager(managerAddress);
                //打印设置结果(验证管理员是否配置成功)
                console.log("Result of setting multiChainContract as manager of SSC_Relay:", myContract.getContractManager() == managerAddress);
                vm.stopBroadcast();  
            } 
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
    //合约地址读写函数,部署后的 BTC_Relay 地址写入文件（如 data/dev/BTC.address），供其他脚本（如创世状态初始化脚本）读取
    function saveContractAddress(string memory contractName, address contractAddress) internal {    
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        string memory data = vm.toString(contractAddress);  
        vm.writeFile(filePath, data);  
        console.log("Contract address saved to", filePath);  
    }   
    //从文件读取指定合约地址（此处用于读取多链管理器地址）。
    function loadContractAddress(string memory contractName) internal view returns (address){    
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        return vm.parseAddress(vm.readFile(filePath));  
    }
    //创世数据生成函数 generateGenesis()
    //核心辅助函数，通过调用 Python 脚本获取 BTC 创世区块数据，生成中继合约初始化所需的 payload 并存储：
    function generateGenesis() public returns (bool) {  
        // 准备 Python 脚本调用  
        string[] memory inputs = new string[](3);  
        //inputs[0] = "python3";  
        string memory pythonPath = vm.envString("PYTHON_PATH");
        inputs[0] = pythonPath;
        inputs[1] = "./script/get_BTC_Header.py";
        inputs[2] = "-1";   
        
        // 执行脚本  
        string memory result = string(vm.ffi(inputs));
        bool res = vm.parseJsonBool(result,".status");
        if (!res){
            return false;
        }
        bytes32 hashGenesis = vm.parseJsonBytes32(result,".hash");
        bytes memory rawGenesis = vm.parseJsonBytes(result,".raw");
        uint heightGenesis = vm.parseJsonUint(result,".height");
        // 解析 JSON 结果  
        //console.logBytes32(hashGenesis);
        //console.logBytes(rawGenesis);
        //console.logUint(heightGenesis);
        bytes memory param = abi.encode(heightGenesis);
        bytes memory payload = abi.encodeWithSignature("setGenesisShadowLedgerByManager(bytes,bytes)", rawGenesis,param);
        string memory projectRoot = vm.projectRoot();   
        string memory filePath = string(abi.encodePacked(dataRoot, "BTC.genesis"));   
        string memory data = vm.toString(payload);  
        vm.writeFile(filePath, data);  
        console.log("Genesis payload saved to", filePath); 
        return true;  
    }  
}  