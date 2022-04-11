# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (token/erc1155/utils/ERC1155_Holder.cairo)

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.uint256 import Uint256

from openzeppelin.utils.constants import (
    IERC1155_ERC165_TOKENRECEIVER, IERC1155_ACCEPTED, IERC1155_BATCH_ACCEPTED)

from openzeppelin.introspection.ERC165 import ERC165_supports_interface, ERC165_register_interface

@view
func onERC1155Received(
        operator : felt, from_ : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
        data : felt*) -> (acceptMagic : felt):
    return (IERC1155_ACCEPTED)
end

@view
func onERC1155BatchReceived(
        operator : felt, from_ : felt, tokenIds_len : felt, tokenIds : Uint256*, values_len : felt,
        values : Uint256*, data_len : felt, data : felt*) -> (acceptMagic : felt):
    return (IERC1155_BATCH_ACCEPTED)
end

@view
func supportsInterface{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        interfaceId : felt) -> (success : felt):
    let (success) = ERC165_supports_interface(interfaceId)
    return (success)
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    ERC165_register_interface(IERC1155_ERC165_TOKENRECEIVER)
    return ()
end
