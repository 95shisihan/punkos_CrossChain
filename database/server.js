
const express = require('express')
const mysql = require('mysql2')
const cors = require('cors')

const app = express()
app.use(cors()) // 解决跨域问题

// 数据库连接配置
const connection = mysql.createConnection({
    host: '111.119.239.159',  
    port: 36036,  
    user: 'root',  
    password: 'szl@buaa#1234', 
    database: 'CrossZone'
})

connection.connect((err) => {
  if (err) {
    console.error('数据库连接失败:', err)
    return
  }
  console.log('数据库连接成功')
})

app.get('/api/crosschainzone', (req, res) => {
  const query = 'SELECT rpc, multi_addr FROM crosschainzone_info WHERE no = 0'
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/sourceChains', (req, res) => {
  const query = 'SELECT * FROM source_chain_info'
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/shadowBlocks/:chain_id', (req, res) => {
  const chain_id = req.params.chain_id
  const query = 'SELECT * FROM source_shadow_info_' + chain_id
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/hubChain', (req, res) => {
  const query = 'SELECT * FROM HubInfo'
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/systemContracts', (req, res) => {
  const query = 'SELECT * FROM system_contract_info'
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/bridgeTxs', (req, res) => {
  const query = 'SELECT no, tx_hash, block_hash, tx_index FROM hub_tx_info'
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})
app.get('/api/bridgeTxsInBlock/:block_hash', (req, res) => {
  const block_hash = req.params.block_hash
  const query = 'SELECT no, tx_hash, block_hash, tx_index FROM hub_tx_info WHERE block_hash = ?'
  connection.query(query, [block_hash], (error, results) => {
    if (error) {
      res.status(500).json({ error: '查询失败' })
      return
    }
    res.json(results)
  })
})

const port = 3020 
app.listen(port, '0.0.0.0', () => {  
  console.log(`服务器运行在 http://localhost:${port}`)  
  })  

