
const {ethers} = require("ethers");
const {Block} = require("bitcoinjs-lib");
//const provider = new ethers.JsonRpcProvider('http://localhost:8545');
const provider = new ethers.providers.JsonRpcProvider('http://123.157.213.102:39761');
//const provider = new ethers.JsonRpcProvider('http://192.168.101.33:8545');
async function listenMulti(){
  const blockNum = await provider.getBlockNumber()
  console.log(blockNum);
}


console.log("!!!")

listenMulti();
