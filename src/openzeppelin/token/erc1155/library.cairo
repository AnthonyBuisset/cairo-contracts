# SPDX-License-Identifier: MIT
# OpenZeppelin Cairo Contracts v0.1.0 (token/erc1155/library.cairo)

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero, assert_not_equal
from starkware.cairo.common.bool import TRUE, FALSE
from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.uint256 import Uint256, uint256_check

from openzeppelin.security.safemath import uint256_checked_add, uint256_checked_sub_le
from openzeppelin.utils.constants import (
    IACCOUNT_ID, IERC1155_ERC165, IERC1155_ERC165_TOKENRECEIVER, IERC1155_ACCEPTED,
    IERC1155_BATCH_ACCEPTED, IERC1155_METADATA_URI)
from openzeppelin.token.erc1155.interfaces.IERC1155_Receiver import IERC1155_Receiver
from openzeppelin.introspection.ERC165 import ERC165_register_interface
from openzeppelin.introspection.IERC165 import IERC165

#
# Events
#

@event
func TransferSingle(operator : felt, from_ : felt, to : felt, tokenId : Uint256, value : Uint256):
end

@event
func TransferBatch(
        operator : felt, from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*,
        values_len : felt, values : Uint256*):
end

@event
func ApprovalForAll(account : felt, operator : felt, approved : felt):
end

#
# Storage
#

@storage_var
func ERC1155_balances(account : felt, tokenId : Uint256) -> (balance : Uint256):
end

@storage_var
func ERC1155_operator_approvals(owner : felt, operator : felt) -> (res : felt):
end

@storage_var
func ERC1155_total_supply(tokenId : Uint256) -> (total_supply : Uint256):
end

@storage_var
func ERC1155_token_uri() -> (token_uri : felt):
end

#
# Constructor
#

func ERC1155_initializer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        uri : felt):
    # register IERC1155
    ERC165_register_interface(IERC1155_ERC165)
    # register IERC1155_Metadata
    ERC165_register_interface(IERC1155_METADATA_URI)
    # Store the URI
    ERC1155_token_uri.write(uri)
    return ()
end

#
# Getters
#

func ERC1155_uri{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        tokenId : Uint256) -> (uri : felt):
    let (uri) = ERC1155_token_uri.read()
    return (uri=uri)
end

func ERC1155_balanceOf{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        account : felt, tokenId : Uint256) -> (balance : Uint256):
    with_attr error_message("ERC1155: balance query for the zero address"):
        assert_not_zero(account)
    end
    let (balance : Uint256) = ERC1155_balances.read(account=account, tokenId=tokenId)
    return (balance)
end

func ERC1155_balanceOfBatch{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        account : felt, tokenIds_len : felt, tokenIds : Uint256*) -> (
        balances_len : felt, balances : Uint256*):
    alloc_locals

    with_attr error_message("ERC1155: balance query for the zero address"):
        assert_not_zero(account)
    end

    let (local balances : Uint256*) = alloc()
    _get_balances(account, tokenIds_len, tokenIds, balances)

    return (tokenIds_len, balances)
end

func ERC1155_isApprovedForAll{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt, operator : felt) -> (is_approved : felt):
    let (is_approved) = ERC1155_operator_approvals.read(owner=owner, operator=operator)
    return (is_approved)
end

#
# Externals
#

func ERC1155_setApprovalForAll{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        operator : felt, approved : felt):
    let (caller) = get_caller_address()
    with_attr error_message("ERC1155: either the caller or operator is the zero address"):
        assert_not_zero(caller * operator)
    end

    with_attr error_message("ERC1155: setting approval status for self"):
        assert_not_equal(caller, operator)
    end

    # Make sure `approved` is a boolean (0 or 1)
    with_attr error_message("ERC1155: approved is not a Cairo boolean"):
        assert approved * (1 - approved) = 0
    end

    ERC1155_operator_approvals.write(owner=caller, operator=operator, value=approved)
    ApprovalForAll.emit(caller, operator, approved)
    return ()
end

func ERC1155_safeTransferFrom{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
        data : felt*):
    alloc_locals  # todo check if needed
    with_attr error_message("ERC1155: tokenId is not a valid Uint256"):
        uint256_check(tokenId)
    end
    let (caller) = get_caller_address()
    let (is_approved) = _is_approved(spender=caller, from_=from_)
    with_attr error_message("ERC1155: either is not approved or the caller is the zero address"):
        assert_not_zero(caller * is_approved)
    end

    _safe_transfer(from_, to, tokenId, amount, data_len, data)
    return ()
end

func ERC1155_safeBatchTransferFrom{
        pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*, data_len : felt, data : felt*):
    alloc_locals  # todo check if needed
    with_attr error_message("ERC1155: tokenId is not a valid Uint256"):
        _uint256_check_all(tokenIds_len, tokenIds)
    end
    let (caller) = get_caller_address()
    let (is_approved) = _is_approved(spender=caller, from_=from_)
    with_attr error_message("ERC1155: either is not approved or the caller is the zero address"):
        assert_not_zero(caller * is_approved)
    end

    _safe_batch_transfer(from_, to, tokenIds_len, tokenIds, amounts_len, amounts, data_len, data)
    return ()
end

func ERC1155_mint{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        to : felt, tokenId : Uint256, amount : Uint256):
    with_attr error_message("ERC1155: amount is not a valid Uint256"):
        uint256_check(amount)
    end
    with_attr error_message("ERC1155: tokenId is not a valid Uint256"):
        uint256_check(tokenId)
    end
    with_attr error_message("ERC1155: cannot mint to the zero address"):
        assert_not_zero(to)
    end

    let (supply : Uint256) = ERC1155_total_supply.read(tokenId=tokenId)
    with_attr error_message("ERC1155: mint overflow"):
        let (new_supply : Uint256) = uint256_checked_add(supply, amount)
    end
    ERC1155_total_supply.write(tokenId, new_supply)

    let (balance : Uint256) = ERC1155_balances.read(account=to, tokenId=tokenId)
    # overflow is not possible because sum is guaranteed to be less than total supply which is checked for overflow above
    let (new_balance : Uint256) = uint256_checked_add(balance, amount)
    ERC1155_balances.write(to, tokenId, new_balance)

    let (caller) = get_caller_address()
    TransferSingle.emit(caller, 0, to, tokenId, amount)
    return ()
end

#
# Internals
#
func _is_approved{pedersen_ptr : HashBuiltin*, syscall_ptr : felt*, range_check_ptr}(
        spender : felt, from_ : felt) -> (res : felt):
    alloc_locals  # todo check if needed

    if spender == from_:
        return (TRUE)
    end

    let (is_operator) = ERC1155_isApprovedForAll(owner=from_, operator=spender)
    if is_operator == TRUE:
        return (TRUE)
    end

    return (FALSE)
end

func _transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256):
    with_attr error_message("ERC1155: amount is not a valid Uint256"):
        uint256_check(amount)
    end

    with_attr error_message("ERC1155: cannot transfer from the zero address"):
        assert_not_zero(from_)
    end

    with_attr error_message("ERC1155: cannot transfer to the zero address"):
        assert_not_zero(to)
    end

    _update_balance(from_, to, tokenId, amount)

    let (operator) = get_caller_address()
    TransferSingle.emit(operator, from_, to, tokenId, amount)
    return ()
end

func _batch_transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*):
    alloc_locals

    with_attr error_message("ERC1155: amount is not a valid Uint256"):
        _uint256_check_all(amounts_len, amounts)
    end

    with_attr error_message("ERC1155: cannot transfer from the zero address"):
        assert_not_zero(from_)
    end

    with_attr error_message("ERC1155: cannot transfer to the zero address"):
        assert_not_zero(to)
    end

    with_attr error_message("ERC1155: ids and amounts length mismatch"):
        assert tokenIds_len = amounts_len
    end

    # Decrease sender balance
    _update_balances(from_, to, tokenIds_len, tokenIds, amounts_len, amounts)

    # Save pedersen_ptr as the reference is being revoked due to call to get_caller_address
    local pedersen_ptr : HashBuiltin* = pedersen_ptr

    let (operator) = get_caller_address()
    TransferBatch.emit(operator, from_, to, tokenIds_len, tokenIds, amounts_len, amounts)

    return ()
end

func _update_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256):
    # Decrease sender balance
    let (sender_balance) = ERC1155_balances.read(from_, tokenId)
    with_attr error_message("ERC1155: transfer amount exceeds balance"):
        let (new_sender_balance : Uint256) = uint256_checked_sub_le(sender_balance, amount)
    end
    ERC1155_balances.write(from_, tokenId, new_sender_balance)

    # Increase receiver balance
    let (receiver_balance) = ERC1155_balances.read(to, tokenId)
    let (new_receiver_balance : Uint256) = uint256_checked_add(receiver_balance, amount)
    ERC1155_balances.write(to, tokenId, new_receiver_balance)

    return ()
end

func _update_balances{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*):
    if tokenIds_len == 0:
        return ()
    end

    _update_balance(from_, to, [tokenIds], [amounts])

    _update_balances(
        from_,
        to,
        tokenIds_len - 1,
        tokenIds + Uint256.SIZE,
        amounts_len - 1,
        amounts + Uint256.SIZE)

    return ()
end

func _safe_transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
        data : felt*):
    _transfer(from_, to, tokenId, amount)

    let (success) = _check_onERC1155Received(from_, to, tokenId, amount, data_len, data)
    with_attr error_message("ERC1155: transfer to non ERC1155Receiver implementer"):
        assert_not_zero(success)
    end
    return ()
end

func _safe_batch_transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*, data_len : felt, data : felt*):
    _batch_transfer(from_, to, tokenIds_len, tokenIds, amounts_len, amounts)

    let (success) = _check_onERC1155BatchReceived(
        from_, to, tokenIds_len, tokenIds, amounts_len, amounts, data_len, data)
    with_attr error_message("ERC1155: transfer to non ERC1155Receiver implementer"):
        assert_not_zero(success)
    end
    return ()
end

func _check_onERC1155Received{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenId : Uint256, amount : Uint256, data_len : felt,
        data : felt*) -> (success : felt):
    let (caller) = get_caller_address()
    let (is_supported) = IERC165.supportsInterface(to, IERC1155_ERC165_TOKENRECEIVER)
    if is_supported == TRUE:
        let (selector) = IERC1155_Receiver.onERC1155Received(
            to, caller, from_, tokenId, amount, data_len, data)

        with_attr error_message("ERC1155: transfer to non ERC1155Receiver implementer"):
            assert selector = IERC1155_ACCEPTED
        end
        return (TRUE)
    end

    let (is_account) = IERC165.supportsInterface(to, IACCOUNT_ID)
    return (is_account)
end

func _check_onERC1155BatchReceived{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to : felt, tokenIds_len : felt, tokenIds : Uint256*, amounts_len : felt,
        amounts : Uint256*, data_len : felt, data : felt*) -> (success : felt):
    let (caller) = get_caller_address()
    let (is_supported) = IERC165.supportsInterface(to, IERC1155_ERC165_TOKENRECEIVER)
    if is_supported == TRUE:
        let (selector) = IERC1155_Receiver.onERC1155BatchReceived(
            to, caller, from_, tokenIds_len, tokenIds, amounts_len, amounts, data_len, data)

        with_attr error_message("ERC1155: transfer to non ERC1155Receiver implementer"):
            assert selector = IERC1155_BATCH_ACCEPTED
        end
        return (TRUE)
    end

    let (is_account) = IERC165.supportsInterface(to, IACCOUNT_ID)
    return (is_account)
end

func _get_balances{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        account : felt, tokenIds_len : felt, tokenIds : Uint256*, balances : Uint256*):
    if tokenIds_len == 0:
        return ()
    end

    let (balance : Uint256) = ERC1155_balances.read(account=account, tokenId=[tokenIds])
    assert [balances] = balance
    _get_balances(account, tokenIds_len - 1, tokenIds + Uint256.SIZE, balances + Uint256.SIZE)
    return ()
end

func _uint256_check_all{range_check_ptr}(values_len : felt, values : Uint256*):
    if values_len == 0:
        return ()
    end

    uint256_check([values])

    _uint256_check_all(values_len - 1, values + Uint256.SIZE)
    return ()
end
