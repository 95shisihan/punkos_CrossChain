// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
//Note: 跨链桥开发者基于此文件中接口开发的合约，不能使用require/revert之类的函数。若使用，默认无法通过跨链区和治理区的联合审计
//Note: 我们假设在跨链区的中继链上运行源链的Shadow Client。Shadow Client是在基于安全性和性能权衡后，从源链客户端、轻客户端、超轻客户端杂糅而来的
//Note: Shadow Ledger refers to the data stored in the Shadow Client
//Note: Shadow Block
import {SystemContract} from "./AbstractSystemContract.sol";
abstract contract SourceConsensusRules{
    
    enum RelayerLabel{
        Default,
        Valid,
        Invalid_Honest,
        Dishonest
    }
    /// @notice 设置初始区块头以及初始高度
    /// @param rawGenesisShadowBlock 设置的第一个区块头，不必须是源链的创世区块头
    /// @param params 区块头之外的初始参数
    /// @return success 函数的执行结果：0表示执行失败（可能原因：没有权限、初始区块头已设置、区块头非法）；1表示执行成功，搬运工可开始后续搬运
    function setGenesisShadowBlock (bytes calldata rawGenesisShadowBlock, bytes calldata params) virtual internal returns(bool success);

    /// @notice 中继新区块头
    /// @param rawNewShadowBlock 搬运工提交的新区块头（这里的区块头与源链的共识有关，是一个逻辑概念）
    /// @return relayerLabel return Valid/1 if relayer is valid; Invalid_Honest/2 if relayer is honest but does not update ledger;
    /// @return keyPrevShadowBlock 父区块哈希(仅当result=1时，需要调用该字段)
    function submitNewShadowBlock(bytes calldata rawNewShadowBlock) virtual internal returns(RelayerLabel relayerLabel, bytes32 keyPrevShadowBlock);
    
    /// @notice 验证是否存在目标交易
    /// @notice 验证过程与源链的记账方式有关，核心是验证默克尔证明以及验证交易根是否被确认
    /// @param leafNode 叶子节点
    /// @param proof 叶子的默克尔证明
    /// @param rootKey 查询根节点的key，通常是交易所在的区块哈希 
    /// @return success 函数的执行结果：false表示交易无效；true表示交易有效
    function verifyTxByShadowLedger (bytes calldata leafNode, bytes calldata proof, bytes32 rootKey, uint delay) virtual public view returns (bool success);
    
    /// @notice 计算区块头哈希
    /// @param rawShadowBlock 区块头源数据 
    /// @return keyShadowBlock 区块头哈希
    function getKeyFromShadowBlock(bytes calldata rawShadowBlock) virtual public pure returns(bytes32 keyShadowBlock);

    /// @notice 查询目标区块头是否被确认为叔块，后续可能会触发剪枝操作
    /// @param keyShadowBlock 区块头哈希 
    /// @return res 函数的执行结果：false表示不确定为叔块（区块头不存在、区块被主链确认、新区块待确认）；true表示确认为叔块（区块未确认且与主链高度差超过阈值）
    function checkIfOldFork(bytes32 keyShadowBlock) virtual public view returns(bool res);

    /// @notice 查询待中继的区块头高度
    /// @return key 影子链当前高度
    function getTopKeyFromShadowLedger() virtual external view returns(bytes32 key);
    
    
}
abstract contract SourceTransactionRules is SystemContract{
    function checkIfPayloadMatchTx(bytes memory _payload, bytes memory _rawTx, uint256 _matchType) virtual external pure returns (bool res);
    function checkIfLeafNodeMatchTx(bytes memory _leafNode, bytes memory _rawTx) virtual external pure returns (bool res);
    function getKeyFromRawTx(bytes memory _rawTx) virtual external pure returns (bytes32 keyTx);
}

