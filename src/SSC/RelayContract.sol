// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {SimpleChainLightClient as SSC_OLC} from "./lib/LightClient.sol";
import {RelayContract as ARC} from "bridge-std/AbstractRelayContract.sol";

contract SSC_Relay is ARC, SSC_OLC{
}