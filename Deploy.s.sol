// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Script.sol";
import "./Simple721.sol";

contract DeployScript is Script {
    function run() public {
        vm.startBroadcast();
        
        Simple721 nft = new Simple721("PipelineDemo", "PDEMO");
        
        console.log("Contract deployed at:", address(nft));
        console.log("Contract name:", nft.name());
        console.log("Contract symbol:", nft.symbol());
        
        vm.stopBroadcast();
    }
}
