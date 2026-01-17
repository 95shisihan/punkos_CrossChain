
const {ethers} = require("ethers");
const provider = new ethers.providers.JsonRpcProvider('http://localhost:8545');
//const provider = new ethers.JsonRpcProvider('http://123.189.165.13:8545');
//const provider = new ethers.JsonRpcProvider('http://192.168.101.33:8545');
console.log("!!!")
class ChainOverview{
  constructor(chainID,name,symbol,registerTime,relayAddress,transportAddress){
    this.chainID = chainID;
    this.name = name;
    this.symbol = symbol;
    this.registerTime = registerTime;
    this.relayAddress = relayAddress;
    this.transportAddress = transportAddress;
  }
}
class ChainDetail{
  constructor(genesisHash,heaviestHash){
    this.genesisHash = genesisHash;
    this.heaviestHash = heaviestHash;
  }
  addShadow(header){
    this.shadows.push(header);
  }
}
class ShadowBlock{
  constructor(hashHeader,bytesHeader,heightHeader,relayer,hubBlockHash,hubTxHash){
    this.hashHeader = hashHeader;
    this.bytesHeader = bytesHeader;
    this.heightHeader = heightHeader;
    this.relayer = relayer;
    this.hubBlockHash = hubBlockHash;
    this.hubTxHash = hubTxHash;
  }
}
let hubchainInfo = {
  "multiAddress":'0x5FbDB2315678afecb367f032d93F642f64180aa3',
  "manager":'0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
  "chainNum":1,
  "chains":[],
};
async function listenMulti(){
    const multiAddress = '0x5FbDB2315678afecb367f032d93F642f64180aa3';
    let multiABI =[
      "function getChainNum() view returns (uint256)",
      "function getOwner() view returns (address)",
      "event SourceChainAdded(uint indexed id, address chainAddress, string name, string symbol)",
      "function getChainInfo(uint chainID) view returns (string memory,string memory,uint256,address,address)",
    ];
    let relayABI =[
      "function getTopHeight() view returns(uint)",
      "event ShadowLedgerUpdate(bytes32 indexed hashHeader, bytes bytesHeader, address relayer)",
      "function getHeaderHeight(bytes32 hashHeader) view returns(uint)",
    ];
    const multiContract = new ethers.Contract(multiAddress, multiABI, provider);
    const owner = await multiContract.getOwner();
    const chainNum = Number(await multiContract.getChainNum());
    console.log("Number of Chains:%d",chainNum+1);
    hubchainInfo['multiAddress'] = multiAddress;
    hubchainInfo['manager'] = owner;
    hubchainInfo['chainNum'] = chainNum;
    for(let i = 0; i <= chainNum; i ++){
      const chainInfo = await multiContract.getChainInfo(i);
      let newSource = new ChainOverview(i,chainInfo[0],chainInfo[1],Number(chainInfo[2]),chainInfo[3],chainInfo[4]);
      hubchainInfo['chains'].push(newSource);
    }
    console.log(hubchainInfo['chains']);
    for (let i = 1; i <= chainNum; i ++){
      const chainInfo = await multiContract.getChainInfo(i);
      const relayAddress = chainInfo[3];
      console.log("ChainID:%d",i);
      const relayContract = new ethers.Contract(relayAddress, relayABI, provider);
      relayHeight = await relayContract.getTopHeight();
      //console.log(Number(relayHeight));
      let eventFilter = await relayContract.filters.ShadowLedgerUpdate();
      let contractEvents = await relayContract.queryFilter(eventFilter);
      console.log("Number of Shadow Blocks:%d",contractEvents.length);
      for (let j = 0; j < contractEvents.length; j ++){
        //console.log(contractEvents[j]);
        let hashHeader = contractEvents[j].args['hashHeader'];
        let bytesHeader = contractEvents[j].args['bytesHeader'];
        let relayer = contractEvents[j].args['relayer'];
        let heightHeader = await relayContract.getHeaderHeight(hashHeader);
        let hubBlockHash = contractEvents[j].blockHash;
        let hubTxHash = contractEvents[j].transactionHash;
        let newShadow = new ShadowBlock(hashHeader,bytesHeader,heightHeader,relayer,hubBlockHash,hubTxHash);
        console.log(newShadow);
      }
    }
    console.log("Over!!!")
    return;
  } 

listenMulti();
