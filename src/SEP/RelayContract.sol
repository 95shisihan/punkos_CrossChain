// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import {SEP_OLC} from "./lib/LightClient.sol";
import {RelayContract as ARC} from "bridge-std/AbstractRelayContract.sol";

contract SEP_Relay is ARC, SEP_OLC{
}