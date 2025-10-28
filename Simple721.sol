// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;


contract Simple721 {
    string public name;
    string public symbol;
    uint256 private _tokenIdCounter;
    
    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Minted(address indexed to, uint256 indexed tokenId, string tokenURI);
    
    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
    }
    
    function mintWithTokenURI(address to, string memory tokenURI) public returns (uint256) {
        uint256 tokenId = _tokenIdCounter;
        _tokenIdCounter++;
        
        _owners[tokenId] = to;
        _tokenURIs[tokenId] = tokenURI;
        _balances[to]++;
        
        emit Transfer(address(0), to, tokenId);
        emit Minted(to, tokenId, tokenURI);
        
        return tokenId;
    }
    
    function tokenURI(uint256 tokenId) public view returns (string memory) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return _tokenURIs[tokenId];
    }
    
    function ownerOf(uint256 tokenId) public view returns (address) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return _owners[tokenId];
    }
    
    function balanceOf(address owner) public view returns (uint256) {
        require(owner != address(0), "Address zero is not a valid owner");
        return _balances[owner];
    }
    
    function totalSupply() public view returns (uint256) {
        return _tokenIdCounter;
    }
}
