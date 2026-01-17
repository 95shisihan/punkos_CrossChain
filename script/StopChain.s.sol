// script/ManagerDeactivateSource.s.sol
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "src/HUB/MultiChainManager.sol";

// 运行命令：
// forge script script/ManagerDeactivateSource.s.sol:RunScript --rpc-url http://127.0.0.1:8545 --broadcast -vvvv
contract RunScript is Script {
    string public env; 
    uint256 public privateKey; 
    string public dataRoot; 
    string public myName = "Manager"; 
    
    // --- 配置区域 ---
    string public targetSymbol = "BTC"; // 在这里修改你要停用的链符号
    // ----------------

    MultiChain public myContract; 
    address public myAddress; 

    function run() public {
        vm.txGasPrice(tx.gasprice);
        loadDev(); 
        
        console.log("=============== START DEACTIVATION ===============");
        vm.startBroadcast(privateKey);

        // 1. 加载合约
        myAddress = loadContractAddress(myName);
        myContract = MultiChain(myAddress);
        console.log("Manager Contract:", myAddress);

        // 2. 执行逻辑
        deactivateChain(targetSymbol);

        vm.stopBroadcast();
        console.log("=============== END DEACTIVATION ===============");
    }

    function deactivateChain(string memory _symbol) internal {
        // 查找 ID
        uint256 chainID = myContract.getSourceChainIDBySymbol(_symbol);
        if (chainID == 0) {
            console.log("[ERROR] Chain symbol not found:", _symbol);
            return;
        }
        console.log("Target Chain:", _symbol, "| ID:", chainID);

        // 检查当前状态
        (,, uint256 oldState,,) = myContract.getSourceChainInfo(chainID);
        console.log("Old State:", oldState);

        if (oldState == 4) {
            console.log("[SKIP] Chain is already STOPPED (State 4).");
            return;
        }

        // 调用合约
        console.log("Tx: Calling deactivateSourceChain...");
        try myContract.deactivateSourceChain(chainID) {
            console.log("[SUCCESS] Transaction executed.");
            
            // 二次确认
            (,, uint256 newState,,) = myContract.getSourceChainInfo(chainID);
            console.log("New State:", newState);
            if(newState == 4) {
                console.log("Result: Chain and sub-contracts successfully DEACTIVATED.");
            } else {
                console.log("Result: [WARNING] State update check failed?");
            }

        } catch Error(string memory reason) {
            console.log("[FAILED] Reverted with reason:", reason);
        } catch {
            console.log("[FAILED] Reverted with unknown error.");
        }
    }

    // --- 环境加载函数 (不变) ---
    function loadDev() public {
        env = vm.envString("DEPLOY_ENV");
        if (keccak256(abi.encodePacked(env)) == keccak256(abi.encodePacked("dev"))) {
            privateKey = vm.envUint("DEV_PRIVATE_KEY");
        } else if (keccak256(abi.encodePacked(env)) == keccak256(abi.encodePacked("test"))) {
            privateKey = vm.envUint("TEST_PRIVATE_KEY");
        } else {
            revert("Invalid environment");
        }
        string memory projectRoot = vm.projectRoot();
        dataRoot = string(abi.encodePacked(projectRoot, "/data/", env, "/"));
    }

    function loadContractAddress(string memory contractName) internal view returns (address) {
        string memory filePath = string(abi.encodePacked(dataRoot, contractName, ".address"));
        return vm.parseAddress(vm.readFile(filePath));
    }
}
