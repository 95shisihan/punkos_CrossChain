// script/ManagerReactivateSource.s.sol
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "src/HUB/MultiChainManager.sol";

// 运行命令：
// forge script script/ManagerReactivateSource.s.sol:RunScript --rpc-url http://127.0.0.1:8545 --broadcast -vvvv
contract RunScript is Script {
    string public env; 
    uint256 public privateKey; 
    string public dataRoot; 
    string public myName = "Manager"; 
    
    // --- 配置区域 ---
    string public targetSymbol = "BTC"; // 在这里修改你要恢复的链符号
    // ----------------

    MultiChain public myContract; 
    address public myAddress; 

    function run() public {
        vm.txGasPrice(tx.gasprice);
        loadDev(); 
        
        console.log("=============== START REACTIVATION ===============");
        vm.startBroadcast(privateKey);

        myAddress = loadContractAddress(myName);
        myContract = MultiChain(myAddress);
        console.log("Manager Contract:", myAddress);

        reactivateChain(targetSymbol);

        vm.stopBroadcast();
        console.log("=============== END REACTIVATION ===============");
    }

    function reactivateChain(string memory _symbol) internal {
        uint256 chainID = myContract.getSourceChainIDBySymbol(_symbol);
        
        // 这里的判断逻辑稍微不同：如果 chainID 是 0，可能是还没注册，也可能是之前释放了 Symbol
        // 如果是释放了 Symbol，getSourceChainIDBySymbol 会查不到。
        // 但由于 reactivateSourceChain 需要 chainID 参数，我们假设 Symbol 没被释放，或者你知道 ID。
        // 如果 Symbol 查不到 ID，手动填入 ID 进行恢复也是一种办法，这里默认通过 Symbol 查。
        if (chainID == 0) {
            console.log("[ERROR] Chain symbol not found:", _symbol);
            console.log("Hint: If you freed the symbol, you might need to recover by raw Chain ID.");
            return;
        }
        
        console.log("Target Chain:", _symbol, "| ID:", chainID);

        (,, uint256 oldState,,) = myContract.getSourceChainInfo(chainID);
        console.log("Old State:", oldState);

        // 如果状态不是 4，可能没必要恢复（或者它本身就是 1, 2, 3）
        if (oldState != 4) {
            console.log("[INFO] Chain is NOT in STOP state (State 4). Proceeding anyway...");
        }

        console.log("Tx: Calling reactivateSourceChain...");
        try myContract.reactivateSourceChain(chainID) {
            console.log("[SUCCESS] Transaction executed.");

            // 验证状态是否变回 1 (Active)
            (,, uint256 newState,,) = myContract.getSourceChainInfo(chainID);
            console.log("New State:", newState);
            
            if(newState == 1) {
                console.log("Result: Chain and sub-contracts successfully REACTIVATED.");
            } else {
                console.log("Result: [WARNING] State update check unexpected (Not 1).");
            }
        } catch Error(string memory reason) {
            console.log("[FAILED] Reverted with reason:", reason);
        } catch {
            console.log("[FAILED] Reverted with unknown error.");
        }
    }

    // --- 环境加载 (同上) ---
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
