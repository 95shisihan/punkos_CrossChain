// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;


import {SystemContract} from "./AbstractSystemContract.sol";
import {StakeManagement} from "./AbstractStakeManagement.sol";

abstract contract Transport is SystemContract,StakeManagement{
    address public relayContract;//中继合约地址
    address public txRuleContract;
    uint256 public delay = 8;
    uint public taskNum = 0;//历史传输任务数量
    uint Max_Task_Time = 144;
    
    enum TransportTaskLabel {
        Default, 
        Created,
        Accepted,
        Rejected,
        Successed,
        Failed
    }
    struct TransportTask{
        address user;
        uint96 fee;
        uint taskType;
        address relayer;
        uint96 stake;
        bytes payload;
        uint256 time;
        TransportTaskLabel label;
    }
    
    mapping(bytes32 => TransportTask) public taskList;
    mapping(uint256 => bytes32) public taskIndex;
    mapping(bytes32 => bool) public txIfCheck;
    

    event NewTransportTask(uint256 indexed _index, bytes32 indexed _key, bytes _payload, uint256 _type, address user, uint fee);
    event UpdateTaskState(bytes32 indexed _key, TransportTaskLabel oldState, TransportTaskLabel indexed newState, address indexed operator);
    event ConfirmSourceTx(bytes32 indexed keyTx, bytes32 indexed keyShadowBlock, uint confirmParam, bool _type);


    function updateSourceInfo(address _relay, address _txRule) external onlyManager{
        relayContract = _relay;
        txRuleContract = _txRule;
    }

    function getCrossFee(bytes memory rawTx) public pure returns(uint fee) {
        uint CROSS_FEE_PER_BYTE = 10;
        fee = CROSS_FEE_PER_BYTE * rawTx.length;
    }

    //用户创建任务
    /// @notice user creats a new transport task
    /// @param _payload the data that user wants to send to source chain
    /// @param _taskType the type to check if input _paylaod matches raw tx
    function createTask(bytes memory _payload, uint256 _taskType) external payable onlyWorking {
        bytes32 taskKey = keccak256(_payload);
        if(taskList[taskKey].label != TransportTaskLabel.Default){
            revert();
        }
        taskList[taskKey] = TransportTask({
            user: msg.sender,
            fee: uint96(msg.value),
            taskType: _taskType,
            relayer: address(0),
            stake: uint96(0),
            payload: _payload,
            time: block.number,
            label: TransportTaskLabel.Created
        });
        taskIndex[taskNum] = taskKey;
        emit NewTransportTask(taskNum, taskKey, _payload, _taskType, msg.sender, msg.value);
        taskNum += 1;
    }
    /// @notice relayer accepts a new transport task
    /// @param _taskKey the key of task which equals to the hash of payload to be transported
    function acceptTask(bytes32 _taskKey) external onlyWorking onlyRelayer{
        TransportTask storage task = taskList[_taskKey];
        if(task.label != TransportTaskLabel.Created){
            revert();
        }
        lockStake(msg.sender, getRequireStake());
        task.relayer = msg.sender;
        task.label = TransportTaskLabel.Accepted;
        task.time = block.number;
        task.stake = uint96(getRequireStake());
        emit UpdateTaskState(_taskKey, TransportTaskLabel.Created, TransportTaskLabel.Accepted, msg.sender);
    }
    /// @notice relayer proves that he has finished a transport task
    /// @param _taskKey 传输任务哈希
    /// @param rawTx 上链的交易源数据
    /// @param leafNode 交易默克尔证明的叶子
    /// @param proof 交易默克尔证明的路径
    /// @param keyShadowBlock 交易默克尔根所在影子区块索引
    function finishTask(bytes32 _taskKey, bytes calldata rawTx, bytes calldata leafNode, bytes calldata proof, bytes32 keyShadowBlock) public returns (bool res){
        TransportTask memory task = taskList[_taskKey];
        if((task.label != TransportTaskLabel.Accepted) || (task.relayer != msg.sender)) {
            revert();
        }
        bool success;
        bytes memory data;
        bytes memory payload = abi.encodeWithSignature("checkIfPayloadMatchTx(bytes,bytes,uint)",task.payload,rawTx,task.taskType);
        (success,) = txRuleContract.call(payload);
        if (!success){
            revert ();
        }
        payload = abi.encodeWithSignature("checkIfLeafNodeMatchTx(bytes, bytes)",leafNode,rawTx);
        (success,) = txRuleContract.call(payload);
        if (!success){
            revert ();
        }
        payload = abi.encodeWithSignature("getKeyFromRawTx(bytes)",rawTx);
        (success, data) = txRuleContract.call(payload);
        if (!success){
            revert ();
        }
        bytes32 keyTx = abi.decode(data,(bytes32));
        if(txIfCheck[keyTx]){
            revert ();
        }
        payload = abi.encodeWithSignature("verifyTxByShadowLedger(bytes,bytes,bytes32,uint256)",leafNode,proof,keyShadowBlock,delay);
        (success, data) = relayContract.call(payload);
        if (!success){
            revert ();
        }
        res = abi.decode(data,(bool));
        if (!res){
            return res;
        }
        txIfCheck[keyTx] = true;
        emit ConfirmSourceTx(keyTx, keyShadowBlock, delay, false);
        emit UpdateTaskState(_taskKey, TransportTaskLabel.Accepted, TransportTaskLabel.Successed, msg.sender);
        uint256 reward = uint256(task.fee + task.stake);
        unlockStake(task.relayer, reward);
        delete taskList[_taskKey];
        return true;
    }
    /// @notice If a relayer does not finish his task uintil time-out, another relayer can re-accept the task 
    /// @param _taskKey the key of task which equals to the hash of payload to be transported
    function reAcceptTask(bytes32 _taskKey) external onlyWorking onlyRelayer {
        TransportTask storage task = taskList[_taskKey];
        if(task.label != TransportTaskLabel.Accepted){
            revert();
        }
        if(block.number - task.time <= Max_Task_Time){
            revert();
        }
        if(task.relayer == msg.sender){
            revert();
        }
        punishLockedRelayer(task.relayer, task.stake);
        lockStake(msg.sender, getRequireStake());
        task.relayer = msg.sender;
        task.time = block.number;
        emit UpdateTaskState(_taskKey, TransportTaskLabel.Accepted, TransportTaskLabel.Accepted, msg.sender);
    }
    /// @notice A user can withdraw his task before accepted or after relayer times out
    /// @param _taskKey the key of task which equals to the hash of payload to be transported
    function withdrawTask(bytes32 _taskKey) external {
        TransportTask memory task = taskList[_taskKey];
        if(task.user != msg.sender){
            revert ();
        }
        if(task.label == TransportTaskLabel.Created){
            payable(msg.sender).transfer(uint256(task.fee));
            emit UpdateTaskState(_taskKey, TransportTaskLabel.Created, TransportTaskLabel.Rejected, msg.sender);
            delete taskList[_taskKey];
        }
        else if((task.label == TransportTaskLabel.Accepted)&&(block.number - task.time > Max_Task_Time)){
            payable(msg.sender).transfer(uint256(task.fee));
            punishLockedRelayer(task.relayer,task.stake);
            emit UpdateTaskState(_taskKey, TransportTaskLabel.Accepted, TransportTaskLabel.Failed, msg.sender);
            delete taskList[_taskKey];
        }
        else{
            revert();
        }
    }
    function getSourceInfo() public view returns (address,address){
        return (relayContract,txRuleContract);
    }
    function getTaskNum() public view returns (uint){
        return taskNum;
    }
    function getTaskKeyByIndex(uint _index) public view returns (bytes32 _taskKey){
        _taskKey = taskIndex[_index];
    }
    function getTaskInfoByKey(bytes32 _taskKey)
        public
        view
        returns (
            address user,
            uint256 fee,
            uint256 taskType,
            address relayer,
            uint256 stake,
            bytes memory payload,
            TransportTaskLabel label,
            uint256 time
        ){
        TransportTask memory task = taskList[_taskKey];
        user = task.user;
        fee = uint256(task.fee);
        taskType = task.taskType;
        relayer = task.relayer;
        stake =  uint256(task.stake);
        payload = task.payload;
        label = task.label;
        time = task.time;
    } 
    function getTaskInfoByIndex(uint256 _index)
        public
        view
        returns (
            address user,
            uint256 fee,
            uint256 taskType,
            address relayer,
            uint256 stake,
            bytes memory payload,
            TransportTaskLabel label,
            uint256 time
        ){
        return getTaskInfoByKey(getTaskKeyByIndex(_index));
    } 
    
}
