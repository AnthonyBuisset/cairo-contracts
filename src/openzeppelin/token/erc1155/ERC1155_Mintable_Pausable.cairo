# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (token/erc1155/ERC1155_Mintable_Pausable.cairo)

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.uint256 import Uint256

from openzeppelin.token.erc1155.library import (
    ERC1155_uri, ERC1155_balanceOf, ERC1155_balanceOfBatch, ERC1155_isApprovedForAll,
    ERC1155_initializer, ERC1155_setApprovalForAll, ERC1155_safeTransferFrom,
    ERC1155_safeBatchTransferFrom, ERC1155_mint)

from openzeppelin.introspection.ERC165 import ERC165_supports_interface

from openzeppelin.security.pausable import (
    Pausable_paused, Pausable_pause, Pausable_unpause, Pausable_when_not_paused)

from openzeppelin.access.ownable import Ownable_initializer, Ownable_only_owner

#
# Constructor
#

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt, uri : felt):
    ERC1155_initializer(uri)
    Ownable_initializer(owner)
    return ()
end

#
# Getters
#

@view
func supportsInterface{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        interfaceId : felt) -> (success : felt):
    let (success) = ERC165_supports_interface(interfaceId)
    return (success)
end

@view
func uri{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(tokenId : Uint256) -> (
        uri : felt):
    let (uri) = ERC1155_uri(tokenId)
    return (uri=uri)
end

@view
func balanceOf{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        account : felt, tokenId : Uint256) -> (balance : Uint256):
    let (balance : Uint256) = ERC1155_balanceOf(account, tokenId)
    return (balance)
end

@view
func balanceOfBatch{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        account : felt, tokenIds_len : felt, tokenIds : Uint256*) -> (
        balances_len : felt, balances : Uint256*):
    let (balances_len : felt, balances : Uint256*) = ERC1155_balanceOfBatch(
        account, tokenIds_len, tokenIds)
    return (balances_len, balances)
end

@view
func isApprovedForAll{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt, operator : felt) -> (isApproved : felt):
    let (isApproved : felt) = ERC1155_isApprovedForAll(owner, operator)
    return (isApproved)
end

@view
func paused{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (paused : felt):
    let (paused) = Pausable_paused.read()
    return (paused)
end

#
# Externals
#

@external
func mint{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        to : felt, tokenId : Uint256, amount : Uint256):
    Pausable_when_not_paused()
    Ownable_only_owner()
    ERC1155_mint(to, tokenId, amount)
    return ()
end

@external
func setApprovalForAll{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        operator : felt, approved : felt):
    Pausable_when_not_paused()
    ERC1155_setApprovalForAll(operator, approved)
    return ()
end

@external
func safeTransferFrom{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
        data : felt*):
    Pausable_when_not_paused()
    ERC1155_safeTransferFrom(from_, to, tokenId, amount, data_len, data)
    return ()
end

@external
func safeBatchTransferFrom{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*, data_len : felt, data : felt*):
    Pausable_when_not_paused()
    ERC1155_safeBatchTransferFrom(
        from_, to, tokenIds_len, tokenIds, amounts_len, amounts, data_len, data)
    return ()
end

@external
func pause{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    Ownable_only_owner()
    Pausable_pause()
    return ()
end

@external
func unpause{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    Ownable_only_owner()
    Pausable_unpause()
    return ()
end
