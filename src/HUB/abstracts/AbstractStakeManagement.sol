// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {SystemContract} from "./AbstractSystemContract.sol"; 
abstract contract StakeManagement is SystemContract{
    uint256 private requireStake;
    uint256 private totalPenalty;
    mapping (address => uint256) private stakeOf; 
    enum StakeLabel{
        Default,
        Add_Unlocked_Stake,
        Withdraw_Unlocked_Stake,
        Lose_Unlocked_Stake,
        Lose_Locked_Stake,
        Lock_Stake,
        Unlock_Stake,
        Receive_Reward,
        Withdraw_Penalty,
        Modify_Setting
    }
    event UpdateStake(address indexed relayer, StakeLabel indexed label, uint256 value); 
    error NonEnoughStake();
    modifier onlyRelayer{
        if (stakeOf[msg.sender] < requireStake){
            revert NonEnoughStake();
        }
        _;
    }
    constructor(){
        totalPenalty = 0;
        requireStake = 1 ether;
    }

    function withdrawPenalty(address _address) external onlyManager{
        payable(_address).transfer(totalPenalty);
        emit UpdateStake(msg.sender, StakeLabel.Withdraw_Penalty, totalPenalty); 
        totalPenalty = 0;
    }
    function getPenalty() external view returns (uint256){
        return totalPenalty;
    }

    function setRequireStake(uint256 _newStake) external onlyWorking{
        requireStake = _newStake;
        emit UpdateStake(msg.sender, StakeLabel.Modify_Setting, _newStake);
    }
    function getRequireStake() public view returns (uint256){
        return requireStake;
    }
    function getMyStake() external view returns (uint256 stake){
        return stakeOf[msg.sender];
    }
    function becomeRelayer() external payable onlyWorking{
        if (stakeOf[msg.sender] + msg.value < requireStake){
            revert NonEnoughStake();
        }
        stakeOf[msg.sender] += msg.value;
        emit UpdateStake(msg.sender, StakeLabel.Add_Unlocked_Stake, msg.value); 
    }

    function withdrawStake(uint256 _amount) external onlyWorking{
        if (stakeOf[msg.sender] < _amount){
            revert NonEnoughStake();
        }
        stakeOf[msg.sender] -= _amount;
        payable(msg.sender).transfer(_amount);
        emit UpdateStake(msg.sender, StakeLabel.Withdraw_Unlocked_Stake, _amount); 
    }
    function unlockStake(address relayer, uint256 value) internal {
        stakeOf[relayer] += value;
        emit UpdateStake(relayer, StakeLabel.Unlock_Stake, value);
    }
    function lockStake(address relayer, uint256 value) internal {
        stakeOf[relayer] -= value;
        emit UpdateStake(relayer, StakeLabel.Lock_Stake, value);
    }
    function punishUnlockedRelayer(address relayer, uint256 value) internal {
        stakeOf[relayer] -= value;
        emit UpdateStake(relayer, StakeLabel.Lose_Unlocked_Stake, value); 
        totalPenalty += value; 
    }
    function punishLockedRelayer(address relayer, uint256 value) internal{
        emit UpdateStake(relayer, StakeLabel.Lose_Locked_Stake, value); 
        totalPenalty += value; 
    }
}
