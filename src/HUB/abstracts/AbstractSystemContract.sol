// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
abstract contract SystemContract {
    address private manager;
    uint256 private state_contract;//0-default;1-init;2-work;3-pause;4-stop
    uint256 private ID_chain;//0-default;1-relay_chain;>=2-source_chain
    uint256 private ID_level;
    error NoManagerAuthority(address _address);
    error NoWorkingState(uint256 _state);
    constructor() {
        manager = msg.sender;
        state_contract = 1;
    }
    modifier onlyManager{
        if (msg.sender != manager){
            revert NoManagerAuthority(msg.sender);
        }
        _;
    }
    modifier onlyWorking{
        if(state_contract != 2){
            revert NoWorkingState(state_contract);
        }
        _;
    }
    function updateContractManager(address newManager) external onlyManager returns (bool res){
        if(newManager != manager){
            manager = newManager;
        }
        res = true;
    }
    function updateContractState(uint newState) external onlyManager {
        if(newState != state_contract){
            state_contract = newState;
        }
    }
    function updateChainID(uint newID) external onlyManager{
        if(newID != ID_chain){
            ID_chain = newID;
        }
    }
    function updateLevelID(uint newID) external onlyManager{
        if(newID != ID_level){
            ID_level = newID;
        }
    }
    function getContractManager() external view returns (address currentManager){
        return manager;
    }
    function getContractState() external view returns (uint currentState){
        return state_contract;
    }
    function getChainID() external view returns (uint currentID){
        return ID_chain;
    }
    function getLevelID() external view returns (uint currentID){
        return ID_level;
    }
}