# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (token/erc1155/interfaces/IERC1155.cairo)

%lang starknet

from starkware.cairo.common.uint256 import Uint256

@contract_interface
namespace IERC1155:
    func balanceOf(account : felt, tokenId : Uint256) -> (balance : Uint256):
    end

    func balanceOfBatch(account : felt, tokenIds_len : felt, tokenIds : Uint256*) -> (
            balances_len : felt, balances : Uint256*):
    end

    func setApprovalForAll(operator : felt, approved : felt):
    end

    func isApprovedForAll(account : felt, operator : felt) -> (isApproved : felt):
    end

    func safeTransferFrom(
            from_ : felt, to : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
            data : felt*):
    end

    func safeBatchTransferFrom(
            from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
            amounts : Uint256*, data_len : felt, data : felt*):
    end
end
