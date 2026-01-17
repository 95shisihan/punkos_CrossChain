DEPLOY_ENV=dev forge script script/Manager.d.sol --broadcast --legacy
DEPLOY_ENV=dev forge script script/ManagerAddSource.s.sol --broadcast --legacy 
DEPLOY_ENV=dev forge script script/SSC_Relay.d.sol --broadcast --legacy
DEPLOY_ENV=dev forge script script/BTC_Relay.d.sol --broadcast --legacy
DEPLOY_ENV=dev forge script script/ETH_Relay.d.sol --broadcast --legacy 
DEPLOY_ENV=dev forge script script/ManagerSetGenesis.s.sol --broadcast --legacy