// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "src/HUB/MultiChainManager.sol";

contract CheckState is Script {
    string env;
    string dataRoot;
    
    function run() public {
        // 1. 设置环境和加载合约地址
        env = vm.envString("DEPLOY_ENV");
        string memory projectRoot = vm.projectRoot();
        dataRoot = string(abi.encodePacked(projectRoot, "/data/", env, "/"));
        
        string memory filePath = string(abi.encodePacked(dataRoot, "Manager.address"));
        address managerAddr = vm.parseAddress(vm.readFile(filePath));
        MultiChain manager = MultiChain(managerAddr);
        
        // 2. 查询 BTC 链信息
        uint256 btcChainID = manager.getSourceChainIDBySymbol("BTC");
        
        if (btcChainID == 0) {
            console.log("BTC Chain not found!");
            return;
        }

        // getSourceChainInfo 返回: (symbol, name, state, numContracts, addresses)
        (string memory symbol,, uint256 state,,) = manager.getSourceChainInfo(btcChainID);
        
        console.log("-----------------------------------");
        console.log("Checking Chain Info for:", symbol);
        console.log("Chain ID:", btcChainID);
        console.log("Current State:", state);
        
        if (state == 1) console.log("Status: Initial (1)");
        else if (state == 2) console.log("Status: Write/Active (2)");
        else if (state == 3) console.log("Status: Pause (3)");
        else if (state == 4) console.log("Status: Stop (4)");
        else console.log("Status: Unknown");
        console.log("-----------------------------------");
    }
}
