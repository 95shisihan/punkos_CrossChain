// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import "forge-std/Script.sol";  
import {SourceConsensusRules} from "./AbstractSourceRules.sol";
import {SystemContract} from "./AbstractSystemContract.sol";
import {StakeManagement} from "./AbstractStakeManagement.sol";
/**
 * @title AbstractRelayContract
 * @dev This contract implements the incentive design for trustless cross-chain relay.
 * It rewards honest relayers while punish attackers, and includes the fee design for relay users. 
 */
abstract contract RelayContract is SystemContract,StakeManagement,SourceConsensusRules{
    
    enum ContributionLabel{//记录各种贡献/操作类型
        Default,
        Submit_New_Commit,
        Open_True_Commit,
        Open_False_Commit,
        Open_Fork_True_Commit,
        Open_Fork_False_Commit,
        Delete_Time_Out_Commit,
        Called_By_User,
        Commit_Opened_True,
        Commit_Opened_False,
        Commit_Time_Out,
        Gas_Not_Enough,
        Submit_Wrong_Data,
        Wrongly_Open_Fork_Commit
    }
    
    struct CommitBlock{//以 child shadow block 的 key 为索引,用于记录针对不同 parent 的提交分支。
        address relayer;                                //The address of relayer eventually binding to the shadow block. The address will receive relayer subsidy and relay fee.
        mapping(bytes32 => CommitMemory) commitFork;    //Records the commit information of a shadow block and stake of the committer. The index is the key of parent shadow block.
    }
    struct CommitMemory{//对某一父子关系（child key 对 parent key）的提交信息
        address relayer;                                //The relayer who commits the shadow block
        uint96 stake;                                   //The stake of relayer binding to the commit
        bytes32 commit;                                 //The value of commit which should equal to keccak256(rawShadowBlock,relayer)
        uint256 time;                                   //The time when relayer submits the commit, which is used to punish relayer if it can not be opened 
    }
    bytes32 public keyGenesisShadowBlock;//记录 genesis 的 key。
    ///@notice A mapping from unique key of shadowblock to its relayer and committer information
    mapping (bytes32 => CommitBlock) public commitTree; //按 childKey 存储 CommitBlock。
    ///@notice A mapping from relayer addresses to their unlocked stake
       
    
    uint256 public MaxOpenCommitDelay;
    uint256 public GasLowerBound;
    
    event SubmitNewCommit(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, address indexed relayer, bytes32 commit);
    event OpenOldCommit(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, address indexed relayer, bool result);

    event RecordRelayerContribution(bytes32 indexed keyShadowBlock, address indexed relayer, ContributionLabel indexed label,uint value);
    event RecordRelayerCost(bytes32 indexed keyShadowBlock, address indexed relayer, RelayerLabel indexed label, uint value);
    event UpdateShadowLedger(bytes32 indexed keyShadowBlock, bytes32 keyParentShadowBlock, bytes rawShadowBlock);
    event UpdateRelayParams(uint indexed flag, uint256 newValue);
    /**  
     * @notice Revert when unexpected condition occurs    
    */ 
    error UnexpectedValue();
    
    error UnAllowedOperation();

    constructor() StakeManagement(){
        GasLowerBound = 10000;
        MaxOpenCommitDelay = 144;
    }
    /**
     * @notice External, read-write and onlyManager functions
    */
    /// @notice Managers Use The Function To Set The Initial State of Relay Contract 
    /// @param _rawGenesisShadowBlock The first source block header to be relayed, which has the same format as following relayers
    /// @param _params The special data only need submitting by managers.
    //管理者设置创世块,会调用 setGenesisShadowBlock（来自父合约）并在 commitTree 上为 genesis 存储 relayer 信息。
    function setGenesisShadowLedgerByManager(
        bytes calldata _rawGenesisShadowBlock,
        bytes calldata _params
        )external onlyManager{
        setGenesisShadowLedgerWithCommit(_rawGenesisShadowBlock, _params, msg.sender);
    }
    
    function setGasLowerBound(uint256 _newBound) external onlyManager{
        GasLowerBound = _newBound;
        emit UpdateRelayParams(2, _newBound);
    }
    function setMaxOpenCommitDelay(uint256 _newDelay) external onlyManager{
        MaxOpenCommitDelay = _newDelay;
        emit UpdateRelayParams(3, _newDelay);
    } 
    
    /**
     * @notice External and write functions that can be operated by anyone
    */
    
    /// @notice Relayers sse this function to update shadow ledger and valid ones will get reward
    /// @param _keyShadowBlock The key of the shadow block from latest source ledger
    /// @param _commitShadowBlock The hash of keyNewShadowBlock and relayer address
    /// @param _rawParentShadowBlock  The raw data of the parent of latest shadow block

    //首先检查 gasleft() 是否高于 GasLowerBound；低于则记录事件并调用 punishUnlockedRelayer（惩罚未锁仓 relayer），返回。
    //根据传入的 _commitShadowBlock 是否为 0 决定调用 submitNewCommit（提交新 commit）还是 openForkCommit（打开分叉）。
    //根据返回的 RelayerLabel（来自父合约/内部逻辑，分为 Valid、Invalid_Honest、Dishonest）做后续处理（记录消耗 gas、惩罚、返回等
    function updateShadowLedgerByRelayer(
        bytes calldata _rawParentShadowBlock,
        bytes32 _keyShadowBlock,
        bytes32 _commitShadowBlock
        ) external onlyWorking onlyRelayer{
        
        uint256 oldGas = gasleft();
        if (oldGas < GasLowerBound){
            emit RecordRelayerContribution(_keyShadowBlock, msg.sender, ContributionLabel.Gas_Not_Enough,getRequireStake());
            punishUnlockedRelayer(msg.sender, getRequireStake());
            return;
        }
        console.log("Gas before processing is okkkkk",oldGas);
        RelayerLabel label = updateShadowLedgerWithCommit(_rawParentShadowBlock,_keyShadowBlock,_commitShadowBlock,msg.sender);
        oldGas = oldGas - gasleft();
        if (label == RelayerLabel.Dishonest){
            console.log("I am dishonest relayer");
            punishUnlockedRelayer(msg.sender, getRequireStake());
            return;
        }
        else if (label == RelayerLabel.Invalid_Honest){
            emit RecordRelayerCost(_keyShadowBlock, msg.sender, label, oldGas);
            return;
        }
        else if (label == RelayerLabel.Valid){
            emit RecordRelayerCost(_keyShadowBlock, msg.sender, label, oldGas);
            return;
        }
        else{
            revert UnexpectedValue();
        }
    }
    function callShadowLedgerByUser(bytes calldata _leafNode, bytes calldata _proof, bytes32 _rootKey, uint _delay) external returns (bool success){
        success = verifyTxByShadowLedger(_leafNode, _proof, _rootKey, _delay);
        emit RecordRelayerContribution(_rootKey, commitTree[_rootKey].relayer, ContributionLabel.Called_By_User,0);
        return success;
    }
    function openTimeOutCommitByChallenger(
        bytes32 _keyParent,
        bytes32 _keyChild
        )external onlyWorking{
        //check whether relayer has deposit here
        uint256 oldGas = gasleft();
        RelayerLabel label = openTimeOutCommit(_keyParent,_keyChild,msg.sender);
        oldGas = oldGas - gasleft();
        if (label == RelayerLabel.Dishonest){
            revert UnAllowedOperation();
        }
        else if (label == RelayerLabel.Invalid_Honest){
            //emit RecordRelayerCost(_keyChild, msg.sender, label, oldGas);
            revert UnAllowedOperation();
        }
        else if (label == RelayerLabel.Valid){
        }
        else{
            revert UnexpectedValue();
        }
    }
    /**
     * @notice External, only-read functions
    */
    
    
    function getGasLowerBound() public view returns (uint256){
        return GasLowerBound;
    }
    function getMaxOpenCommitDelay() public view returns (uint256){
        return MaxOpenCommitDelay;
    }
    function getCommitInfo(bytes32 _keyChild, bytes32 _keyParent)
        public
        view
        returns(
            address relayer,
            uint256 stake,
            bytes32 commit,
            uint256 time
        ){
        CommitMemory memory cm = commitTree[_keyChild].commitFork[_keyParent];
        relayer = cm.relayer;
        stake = uint256(cm.stake);
        commit = cm.commit;
        time = cm.time;
    }
    function getGenesisKey() public view returns (bytes32){
        return keyGenesisShadowBlock;
    }
    /**
     * @notice Internal functions
    */
    function setGenesisShadowLedgerWithCommit(
        bytes calldata _rawGenesisBlock,
        bytes calldata _params,
        address _relayer
        )internal{
        bytes32 keyGenesis = getKeyFromShadowBlock(_rawGenesisBlock);
        bool res = setGenesisShadowBlock(_rawGenesisBlock, _params);
        if(res){
            bytes32 keyParentGenesis;
            emit UpdateShadowLedger(keyGenesis, keyParentGenesis, _rawGenesisBlock);
            storeGenesisCommit(_rawGenesisBlock, keyGenesis, _relayer, keyParentGenesis);
            keyGenesisShadowBlock = keyGenesis;
        }
        else{
            revert();
        }
    }

    function updateShadowLedgerWithCommit(
        bytes calldata _rawParentShadowBlock,
        bytes32 _keyShadowBlock,
        bytes32 _commitShadowBlock,
        address _relayer
        )internal returns (RelayerLabel label){
        if(_commitShadowBlock == bytes32(0)){
            console.log("Entering openForkCommit");
            label = openForkCommit(_rawParentShadowBlock, _keyShadowBlock, _relayer);
        }
        else{
            console.log("Entering submitNewCommit");
            label = submitNewCommit(_rawParentShadowBlock, _keyShadowBlock, _commitShadowBlock, _relayer);
        }
    }
    function storeGenesisCommit(
        bytes calldata _rawGenesis,
        bytes32 _keyGenesis,
        address _relayer,
        bytes32 _keyParentGenesis
        )internal returns (bool){
        CommitBlock storage cb = commitTree[_keyGenesis];
        cb.relayer = _relayer;
        emit OpenOldCommit(_keyGenesis, _keyParentGenesis, _relayer, true);
        return true;
    }

    //取得 parent key（从 _rawParent 解出）。
    //若已有同 parent 的 commit 存在则返回 Invalid_Honest（重复提交）。
    //调用 submitNewShadowBlock(_rawParent)（来自 SourceConsensusRules，负责链上校验、更新 shadow ledger）得到 label 与 keyGrandParent。
    function submitNewCommit(
        bytes calldata _rawParent,
        bytes32 _key,
        bytes32 _commit,
        address _relayer
        ) internal returns (RelayerLabel label){
        bytes32 keyParent = getKeyFromShadowBlock(_rawParent);
        CommitBlock storage cb = commitTree[_key];
        if (cb.commitFork[keyParent].commit != bytes32(0)){
            console.log("Duplicate commit for the same parent");
            label = RelayerLabel.Invalid_Honest;
            return label;             
        }
        bytes32 keyGrandParent;
        console.log("Submitting new shadow block with parent block key");
        (label, keyGrandParent) = submitNewShadowBlock(_rawParent);
        //若 label == Dishonest：认为 relayer 提交的数据错误，记录并返回（不保存质押）。
        if(label == RelayerLabel.Dishonest){
            console.log("Relayer submits wrong data");
            emit RecordRelayerContribution(_key, _relayer, ContributionLabel.Submit_Wrong_Data,getRequireStake());
            return label;
        }
        else if(label == RelayerLabel.Valid){
            console.log("Relayer submits valid data");
            //触发 UpdateShadowLedger 事件，处理 parent 对应的 prev_cb.commitFork[keyGrandParent]（即 parent 对其自己的 parent 的提交记录）：
            CommitBlock storage prev_cb = commitTree[keyParent];
            CommitMemory memory prev_cb_detail = prev_cb.commitFork[keyGrandParent];
            emit UpdateShadowLedger(keyParent, keyGrandParent, _rawParent);
            if(prev_cb_detail.commit != bytes32(0)){
                //若 prev_cb_detail 存在，则用 checkCommit 比对 prev 提交（commit == keccak(rawParent, prev_relayer)）：
                uint256 stake = uint256(prev_cb_detail.stake);
                if(checkCommit(_rawParent, prev_cb_detail.relayer, prev_cb_detail.commit)){
                    unlockStake(prev_cb_detail.relayer,stake);
                    emit RecordRelayerContribution(keyParent, prev_cb_detail.relayer, ContributionLabel.Commit_Opened_True,0);
                    prev_cb.relayer = prev_cb_detail.relayer;
                    
                    emit RecordRelayerContribution(keyParent, _relayer, ContributionLabel.Open_True_Commit,0);
                    
                    emit OpenOldCommit(keyParent,keyGrandParent,_relayer,true); 
                    delete prev_cb.commitFork[keyGrandParent];        
                }
                else{
                    punishLockedRelayer(prev_cb_detail.relayer,stake);        
                    emit RecordRelayerContribution(keyParent, prev_cb_detail.relayer, ContributionLabel.Commit_Opened_False,stake);
                    
                    emit RecordRelayerContribution(keyParent, _relayer, ContributionLabel.Open_False_Commit,stake);
                    prev_cb.relayer = _relayer;

                    emit OpenOldCommit(keyParent,keyGrandParent,_relayer,false);
                    delete prev_cb.commitFork[keyGrandParent];
                }
            }
        }
        //表示这次更新只是正常的但不是针对新 shadow（如 fork 情况），在特定条件下也可能触发 Dishonest 返回（见代码分支）。
        else if(label == RelayerLabel.Invalid_Honest){//Condition occurs if sourcechain generates a new fork, or the relayer is the first after setGenesis 
            if(cb.relayer != address(0)){
                label = RelayerLabel.Dishonest;
                return label;
            }
        }
        else{
            revert UnexpectedValue();
        }
        console.log("lock the stake required");
        lockStake(_relayer, getRequireStake());
        CommitMemory memory cm = CommitMemory({
            relayer: _relayer,
            commit: _commit,
            time: block.number,
            stake: uint96(getRequireStake())
        });
        console.log("Storing commit information in commit tree");
        cb.commitFork[keyParent] = cm; 
        emit SubmitNewCommit(_key, keyParent, _relayer, _commit);
        emit RecordRelayerContribution(_key, _relayer, ContributionLabel.Submit_New_Commit,0);

        label = RelayerLabel.Valid;
        return label;
    }
    function openForkCommit(//显式打开分叉的 commit
        bytes calldata _rawFork,
        bytes32 _keyFork,
        address _relayer
        ) internal returns (RelayerLabel label){
        if (_keyFork != getKeyFromShadowBlock(_rawFork)){
            emit RecordRelayerContribution(_keyFork, _relayer, ContributionLabel.Submit_Wrong_Data,getRequireStake());
            label = RelayerLabel.Dishonest;
            return label;
        }
        (RelayerLabel res,bytes32 keyParentFork) = submitNewShadowBlock(_rawFork);
        if(res == RelayerLabel.Dishonest){
            emit RecordRelayerContribution(_keyFork, _relayer, ContributionLabel.Submit_Wrong_Data,getRequireStake());
            label = RelayerLabel.Dishonest;
            return label;
        }
        else if(res == RelayerLabel.Invalid_Honest){
            label = RelayerLabel.Invalid_Honest;
            return label;
        }
        else if(res == RelayerLabel.Valid){
            emit UpdateShadowLedger(_keyFork, keyParentFork, _rawFork);
            if(!checkIfOldFork(_keyFork)){
                revert UnAllowedOperation();
            }
            CommitBlock storage fork_cb = commitTree[_keyFork];
            CommitMemory memory fork_cb_detail = fork_cb.commitFork[keyParentFork];
            if(fork_cb_detail.commit != bytes32(0)){
                uint256 stake = uint256(fork_cb_detail.stake);
                if(checkCommit(_rawFork, fork_cb_detail.relayer, fork_cb_detail.commit)){//commit relayer is honest
                    unlockStake(fork_cb_detail.relayer,stake);
                    emit RecordRelayerContribution(_keyFork, fork_cb_detail.relayer, ContributionLabel.Commit_Opened_True,0);
                    fork_cb.relayer = fork_cb_detail.relayer;

                    emit RecordRelayerContribution(_keyFork, _relayer, ContributionLabel.Open_Fork_True_Commit,0);
                    
                    emit OpenOldCommit(_keyFork,keyParentFork,_relayer,true);
                    delete fork_cb.commitFork[keyParentFork];
                }
                else{//commit relayer is dishonest
                    punishLockedRelayer(fork_cb_detail.relayer,stake);
                    emit RecordRelayerContribution(_keyFork, fork_cb_detail.relayer, ContributionLabel.Commit_Opened_False,stake);
                    
                    emit RecordRelayerContribution(_keyFork, _relayer, ContributionLabel.Open_Fork_False_Commit,stake);
                    fork_cb.relayer = _relayer;

                    emit OpenOldCommit(_keyFork,keyParentFork,_relayer,false);
                    delete fork_cb.commitFork[keyParentFork];
                }
            }
            else{
                revert UnexpectedValue();
            }
        }
        else {
            revert UnexpectedValue();
        }
        return label;
    }
    function openTimeOutCommit(
        bytes32 _keyParent,
        bytes32 _keyChild,
        address _challenger
        ) internal returns (RelayerLabel label){
        CommitBlock storage timeout_cb = commitTree[_keyChild];
        CommitMemory memory timeout_cb_detail = timeout_cb.commitFork[_keyParent];
        if(timeout_cb_detail.commit != bytes32(0)){
            if(block.number - timeout_cb_detail.time > MaxOpenCommitDelay){
                uint256 stake = uint256(timeout_cb_detail.stake);
                punishLockedRelayer(timeout_cb_detail.relayer,stake);
                emit RecordRelayerContribution(_keyChild, timeout_cb_detail.relayer, ContributionLabel.Commit_Time_Out,stake);
                
                emit RecordRelayerContribution(_keyChild, _challenger, ContributionLabel.Delete_Time_Out_Commit,stake);
                
                emit OpenOldCommit(_keyChild,_keyParent,_challenger,false);
                delete timeout_cb.commitFork[_keyParent];
                delete commitTree[_keyChild];
                return RelayerLabel.Valid;
            }
            else{
                return RelayerLabel.Dishonest;
            }
        }
        else {
            return RelayerLabel.Invalid_Honest;
        }
    }
    function checkCommit(bytes calldata _rawShadowBlock, address _relayer, bytes32 _commit) internal pure returns (bool){
        return (_commit == hashInCommit(_rawShadowBlock,_relayer));
    }
    function hashInCommit(bytes calldata _input1, address _input2) internal pure returns (bytes32){
        return keccak256(abi.encodePacked(_input1, _input2));
    }
    function getCommitState(bytes32 _keyNew, bytes32 _keyOld) public view returns (bytes32){
        return commitTree[_keyNew].commitFork[_keyOld].commit;
    }
    
}
