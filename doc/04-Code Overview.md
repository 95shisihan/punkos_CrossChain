# 跨链区开发说明文档

## 概述
跨链区基于foundry框架对所设计协议进行开发，使用地语言主要是solidity、python。

## 项目结构
跨链区代码地一级目录如下：
```tree 
CrosschainZone/  
├── src/                                            # 智能合约组件  
├── script/                                         # 合约部署和启动脚本
├── client/                                         # 与合约交互地链下客户端 
├── vue/                                            # 前端组件
├── database/                                       # 数据库组件
├── docs/                                           # 文档目录
├── .env                                            # 环境变量配置文件
├── foundry.toml                                    # foundry配置文件
└── readme.md                                       # 跨链区简介
```

## 智能合约组件
```tree
CrosschainZone/src/                                 # 智能合约目录  
├── Hub/                                        # 跨链区核心合约目录 
│   ├── abstracts/                              # 抽象合约目录
│   │   ├── AbstractSystemContract.sol          # 系统合约规则
│   │   ├── AbstractStakeManagement.sol         # 质押管理规则
│   │   ├── AbstractSourceRules.sol             # 源链原生规则
│   │   ├── AbstractRelayContract.sol           # 中继合约规则
│   │   └── AbstractTransportContract.sol       # 传输合约规则
│   └── MultiChainManager.sol                   # 多链管理合约  
├── BTC/                                        # 比特币跨链桥目录
│   ├── lib/                                    # 比特币跨链合约的库
│   ├── LigthClient.sol                         # 测试用的比特币影子客户端合约
│   ├── RelayContract.sol                       # 最后部署的中继合约
│   ├── TxRule.sol                              # 最后部署的交易规则合约
│   └── TransportContract.sol                   # 最后部署的传输合约
└── ETH/                                        # 以太坊跨链桥目录
    ├── lib/                                    # 以太坊跨链合约的库
    ├── LigthClient.sol                         # 测试用的以太坊影子客户端合约
    ├── RelayContract.sol                       # 最后部署的中继合约
    ├── TxRule.sol                              # 最后部署的交易规则合约
    └── TransportContract.sol                   # 最后部署的传输合约  
```
### 通用跨链合约组件
通用跨链组件位于`src/HUB`目录下,包含接口合约(`/abstracts/`)和多链管理合约(`/MultiChainManager.sol`)，各合约分别实现如下功能：
- 接口合约
  - 系统合约接口(`AbstractSystemContract.sol`):规定系统合约需要记录所属链的相关信息，以及相关的权限控制操作
  - 质押接口(`AbstractStakeManagement.sol`):规定质押所需的相关信息及操作
  - 源链规则接口(`AbstractSourceRules.sol`):统一源链数据验证过程的输入参数、输出参数、和必要的中间过程
  - 通用信任中继协议(`AbstractRelayContract.sol`):基于抽象源链规则，实现无需信任的跨链信任中继协议及其激励机制
  - 通用消息传输协议(`AbstractTransportContract.sol`): 基于抽象源链规则和单向跨链信任，实现安全的双向跨链消息传输协议
- 多链管理合约：跨链区的0号系统合约，负责登记所有源链及系统合约信息，掌管所有跨链合约的控制权。自身的控制权归于治理区。

### 比特币跨链合约组件

- 库合约(`BTC/lib/`)：实现比特币验证规则所需的库
- 链上轻节点合约(`BTC/LigthClient.sol`):基于源链规则接口和比特币库合约实现的比特币链上轻节点，仅实现相关数据验证，不包含激励设计。能够在测试过程部署运行，但最终并不部署该合约
- 中继合约(`BTC/RelayContract.sol`)：比特币链上轻节点合约和通用信任中继协议的公共子合约，最终部署上链

## 合约组件
