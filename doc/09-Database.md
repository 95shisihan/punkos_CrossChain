|编号|题目|阶段|类别|作者|创建|修改|
|---|---|---|---|---|---|---|
|4|跨链区数据库设计|草稿|机制设计|耿一夫|2024-12|2024-12|

## 目录
- [目录](#目录)
- [表结构概览](#表结构概览)
- [详细表结构](#详细表结构)
  - [跨链区信息表](#跨链区信息表)
  - [中继链信息表](#中继链信息表)
  - [源链信息表](#源链信息表)
  - [系统合约信息表](#系统合约信息表)
  - [中继链区块信息表](#中继链区块信息表)
  - [中继链交易信息表](#中继链交易信息表)
  - [中继链事件类型表](#中继链事件类型表)
  - [中继链事件信息表](#中继链事件信息表)
  - [中继合约基础信息表](#中继合约基础信息表)
  - [影子区块信息表](#影子区块信息表)
  - [传输任务信息表](#传输任务信息表)
- [硬编码的表数据](#硬编码的表数据)
  - [跨链区信息表`crosschainzone_info`](#跨链区信息表crosschainzone_info)
  - [中继链事件类型表 `event_type`](#中继链事件类型表-event_type)
- [数据库维护流程](#数据库维护流程)
  - [初始化](#初始化)
  - [日常维护](#日常维护)
  - [进一步解析](#进一步解析)

## 表结构概览

数据库中有两类核心表：
- 第一类表：数据库中只会存在一个表：
  - crosschainzone_info：跨链区信息表
  - hub_chain_info：中继链信息表
  - source_chain_info: 源链信息表
  - system_contract_info：源链信息表
  - hub_block_info: 中继链区块信息表
  - hub_tx_info: 中继链交易信息表
  - event_type: 中继链事件类型表
  - event_info: 中继链事件信息表
- 第二类表：数据库中动态维护若干个表：
  - source_shadow_info_{chain_id}: 影子区块信息表
  - transport_task_info_{chain_id}: 传输任务信息表

## 详细表结构

### 跨链区信息表

`crosschainzone_info`记录跨链区的硬编码信息
| 字段名 | 类型 | 说明 |
|--------|------|------|
| no | int | 0 |
| zone_type | int | 本地测试链为0; 远程测试链为1 |
| rpc | text | 链rpc地址和端口 |
| multi_addr | varchar(42)| 管理合约地址 |
| visit_block_height | bigint | 监听器标识 |

索引：
- PRIMARY KEY `no`

备注：
- 只有一条记录, `no = 0`

### 中继链信息表

`hub_chain_info`记录跨链区中继链的信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| chain_id | uint256 | int | 链ID |
| symbol | string | text | 链符号 |
| name | string | text | 链名称 |
| source_chain_num | uint256 | bigint | 注册源链数量 |
| system_contract_num | uint256 | bigint | 注册系统合约数量 |
| visit_block_height | uint256 | bigint | 获取全局状态的区块高度 |

索引：
- PRIMARY KEY `chain_id`

备注：
- 只有一条记录 `chain_id = 0`

### 源链信息表 

`source_chain_info`记录在跨链区注册的源链信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| chain_id | uint256 | int | 链ID |
| symbol | string | text | 链符号 |
| name | string | text | 链名称 |
| state | uint256 | int | 链状态 |
| visit_block_height | uint256 | bigint | 获取全局状态的区块高度 |
| register_tx_hash | bytes32 | varchar(66) | 源链的注册交易哈希 |


索引：
- PRIMARY KEY `chain_id`

### 系统合约信息表 

`system_contract_info`记录系统合约的基础信息。


| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| contract_id | uint256 | int | 合约ID |
| contract_addr | address | varchar(42) | 合约地址 |
| manager_addr |  address | varchar(42) | 合约管理员地址 |
| contract_state | uint256 | int |  合约状态 |
| chain_id | uint256 | int | 对应链ID |
| level_id | uint256 | int | 链内编号 |
| visit_block_height | uint256 | bigint | 获取全局状态的区块高度 |
| deploy_tx_hash | bytes32 | varchar(66) | 合约的部署交易哈希 |

索引：
- PRIMARY KEY `contract_id`
- UNIQUE KEY `contract_addr`

### 中继链区块信息表 
`hub_block_info`记录系统合约的基础信息。


| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| no | uint256 | bigint | 自动分配的编号 |
| block_hash | bytes32 | varchar(66) | 区块哈希 |
| prev_hash | bytes32 | varchar(66) | 父区块哈希 |
| block_height | uint256 | bigint |  区块高度 |
| if_matter | bool | TINYINT(1) | 是否包含重要交易 |

索引：
- PRIMARY KEY `no` (`AUTO_INCREMENT=1`)
- UNIQUE KEY `block_hash`

### 中继链交易信息表 
`hub_tx_info`记录系统合约的基础信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| no | uint256 | bigint | 自动分配的编号 |
| tx_hash | bytes32 | varchar(66) | 交易哈希 |
| block_hash | bytes32 | varchar(66) | 交易所在区块的哈希 |
| tx_index | uint256 | bigint | 交易在区块中的索引 |

索引：
- PRIMARY KEY `no` (`AUTO_INCREMENT=1`)
- UNIQUE KEY `tx_hash`
- UNIQUE KEY `(block_hash,tx_index)`

### 中继链事件类型表 
`event_type`记录系统合约关键事件的类型信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| no | uint256 | bigint | 自动分配的编号 |
| event_sig | bytes32 | varchar(66) | 事件签名 |
| description |  | text | 事件文本 |
| event_param |  | json | 参数含义及数据类型 |

索引：
- PRIMARY KEY `no` (`AUTO_INCREMENT=1`)
- UNIQUE KEY `event_sig`

### 中继链事件信息表 
`event_info`记录系统合约关键事件的数据信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| no | uint256 | bigint | 自动分配的编号 |
| contract_addr | address | varchar(42) | 触发事件的合约地址 |
| event_sig | bytes32 | varchar(66) | 事件签名 |
| event_topic |  | text | 索引参数 |
| event_data |  | text | 普通参数 |
| tx_hash | bytes32 | varchar(66) | 事件所在交易的哈希 |
| event_index | uint256 | bigint | 事件在交易中的索引 |
| if_process | bool | TINYINT(1) | 是否对事件做进一步解析 |

索引：
- PRIMARY KEY `no` (`AUTO_INCREMENT=1`)
- UNIQUE KEY (`tx_hash,event_index`)
  
### 中继合约基础信息表 

`relay_basic_info`记录源链中继合约的基础信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| chain_id | int |  | 链ID |
| genesis_key | varchar | 66 | 创世影子区块KEY |
| gas_bound | varchar | 66 | 搬运工gas下界 |
| commit_time_out | varchar | 66 | 承诺有效上界 |
| require_stake | varchar | 66 | 搬运工质押下界 |
| processed_penalty | varchar | 66 | 已处理的罚金 |
| un_processed_penalty | varchar | 66 | 待处理的罚金 |

索引：
- PRIMARY KEY (`chain_id`)

### 影子区块信息表 

`source_shadow_info_{chain_id}`记录中继合约中的影子区块信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|--------|------|------|------|
| no | uint256 | bigint | 自动分配的编号 |
| shadow_key | bytes32 | varchar(66) | 影子区块KEY |
| prev_key | bytes32 | varchar(66) | 影子父区块KEY |
| offset_height | uint256 | bigint | 与创世影子区块的相对高度 |
| commit_event_no | uint256 | bigint | 提交承诺的事件no |
| commit_relayer_addr | address | varchar(42) | 承诺的搬运工地址 |
| commit_value | bytes32 | varchar(66) | 承诺值 |
| open_event_no | uint256 | bigint | 打开承诺的事件no |
| open_event_type | uint256 | bigint | 打开承诺的事件类型 |
| open_relayer_addr | address | varchar(42) | 打开承诺的搬运工 |
| open_result | bool | TINYINT(1) | 承诺的验证结果 |
| raw_data | text |  | 影子区块源数据 |

索引：
- PRIMARY KEY `no` (`AUTO_INCREMENT=1`)


### 传输任务信息表 

`transport_task_info_{chain_id}`记录传输任务信息。

| 字段名 | solidity类型 | mysql类型 | 说明 |
|-------|------|------|------|
| id | uint256 | bigint | 传输任务编号 |
| task_hash | bytes32 | varchar(66) | 传输任务哈希 |
| task_state | uint256 | bigint | 传输任务的当前状态 |
| user_addr | address | varchar(42) | 创建任务的用户地址 |
| create_event_no | uint256 | bigint | 创建任务的事件编号 |
| task_type_1 | uint256 | bigint | 一级传输任务类型 |
| payload | bytes | text | 待传输数据 |
| task_type_2 | uint256 | bigint | 二级传输任务类型 |
| accept_event_no | uint256 | bigint | 接受任务的事件编号 |
| accept_event_type | uint256 | bigint | 接受任务的事件类型 |
| accept_relayer_addr | address | varchar(42) | 接受任务的搬运工地址 |
| finish_event_no | uint256 | bigint | 结束任务的事件编号 |
| finish_event_type | uint256 | bigint | 结束任务的事件类型 |
| finish_role_addr | address | varchar(42) | 结束任务的角色地址 |
| source_tx_key | bytes32 | varchar(66) | 关联源链交易的key |
| source_tx_raw | bytes | text | 关联源链交易的源数据 |
| source_shadow_key | bytes32 | varchar(66) | 关联源链交易的key |

索引：
- PRIMARY KEY `id`
- UNIQUE KEY `task_hash`


## 硬编码的表数据

### 跨链区信息表`crosschainzone_info`

| zone_type | rpc | multi_addr |
|--------|------|------|
| 0 | http://127.0.0.1:8545 | 0x5FbDB2315678afecb367f032d93F642f64180aa3 |

### 中继链事件类型表 `event_type`

| no | event_sig | description | event_param |
|--------|------|------|------|
| 0 | 0x9dad43a7b4a76afed98c6a24f82688b4418e8fc9c31f37fc877d77f73477f8c9 | UpdateChainInfo(uint256 indexed) | `{"index":(_chainID),"data":()}` |
| 1 | 0x4d0b8309615448c317b4a179cde98e9a0c5d77e4637f3be004f7c3c14d19fb4a | UpdateContractInfo(address indexed) | `{"index":(_contractAddress),"data":()}` |
| 2 | 0x00f76ab116a28b0fe312c7ff8d51d85886dc7a2a4e739f6911db90a4da110c7c | UpdateShadowLedger(bytes32 indexed ,bytes32 ,bytes) | `{"index":(keyShadowBlock),"data":(keyParentShadowBlock,rawShadowBlock)}` |
| 3 | 0x3d6a8e5ef4d505e0b03ec65b743caffc5a90079d0a6851c06646d0878cfa89e3 | OpenOldCommit(bytes32 indexed,bytes32,address indexed,bool) | `{"index":(keyShadowBlock,relayer),"data":(keyParentShadowBlock,result})` |
| 4 | 0xecb32623cdb13b96fe5fe2ba21058d1fd83ed4a7ae572310702d3e2cf9fdca2c | SubmitNewCommit(bytes32 indexed,bytes32,address indexed,bytes32)  | `{"index":(keyShadowBlock,relayer),"data":(keyParentShadowBlock,commit)}` |

## 数据库维护流程

### 初始化
- 第一次启动数据库，创建所有空白的一类表，并导入硬编码的数据
- 每次重置数据库，删除数据库中的所有表，然后执行上述操作

### 日常维护
- 每次启动程序，先检验数据库是否经过初始化
- 通过初始化验证后，从数据库中的硬编码数据和其它历史数据，生成待监听的特定合约中的特定事件，维护中继链的区块、交易、事件信息表，并标记扫描过的最新区块索引
  - 若发现新的源链或合约，动态创建对应的二类表
  - 扫描新注册的所有历史事件和部署交易单
  - 更新监听合约列表
  
### 进一步解析
- 每次启动程序，先检验数据库是否经过初始化
- 通过初始化验证后，监听中继链事件信息表
- 每当检测到新的事件，基于其事件类型和参数更新数据库，并在更新成功后标记该事件
  - 记录历史数据的事件，在表中插入或更新数据
  - 标记全局变量更新的事件，先判断是否需要更新数据。若需要，则从合约读取其最新状态，然后更新数据并标记最新区块索引
