// deploy.sol  
pragma solidity ^0.8.0;  

import "forge-std/Script.sol";  
import "src/BTC/RelayContract.sol";
import "src/HUB/MultiChainManager.sol";
//forge script script/BTC_Relay.s.sol:RunScript --rpc-url http:127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast -vvvv
contract RunScript is Script {  
    string public env;//当前环境
    uint256 public privateKey;//使用的私钥
    string public dataRoot;//数据文件根目录
    string public myName = "BTC";//当前链名
    address public myAddress;//BTC_Relay的合约地址
    BTC_Relay public myContract;//BTC_Relay的合约实例

    string public managerName = "Manager";
    address public managerAddress;
    MultiChain public managerContract;//MultiChainManager的合约实例
    function run() public {  //整个脚本的核心执行流程
        vm.txGasPrice(tx.gasprice);
        loadDev();//加载环境配置
        vm.startBroadcast(privateKey);
        managerAddress = loadContractAddress(managerName);
        managerContract = MultiChain(managerAddress);
        console.log("1");
        if (!checkIfRelayWork()){//检查中继是否处于工作状态
            vm.stopBroadcast();
            return;
        }
        console.log("2");
        if (!checkIfRelayer()){//检查是否为合格中继者（stake是否足够，即质押代币是否足够）
            vm.stopBroadcast();
            return;
        }
        console.log("3");
        //withdrawStake();
        relayBlock();//执行区块中继逻辑
        vm.stopBroadcast(); 
    } 
    function loadDev() public{//环境加载函数
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
    function loadContractAddress(string memory contractName) internal view returns (address){  //加载合约地址
        //Foundry中每次部署后把合约地址写入文件，下次执行脚本时直接从文件读取  
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));   
        return vm.parseAddress(vm.readFile(filePath));  
    }
    function checkIfRelayWork() internal returns (bool){//检查中继状态，是否在工作
        uint256 myChainID = managerContract.getSourceChainIDBySymbol(myName);
        //uint256 myChainID = 2;
        uint256 myLevelID = 0;
        //通过MultiChainManager获取BTC_Relay的地址，读取其中的合约状态，如果状态码为2，则表示中继工作正常
        myAddress = managerContract.getSystemContractAddressByLevelID(myChainID,myLevelID);
        myContract = BTC_Relay(myAddress);
        if(myContract.getContractState() == 2){
            return true;
        }  
        return false;
    }
    function checkIfRelayer() internal returns (bool){//检查是否是中继者，判断质押数量是否足够
        uint256 myStake = myContract.getMyStake();
        uint256 targetStake = 2 * myContract.getRequireStake();
        
        if(myStake >= targetStake){
            return true;
        }
        else{//如果不够，自动调用becomeRelay（）来补齐质押
            uint newStake = targetStake - myStake;
            myContract.becomeRelayer{value: newStake}();
            myStake = myContract.getMyStake();
            if(myStake >= targetStake){
                return true;
            }
        }
        return false;
    }
    function relayBlock() internal returns (bool){//中继区块主逻辑
        uint256 topHeight = myContract.getTopHeight();//当前中继的最高比特币高度
        bytes32 topKey = myContract.getTopKeyFromShadowLedger();//获取影子账本顶层块的hash，账本顶层key
        console.log("TopHeight:",topHeight);
        (bytes32 key, bytes memory raw) = getBlockHeaderFromHeight(topHeight + 1);
        //console.logBytes32(key);
        //console.logBytes32(topKey);
        bytes32 v = myContract.getCommitState(key,topKey);//根据v判断自己是不是第一个中继者
        //console.logBytes32(v); 
        //要同步新的比特币区块头，更新链上影子账本
        if (v == bytes32(0)){
            console.log("I am the first relayer");
            (bytes32 keyOld, bytes memory rawOld) = getBlockHeaderFromHeight(topHeight);
            myContract.updateShadowLedgerByRelayer{gas:1000000}(rawOld,key,keccak256(abi.encodePacked(raw,vm.addr(privateKey))));
        }
        else{
            console.log("I am not the first relayer");
            (bytes32 keyNew, bytes memory rawNew) = getBlockHeaderFromHeight(topHeight + 2);
            //这里同步时比第一个中继者处理的区块高两个高度，为topHeight + 2，用于和第一个中继者的区块形成链，避免重复工作
            myContract.updateShadowLedgerByRelayer{gas:1000000}(raw,keyNew,keccak256(abi.encodePacked(rawNew,vm.addr(privateKey))));
        } 
        return true;    
    }
    function withdrawStake() internal returns (bool){//
        uint256 myStake = myContract.getMyStake();
        myContract.withdrawStake(myStake);
        console.log("My stake is:", myContract.getMyStake());
        return true;
    }
    function getBlockHeaderFromHeight(uint256 height) public returns (bytes32 key, bytes memory raw) {  
        // 准备 Python 脚本调用  
        string[] memory inputs = new string[](3);  
        //inputs[0] = "python3";  
        string memory pythonPath = vm.envString("PYTHON_PATH");
        inputs[0] = pythonPath;
        inputs[1] = "./script/get_BTC_Header.py";
        inputs[2] = vm.toString(height);   
        
        // 执行脚本  
        string memory result = string(vm.ffi(inputs));
        bool status = vm.parseJsonBool(result,".status");
        if (!status){
            revert();
        }
        key = vm.parseJsonBytes32(result,".hash");
        raw = vm.parseJsonBytes(result,".raw");
        //myContract.updateShadowLedgerByRelayer{gas:1000000}(rawPrev,keyShadowBlock,keccak256(abi.encodePacked(rawShadowBlock,vm.addr(privateKey)))); 
    }
}  