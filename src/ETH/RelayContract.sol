// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {ETH_OLC} from "./lib/LightClient.sol";
import  {RelayContract as ARC} from "bridge-std/AbstractRelayContract.sol";

contract ETH_Relay is ARC,ETH_OLC{
}