// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {BTC_OLC} from "./lib/LightClient.sol";
import {RelayContract as ARC} from "bridge-std/AbstractRelayContract.sol";
//import {RelayContract as ARC} from "src/HUB/abstracts/AbstractRelayContract.sol";
contract BTC_Relay is BTC_OLC, ARC{
    constructor(uint _mainnet) BTC_OLC(_mainnet){
    }
}