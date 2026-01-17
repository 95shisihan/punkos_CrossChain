// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {SystemContract} from "./abstracts/AbstractSystemContract.sol"; 
/// @title MultiChain
/// @author Yifu Geng
/// @notice This is a the most special system contract in CrosschainZone
/// @notice This contract records information of hubchain, all sourcechains, and all other system contracts in CrosschainZone
/// @notice This contract should be the manager of all other system contracts in CrosschainZone
/// @notice This contract's manager should be deployed in GovernmentZone 
contract MultiChain is SystemContract{
    uint256 public sourceChainNum;
    uint256 public systemContractNum;
    struct SystemContractInfo{
        uint contractID;
        uint chainID;
        uint levelID;
        uint state;
    }
    struct HubChainInfo{//记录主链信息
        uint chainID;
        string symbol;
        string name;
        uint256 numSystemContract;
    }
    struct SourceChainInfo{//各个源链信息
        uint chainID;
        string symbol;
        string name;
        uint chainState;//0-default;1-initial;2-write;3-pause;4-stop
        uint256 numSystemContract;
    }
    //数据映射
    HubChainInfo public hubChain; 
    mapping(uint256 => SourceChainInfo) public sourceChains;
    mapping(string => uint256) public sourceChainIndex;
    mapping(address => SystemContractInfo) public systemContracts;
    mapping(uint256 => address) public systemContractIndex;
    mapping(uint256 => mapping(uint256 => address)) public contract_chain_index;
    
    enum Item{
        Default,
        HubChain,
        SourceChain,
        MultiContract,
        SystemContract
    }
    error CallSystemContractFailure(address _address, string _operation);
    error NonExistentOperatedItem(Item _item, string _operation);
    error ConflictOperation(Item _item, string _operation);

    event UpdateChainInfo(uint256 indexed _chainID);
    event UpdateContractInfo(uint256 indexed _contractID);
    ///@notice Constructor sets the deployer as the initial manager, records hubchain with chainID = 0, records itself with contractID = 0
    constructor() SystemContract(){//构造函数，把MultiChain合约作为第一个系统合约加入
        hubChain = HubChainInfo({
            chainID: 0,
            symbol: "HC",
            name: "HubChain",
            numSystemContract: 1
        });
        systemContracts[address(this)] = SystemContractInfo({
            contractID: 0,
            chainID: 0,
            levelID: 0,
            state: 1
        });
        systemContractIndex[0] = address(this);
        contract_chain_index[0][0] = address(this);
        systemContractNum = 1;
    }
    ///@notice This function updates the information of hubchain
    ///@param _symbol The new symbol of hubchain, which is usually composed of three to five uppercase letters. Input new value if modify, while input old value if not
    ///@param _name The new full name of hubchain. Input new value if modify, while input old value if not
    function updateHubChainInfo(
        string memory _symbol,
        string memory _name
        ) external onlyManager{//仅管理员可改主链符号和名称
        hubChain.symbol = _symbol;
        hubChain.name = _name;
        emit UpdateChainInfo(0);
    }
    ///@notice This function records the information of a new sourcechain
    ///@param _symbol The unique symbol of sourcechain, which is usually composed of three to five uppercase letters. 
    ///@param _name The full name of sourcechain
    ///@dev The new sourcechain will gets its own chainID, which equals to the number of sourcechains when it registers
    function addNewSourceChain(//增加源链
        string memory _symbol,
        string memory _name
        ) external onlyManager{//external 表示只能从外部调用  onlyManger 表示限制只能由合约的管理员调用
        if(sourceChainIndex[_symbol] != 0){
            revert ConflictOperation(Item.SourceChain, "Symbol");//源链 symbol 不能重复
        }
        sourceChainNum += 1;//新链的唯一 ID
        sourceChains[sourceChainNum] = SourceChainInfo({
            chainID: sourceChainNum,
            symbol: _symbol,//链的简写
            name: _name,//链的名称
            chainState: 1,//默认都是 1
            numSystemContract: 0//当前链下登记的合约
        });
        sourceChainIndex[_symbol] = sourceChainNum;
        emit UpdateChainInfo(sourceChainNum);
        
    }
    ///@notice This function undates the information of an existed sourcechain
    ///@param _chainID The index to locate the sourcechain to be updated
    ///@param _symbol The unique symbol of sourcechain. Input new value if modify, while input old value if not
    ///@param _name The full name of sourcechain. Input new value if modify, while input old value if not
    ///@param _state The state of sourcechain. Input new value if modify, while input old value if not
    ///@dev Mustn't modify chainID
    ///@dev Mustn't modify hubchain through this function with inputed chainID = 0
    function updateSourceChainInfo(//更新源链
        uint _chainID,
        string memory _symbol,
        string memory _name,
        uint _state
        ) external onlyManager{
        SourceChainInfo storage source = sourceChains[_chainID];
        if(source.chainState == 0){
            revert NonExistentOperatedItem(Item.SourceChain,"ChainID");
        }
        if(keccak256(bytes(source.symbol)) != keccak256(bytes(_symbol))){
            if(sourceChainIndex[_symbol] != 0){
                revert ConflictOperation(Item.SourceChain,"Symbol");
            }
            sourceChainIndex[source.symbol] = 0;
            sourceChainIndex[_symbol] = _chainID;
            source.symbol = _symbol;
        }
        source.name = _name;
        source.chainState = _state;
        emit UpdateChainInfo(_chainID);
    }
    ///@notice This function adds a new system contract and binds it to hubchain
    ///@param _address The address of system contract to be added
    ///@dev This function will write system contract to set chainID = 0 and contractState = 1
    function addNewSystemContractToHubChain(//添加合约到HubChain
        address _address
        ) external onlyManager{
        if(systemContracts[_address].state != 0){
            revert ConflictOperation(Item.SystemContract,"Address");
        }
        systemContractIndex[systemContractNum] = _address;
        systemContracts[_address] = SystemContractInfo({
            contractID: systemContractNum,
            chainID: 0,
            levelID: hubChain.numSystemContract,
            state: 1
        });
        contract_chain_index[0][hubChain.numSystemContract] = _address;
        bytes memory payload = abi.encodeWithSignature("updateChainID(uint256)",0);
        (bool success, ) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "ChainID");
        }
        payload = abi.encodeWithSignature("updateLevelID(uint256)",hubChain.numSystemContract);
        (success, ) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "LevelID");
        }
        payload = abi.encodeWithSignature("updateContractState(uint256)", 1);
        (success, ) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "State");
        }
        hubChain.numSystemContract += 1;
        emit UpdateChainInfo(0);
        emit UpdateContractInfo(systemContractNum);
        systemContractNum += 1;
    }
    ///@notice This function adds a new system contract and binds it to existed sourcechain
    ///@param _chainID The index to locate the sourcechain
    ///@param _address The address of system contract to be added
    ///@dev This function will write system contract to set chainID = _chainID and contractState = 1
    ///@dev Mustn't add to hubchain through this function with inputed chainID = 0
    ///@dev Mustn't add to unexisted sourcechain
    function addNewSystemContractToSourceChain(//添加合约到源链
        uint _chainID,
        address _address
        ) external onlyManager{
        if(systemContracts[_address].state != 0){
            revert ConflictOperation(Item.SystemContract,"Address");
        }
        SourceChainInfo storage source = sourceChains[_chainID];
        // --- 新增对废弃链的判断 ---
        if(source.chainState == 0){
            revert NonExistentOperatedItem(Item.SourceChain,"ChainID");
        }
        // 如果链处于 3(Pause) 或 4(Stop)，禁止添加合约
        if(source.chainState > 2) {
             revert ConflictOperation(Item.SourceChain, "ChainState");
        }
        // --- 新增逻辑结束 ---

        systemContractIndex[systemContractNum] = _address;
        systemContracts[_address] = SystemContractInfo({
            contractID: systemContractNum,
            chainID: _chainID,
            levelID: source.numSystemContract,
            state: 1
        });
        contract_chain_index[_chainID][source.numSystemContract] = _address;
        bytes memory payload = abi.encodeWithSignature("updateChainID(uint256)",_chainID);
        (bool success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "ChainID");
        }
        payload = abi.encodeWithSignature("updateLevelID(uint256)",source.numSystemContract);
        (success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "LevelID");
        }
        payload = abi.encodeWithSignature("updateContractState(uint256)",1);
        (success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "State");
        }
        source.numSystemContract += 1;
        emit UpdateChainInfo(_chainID);
        emit UpdateContractInfo(systemContractNum);
        systemContractNum += 1;
    }
    function replaceSystemContract(//替换系统合约
        uint256 _chainID,
        uint256 _levelID,
        address _address
    ) external onlyManager{
        if(systemContracts[_address].state != 0){
            revert ConflictOperation(Item.SystemContract,"Address");
        }
        // if(_chainID != 0){
        //     if(sourceChains[_chainID].chainState == 0){
        //         revert NonExistentOperatedItem(Item.SourceChain,"ChainID");
        // }
        // else{
        //     if(_levelID == 0){
        //         revert ConflictOperation(Item.MultiContract,"Address");
        //     }
        // }
        // }
        // --- 新增/修改逻辑开始 ---
        if(_chainID != 0){
            SourceChainInfo memory source = sourceChains[_chainID];
            if(source.chainState == 0){
                revert NonExistentOperatedItem(Item.SourceChain,"ChainID");
            }
            // 如果链处于 3(Pause) 或 4(Stop)，禁止替换合约
            if(source.chainState > 2){
                revert ConflictOperation(Item.SourceChain, "ChainState");
            }
        } 
        else {
             // 如果是 HubChain (_chainID == 0)，检查 levelID 是否合法
            if(_levelID == 0){
                revert ConflictOperation(Item.MultiContract,"Address");
            }
        }
        // --- 新增/修改逻辑结束 ---

        address oldAddress = contract_chain_index[_chainID][_levelID];
        if(oldAddress == address(0)){
            revert ConflictOperation(Item.SystemContract,"Address");
        }
        bytes memory payload = abi.encodeWithSignature("updateContractState(uint256)",3);
        (bool success,) = oldAddress.call(payload);
        if (!success){
            revert CallSystemContractFailure(oldAddress, "State");
        }
        systemContracts[oldAddress].state = 3;
        emit UpdateContractInfo(systemContracts[oldAddress].contractID);
        systemContractIndex[systemContractNum] = _address;
        systemContracts[_address] = SystemContractInfo({
            contractID: systemContractNum,
            chainID: _chainID,
            levelID: _levelID,
            state: 1
        });
        contract_chain_index[_chainID][_levelID] = _address;
        payload = abi.encodeWithSignature("updateChainID(uint256)",_chainID);
        (success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "ChainID");
        }
        payload = abi.encodeWithSignature("updateLevelID(uint256)",_levelID);
        (success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "LevelID");
        }
        payload = abi.encodeWithSignature("updateContractState(uint256)",1);
        (success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "State");
        }
        emit UpdateChainInfo(_chainID);
        emit UpdateContractInfo(systemContractNum);
        systemContractNum += 1;
    }
    ///@notice This function write existed system contract
    ///@param _address The index to locate the system contract
    ///@param payload The data to be sent from this contract to system contract
    ///@dev This function only writes system contract and don't modify information recorded in this contract
    ///@dev Mustn't operate this contract itself through this function with inputed _address = address(this)
    //这个函数的核心功能就是“代理调用”已注册的系统合约，并执行传入的任意功能，完成对系统合约的操作。
    function operateSystemContract(//操作系统合约
        address _address,
        bytes memory payload
        ) external onlyManager{
        if(_address == address(this)){
            revert ConflictOperation(Item.MultiContract,"Address");
        }
        if(systemContracts[_address].state == 0){
            revert NonExistentOperatedItem(Item.SystemContract,"Address");
        }
        // --- 新增对源链状态的判断 ---
        // 检查合约所属的链是否处于异常状态
        // info.chainID == 0 是 HubChain，默认不检查状态（或者你可以认为它总是活跃）
        SystemContractInfo memory info = systemContracts[_address];
        if (info.chainID != 0) {
            uint chainState = sourceChains[info.chainID].chainState;
            // 0:不存在, 3:Pause, 4:Stop
            if (chainState == 0) {
                 revert NonExistentOperatedItem(Item.SourceChain, "ChainID");
            }
            if (chainState > 2) {
                 revert ConflictOperation(Item.SourceChain, "ChainState");
            }
        }
        // --- 新增逻辑结束 ---

        //对目标合约发起一个交易调用，调用的是 payload 指定的合约函数（以及相关参数）。
        (bool success, bytes memory returnData) = _address.call(payload);
        if (!success){
            // revert CallSystemContractFailure(_address, "Payload");
            // 如果 returnData 有内容，尝试解码并透传
            if (returnData.length > 0) {
                // 这种方式可以把底层的 revert 抛给上层，Foundry 能显示更详细的解码
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            } else {
                revert CallSystemContractFailure(_address, "Payload");
            }
        }
        emit UpdateContractInfo(systemContracts[_address].contractID);
    }
    ///@notice This function modifies contractState of existed system contract
    ///@param _address The index to locate the system contract
    ///@param _state The new state of system contract
    ///@dev This function both writes system contract and updates information recorded in this contract
    ///@dev Mustn't operate this contract itself through this function with inputed _address = address(this)
    function updateSystemContractState(
        address _address,
        uint _state
        ) external onlyManager{
        if(_address == address(this)){
            revert ConflictOperation(Item.MultiContract,"Address");
        }
        if(systemContracts[_address].state == 0){
            revert NonExistentOperatedItem(Item.SystemContract,"Address");
        }
        //链上调用目标合约的 updateContractState(uint256) 方法
        bytes memory payload = abi.encodeWithSignature("updateContractState(uint256)",_state);
        (bool success,) = _address.call(payload);
        if (!success){
            revert CallSystemContractFailure(_address, "State");
        }
        systemContracts[_address].state = _state;
        emit UpdateContractInfo(systemContracts[_address].contractID);
    }
    ///@notice This function queries the num of existed sourcechains in CrosschainZone
    ///@return num Number of sourcechains
    ///@dev return 0 if only hubchain
    function getSourceChainNum() public view returns (uint256 num){
        num = sourceChainNum;
    }
    ///@notice This function queries the num of existed system contracts in CrosschainZone
    ///@return num Number of system contracts
    ///@dev return 1 if only this contract
    function getSystemContractNum() public view returns (uint num){
        num = systemContractNum;
    }
    ///@notice This function queries the information of hubchain
    ///@return chainID Hubchain's chainID equals to 0
    ///@return symbol Symbol of hubchain
    ///@return name Name of hubchain
    ///@return numSystemContract Number of system contracts binded to hubchain
    ///@return addressSystemContract List of addresses of system contracts binded to hubchain
    ///@dev If only this contract, numSystemContract = 0 and addressSystemContract = NULL
    function getHubChainInfo() 
        public
        view
        returns (
            uint256 chainID,
            string memory symbol,
            string memory name,
            uint numSystemContract,
            address[] memory addressSystemContract
        ){
        chainID = hubChain.chainID;
        symbol = hubChain.symbol;
        name = hubChain.name;
        numSystemContract = hubChain.numSystemContract;
        addressSystemContract = new address[] (numSystemContract);
        for (uint i = 0; i < numSystemContract; i ++){
           addressSystemContract[i] = contract_chain_index[0][i];
        }
    }
    ///@notice This function queries the information of sourcechain
    ///@param chainID The index to locate sourcechain
    ///@return symbol Symbol of sourcechain
    ///@return name Name of sourcechain
    ///@return state State of sourcechain
    ///@return numSystemContract Number of system contracts binded to sourcechain
    ///@return addressSystemContract List of addresses of system contracts binded to sourcechain
    ///@dev If query hubchain and unexisted sourcechain with wrong inputted chainID, default data will be returned
    function getSourceChainInfo(uint256 chainID) 
        public
        view
        returns (
            string memory symbol,
            string memory name,
            uint256 state,
            uint256 numSystemContract,
            address[] memory addressSystemContract
            ){
        SourceChainInfo memory source = sourceChains[chainID];
        symbol = source.symbol;
        name = source.name;
        state = source.chainState;
        numSystemContract = source.numSystemContract;
        addressSystemContract = new address[] (numSystemContract);
        for (uint i = 0; i < numSystemContract; i ++){
           addressSystemContract[i] = contract_chain_index[chainID][i];
        }
    }
    ///@notice This function queries the chainID of sourcechain by symbol
    ///@param _symbol Symbol of sourcechain
    ///@return chainID ChainID of sourcechain
    ///@dev If query with symbol of hubchain and unexisted sourcechain, return 0
    function getSourceChainIDBySymbol(string memory _symbol) public view returns (uint256 chainID){
        chainID = sourceChainIndex[_symbol];
    }
    ///@notice This function queries the information of system contract
    ///@param _address Address of system contract
    ///@return contractID ID of the system contract
    ///@return chainID ID of blockchain that system contract belongs to
    ///@return levelID Index of system contract in its binded blockchain
    ///@return state State of system contract
    ///@dev Don't suggest query this contract by the function
    ///@dev Query unexisted system contract will get default data.
    function getSystemContractInfo(address _address)
        public
        view
        returns (
            uint contractID,
            uint chainID,
            uint levelID,
            uint state
        ){
        if (_address == address(this)){
            contractID = 0;
            chainID = this.getChainID();
            levelID = 0;
            state = this.getContractState();
        }
        else{
            SystemContractInfo memory targetContract = systemContracts[_address];
            contractID = targetContract.contractID;
            chainID = targetContract.chainID;
            levelID = targetContract.levelID;
            state = targetContract.state;
        }
    }
    ///@notice This function queries the address of system contract by contractID
    ///@param _contractID ContractID of the system contract
    ///@return _address The deployed address of system contract
    ///@dev Query unexisted system contract will get default data.
    function getSystemContractAddressByID(uint _contractID) public view returns (address _address){
        _address = systemContractIndex[_contractID];
    }
    ///@notice This function queries the address of system contract by contractID
    ///@param _chainID chainID of hub or source
    ///@param _levelID levelID of the system contract
    ///@return _address The deployed address of system contract
    ///@dev Query unexisted system contract will get default data.
    function getSystemContractAddressByLevelID(uint256 _chainID, uint256 _levelID) public view returns (address _address){
        _address = contract_chain_index[_chainID][_levelID];
    }

        // 增加一个内部辅助函数，用于将单个系统合约状态置为“停止/废弃”
    // 假设 state = 3 代表停止/废弃 (参照 replaceSystemContract 中的逻辑)
    function _disableSystemContract(address _contractAddr) internal {
        // 1. 更新管理合约内的记录
        if (systemContracts[_contractAddr].state != 3) {
             systemContracts[_contractAddr].state = 3;
             emit UpdateContractInfo(systemContracts[_contractAddr].contractID);
        }

        // 2. 外部调用：强制修改目标子合约的状态
        // 这要求子合约必须有 updateContractState 方法，且信任管理合约的调用
        bytes memory payload = abi.encodeWithSignature("updateContractState(uint256)", 3);
        (bool success, ) = _contractAddr.call(payload);
        
        // 如果调用失败，必须回滚，否则会导致管理合约和子合约状态不一致
        if (!success){
            revert CallSystemContractFailure(_contractAddr, "State");
        }
    }

    ///@notice This function soft-deletes a sourcechain and DISABLES all its contracts
    function deactivateSourceChain(uint256 _chainID) external onlyManager {
        SourceChainInfo storage source = sourceChains[_chainID];

        // 1. 检查链是否存在
        if(source.chainState == 0){
            revert NonExistentOperatedItem(Item.SourceChain, "ChainID");
        }

        // 2. 将链状态修改为 4 (STOP)
        source.chainState = 4;

        // 3. 【核心修改】遍历该链下的所有系统合约，并强制停止它们
        uint256 numContracts = source.numSystemContract;
        for (uint256 i = 0; i < numContracts; i++) {
            address contractAddr = contract_chain_index[_chainID][i];
            // 只有当地址有效且当前未处于停止状态时才调用，节省 gas
            if (contractAddr != address(0)) {
                _disableSystemContract(contractAddr);
            }
        }

        emit UpdateChainInfo(_chainID);
    }

    // 同样逻辑应用到带释放 Symbol 功能的函数中
    function deactivateSourceChainAndFreeSymbol(uint256 _chainID) external onlyManager {
        SourceChainInfo storage source = sourceChains[_chainID];
        if(source.chainState == 0){
            revert NonExistentOperatedItem(Item.SourceChain, "ChainID");
        }
        
        // 1. 清除 Symbol 索引
        delete sourceChainIndex[source.symbol];
        
        // 2. 标记链为 Stop
        source.chainState = 4;
        
        // 3. 【核心修改】强制停止该链下的所有合约
        uint256 numContracts = source.numSystemContract;
        for (uint256 i = 0; i < numContracts; i++) {
            address contractAddr = contract_chain_index[_chainID][i];
            if (contractAddr != address(0)) {
                _disableSystemContract(contractAddr);
            }
        }
        
        emit UpdateChainInfo(_chainID);
    }

        // --- 内部辅助函数：恢复单个系统合约 ---
    function _enableSystemContract(address _contractAddr) internal {
        // 1. 更新管理合约内的记录 ( 2 代表正常工作状态)
        if (systemContracts[_contractAddr].state != 2) {
             systemContracts[_contractAddr].state = 2;
             emit UpdateContractInfo(systemContracts[_contractAddr].contractID);
        }

        // 2. 外部调用：强制恢复目标子合约的状态
        bytes memory payload = abi.encodeWithSignature("updateContractState(uint256)", 2);
        (bool success, ) = _contractAddr.call(payload);
        
        // 必须确保调用成功，保持状态一致
        if (!success){
            revert CallSystemContractFailure(_contractAddr, "State");
        }
    }

    // --- 主功能：恢复源链及其下属合约 ---
    ///@notice This function reactivates a stopped sourcechain and ENABLES all its contracts
    ///@param _chainID The index to locate the sourcechain to be reactivated
    function reactivateSourceChain(uint256 _chainID) external onlyManager {
        SourceChainInfo storage source = sourceChains[_chainID];

        // 1. 检查链是否存在
        if(source.chainState == 0){
            revert NonExistentOperatedItem(Item.SourceChain, "ChainID");
        }

        // 2. 检查符号冲突 (关键逻辑)
        // 如果之前调用了 deactivateSourceChainAndFreeSymbol，Symbol 索引可能被删除了
        // 这里需要检查该 Symbol 是否被其他新链占用了
        uint256 existingID = sourceChainIndex[source.symbol];
        
        if (existingID == 0) {
            // 情况 A: Symbol 索引为空，说明之前被释放了，现在重新认领
            sourceChainIndex[source.symbol] = _chainID;
        } 
        else if (existingID != _chainID) {
            // 情况 B: Symbol 索引存在，但指向了别的链 ID (说明这段时间里有新链用了这个名字)
            // 此时无法恢复，因为 Symbol 冲突，必须报错
            revert ConflictOperation(Item.SourceChain, "SymbolTaken");
        }
        // 情况 C: existingID == _chainID，说明之前只是普通 deactivate，索引还在，无需操作

        // 3. 将链状态改回  2 (Write)
        source.chainState = 2;

        // 4. 遍历并激活该链下的所有系统合约
        uint256 numContracts = source.numSystemContract;
        for (uint256 i = 0; i < numContracts; i++) {
            address contractAddr = contract_chain_index[_chainID][i];
            if (contractAddr != address(0)) {
                _enableSystemContract(contractAddr);
            }
        }

        emit UpdateChainInfo(_chainID);
    }



}