# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (token/erc1155/interfaces/IERC1155_Receiver.cairo)

%lang starknet

from starkware.cairo.common.uint256 import Uint256

@contract_interface
namespace IERC1155_Receiver:
    func onERC1155Received(
            operator : felt, from_ : felt, tokenId : Uint256, value : Uint256, data_len : felt,
            data : felt*) -> (acceptMagic : felt):
    end

    func onERC1155BatchReceived(
            operator : felt, from_ : felt, tokenIds_len : felt, tokenIds : Uint256*,
            values_len : felt, values : Uint256*, data_len : felt, data : felt*) -> (
            acceptMagic : felt):
    end
end
