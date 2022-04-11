import pytest
from starkware.starknet.testing.starknet import Starknet
from utils import (
    Signer, str_to_felt, TRUE, FALSE, get_contract_def, cached_contract, assert_revert, assert_event_emitted, to_uint, add_uint, sub_uint, MAX_UINT256, ZERO_ADDRESS, INVALID_UINT256,
)

signer = Signer(123456789987654321)

# random token IDs
TOKENS = [to_uint(5042), to_uint(793)]
TOKEN_TO_MINT = to_uint(33)
# random data (mimicking bytes in Solidity)
DATA = [0x42, 0x89, 0x55]
# URI
TOKEN_URI = str_to_felt('mock://mytoken')

INIT_SUPPLY = to_uint(10000)
AMOUNT = to_uint(200)


@pytest.fixture(scope='module')
def contract_defs():
    account_def = get_contract_def('openzeppelin/account/Account.cairo')
    erc1155_def = get_contract_def(
        'openzeppelin/token/erc1155/ERC1155_Mintable_Pausable.cairo')
    erc1155_holder_def = get_contract_def(
        'openzeppelin/token/erc1155/utils/ERC1155_Holder.cairo')
    unsupported_def = get_contract_def(
        'openzeppelin/security/initializable.cairo')

    return account_def, erc1155_def, erc1155_holder_def, unsupported_def


@pytest.fixture(scope='module')
async def erc1155_init(contract_defs):
    account_def, erc1155_def, erc1155_holder_def, unsupported_def = contract_defs
    starknet = await Starknet.empty()
    account1 = await starknet.deploy(
        contract_def=account_def,
        constructor_calldata=[signer.public_key]
    )
    account2 = await starknet.deploy(
        contract_def=account_def,
        constructor_calldata=[signer.public_key]
    )
    erc1155 = await starknet.deploy(
        contract_def=erc1155_def,
        constructor_calldata=[
            account1.contract_address, TOKEN_URI
        ]
    )
    erc1155_holder = await starknet.deploy(
        contract_def=erc1155_holder_def,
        constructor_calldata=[]
    )
    unsupported = await starknet.deploy(
        contract_def=unsupported_def,
        constructor_calldata=[]
    )
    return (
        starknet.state,
        account1,
        account2,
        erc1155,
        erc1155_holder,
        unsupported
    )


@pytest.fixture
def erc1155_factory(contract_defs, erc1155_init):
    account_def, erc1155_def, erc1155_holder_def, _ = contract_defs
    state, account1, account2, erc1155, erc1155_holder, _ = erc1155_init
    _state = state.copy()
    account1 = cached_contract(_state, account_def, account1)
    account2 = cached_contract(_state, account_def, account2)
    erc1155 = cached_contract(_state, erc1155_def, erc1155)
    erc1155_holder = cached_contract(
        _state, erc1155_holder_def, erc1155_holder)

    return erc1155, account1, account2, erc1155_holder


@pytest.fixture
async def erc1155_minted(erc1155_factory):
    erc1155, account, account2, erc1155_holder = erc1155_factory
    # mint tokens to account
    for token in TOKENS:
        await signer.send_transaction(
            account, erc1155.contract_address, 'mint', [
                account.contract_address, *token, *INIT_SUPPLY]
        )
        pass

    return erc1155, account, account2, erc1155_holder

# Fixture for testing contracts that do not accept safe ERC1155 transfers


@pytest.fixture
async def erc1155_unsupported(erc1155_minted, contract_defs, erc1155_init):
    _, _, _, unsupported_def = contract_defs
    state, _, _, _, _, unsupported = erc1155_init
    _state = state.copy()
    unsupported = cached_contract(_state, unsupported_def, unsupported)

    erc1155, account, account2, erc1155_holder = erc1155_minted
    return erc1155, account, account2, erc1155_holder, unsupported


#
# Mintable
#


@pytest.mark.asyncio
async def test_mint(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'mint', [
            account.contract_address,
            *TOKENS[1],
            *AMOUNT
        ])

    # check new balance
    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[1]).invoke()
    new_balance = execution_info.result.balance
    assert new_balance == add_uint(INIT_SUPPLY, AMOUNT)


@pytest.mark.asyncio
async def test_mint_emits_event(erc1155_factory):
    erc1155, account1, account2, _ = erc1155_factory

    tx_exec_info = await signer.send_transaction(
        account1, erc1155.contract_address, 'mint', [
            account2.contract_address,
            *TOKENS[1],
            *AMOUNT
        ])

    assert_event_emitted(
        tx_exec_info,
        from_address=erc1155.contract_address,
        name='TransferSingle',
        data=[
            account1.contract_address,
            ZERO_ADDRESS,
            account2.contract_address,
            *TOKENS[1],
            *AMOUNT
        ]
    )


@pytest.mark.asyncio
async def test_mint_to_zero_address(erc1155_factory):
    erc1155, account, _, _ = erc1155_factory

    await assert_revert(signer.send_transaction(
        account,
        erc1155.contract_address,
        'mint',
        [ZERO_ADDRESS, *TOKENS[1], *AMOUNT]
    ),
        reverted_with="ERC1155: cannot mint to the zero address"
    )


@pytest.mark.asyncio
async def test_mint_overflow(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted
    # pass_amount subtracts the already minted supply from MAX_UINT256 in order for
    # the minted supply to equal MAX_UINT256
    # (2**128 - 1, 2**128 - 1)
    pass_amount = sub_uint(MAX_UINT256, INIT_SUPPLY)

    await signer.send_transaction(
        account, erc1155.contract_address, 'mint', [
            account.contract_address,
            *TOKENS[1],
            *pass_amount
        ])

    # totalSupply is MAX_UINT256 therefore adding (1, 0) should fail
    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'mint', [
                account.contract_address,
                *TOKENS[1],
                *AMOUNT
            ]),
        reverted_with="ERC1155: mint overflow"
    )


@pytest.mark.asyncio
async def test_mint_invalid_uint256(erc1155_factory):
    erc1155, account, _, _ = erc1155_factory

    await assert_revert(signer.send_transaction(
        account,
        erc1155.contract_address,
        'mint',
        [account.contract_address, *TOKENS[1], *INVALID_UINT256]),
        reverted_with="ERC1155: amount is not a valid Uint256"
    )

#
# Pausable
#


@pytest.mark.asyncio
async def test_pause(erc1155_minted):
    erc1155, owner, other, erc1155_holder = erc1155_minted

    # pause
    await signer.send_transaction(owner, erc1155.contract_address, 'pause', [])

    execution_info = await erc1155.paused().invoke()
    assert execution_info.result.paused == TRUE

    await assert_revert(signer.send_transaction(
        owner, erc1155.contract_address, 'setApprovalForAll', [
            other.contract_address,
            TRUE
        ]),
        reverted_with="Pausable: contract is paused"
    )

    await assert_revert(signer.send_transaction(
        owner, erc1155.contract_address, 'safeTransferFrom', [
            owner.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[1],
            *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="Pausable: contract is paused"
    )

    await assert_revert(signer.send_transaction(
        owner, erc1155.contract_address, 'safeBatchTransferFrom', [
            owner.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="Pausable: contract is paused"
    )

    await assert_revert(signer.send_transaction(
        owner, erc1155.contract_address, 'mint', [
            other.contract_address,
            *TOKEN_TO_MINT, *AMOUNT
        ]),
        reverted_with="Pausable: contract is paused"
    )


@pytest.mark.asyncio
async def test_unpause(erc1155_minted):
    erc1155, owner, other, erc1155_holder = erc1155_minted

    # pause
    await signer.send_transaction(owner, erc1155.contract_address, 'pause', [])

    # unpause
    await signer.send_transaction(owner, erc1155.contract_address, 'unpause', [])

    execution_info = await erc1155.paused().invoke()
    assert execution_info.result.paused == FALSE

    await signer.send_transaction(
        owner, erc1155.contract_address, 'setApprovalForAll', [
            other.contract_address,
            TRUE
        ]
    )

    await signer.send_transaction(
        other, erc1155.contract_address, 'safeTransferFrom', [
            owner.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[1],
            *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    await signer.send_transaction(
        other, erc1155.contract_address, 'safeBatchTransferFrom', [
            owner.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    await signer.send_transaction(
        owner, erc1155.contract_address, 'mint', [
            other.contract_address,
            *TOKEN_TO_MINT,
            *AMOUNT
        ]
    )

#
# Ownable
#


@pytest.mark.asyncio
async def test_only_owner(erc1155_minted):
    erc1155, owner, other, _ = erc1155_minted

    # not-owner pause should revert
    await assert_revert(
        signer.send_transaction(
            other, erc1155.contract_address, 'pause', []),
        reverted_with="Ownable: caller is not the owner"
    )

    # owner pause
    await signer.send_transaction(owner, erc1155.contract_address, 'pause', [])

    # not-owner unpause should revert
    await assert_revert(
        signer.send_transaction(
            other, erc1155.contract_address, 'unpause', []),
        reverted_with="Ownable: caller is not the owner"
    )

    # owner unpause
    await signer.send_transaction(owner, erc1155.contract_address, 'unpause', [])


#
# balanceOf
#


@pytest.mark.asyncio
async def test_balanceOf(erc1155_factory):
    erc1155, account, other, _ = erc1155_factory

    # Initial balance should be zero
    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (to_uint(0),)

    # mint tokens to account
    await signer.send_transaction(
        account, erc1155.contract_address, 'mint', [
            account.contract_address, *TOKENS[0], *AMOUNT]
    )

    # Balance should have increased
    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)

    # Balance of other users should still be zero
    execution_info = await erc1155.balanceOf(other.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (to_uint(0),)

    # Balance for other token should still be zero
    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[1]).invoke()
    assert execution_info.result == (to_uint(0),)


@pytest.mark.asyncio
async def test_balanceOf_zero_address(erc1155_factory):
    erc1155, _, _, _ = erc1155_factory

    await assert_revert(
        erc1155.balanceOf(ZERO_ADDRESS, TOKENS[0]).invoke(),
        reverted_with="ERC1155: balance query for the zero address"
    )


#
# Metadata_URI
#


@pytest.mark.asyncio
async def test_uri(erc1155_factory):
    erc1155, account, other, _ = erc1155_factory

    # URI is the same for all tokens
    execution_info = await erc1155.uri(TOKENS[0]).invoke()
    assert execution_info.result == (TOKEN_URI,)

    execution_info = await erc1155.uri(TOKENS[1]).invoke()
    assert execution_info.result == (TOKEN_URI,)


#
# balanceOfBatch
#


@pytest.mark.asyncio
async def test_balanceOfBatch(erc1155_factory):
    erc1155, account, other, _ = erc1155_factory

    # Initial balance should be zero
    execution_info = await erc1155.balanceOfBatch(account.contract_address, TOKENS).invoke()
    assert execution_info.result == ([to_uint(0), to_uint(0)],)

    # mint tokens to account
    await signer.send_transaction(
        account, erc1155.contract_address, 'mint', [
            account.contract_address, *TOKENS[0], *AMOUNT]
    )

    await signer.send_transaction(
        account, erc1155.contract_address, 'mint', [
            account.contract_address, *TOKENS[1], *INIT_SUPPLY]
    )

    # Balance should have increased
    execution_info = await erc1155.balanceOfBatch(account.contract_address, TOKENS).invoke()
    assert execution_info.result == ([AMOUNT, INIT_SUPPLY],)

    # Balance of other users should still be zero
    execution_info = await erc1155.balanceOfBatch(other.contract_address, TOKENS).invoke()
    assert execution_info.result == ([to_uint(0), to_uint(0)],)

    # Balance for other token should still be zero
    execution_info = await erc1155.balanceOfBatch(account.contract_address, [TOKEN_TO_MINT]).invoke()
    assert execution_info.result == ([to_uint(0)],)


@pytest.mark.asyncio
async def test_balanceOfBatch_zero_address(erc1155_factory):
    erc1155, _, _, _ = erc1155_factory

    await assert_revert(
        erc1155.balanceOfBatch(ZERO_ADDRESS, TOKENS).invoke(),
        reverted_with="ERC1155: balance query for the zero address"
    )

#
# setApprovalForAll
#


@pytest.mark.asyncio
async def test_setApprovalForAll(erc1155_minted):
    erc1155, account, spender, _ = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, TRUE]
    )

    execution_info = await erc1155.isApprovedForAll(
        account.contract_address, spender.contract_address).invoke()
    assert execution_info.result == (TRUE,)


@pytest.mark.asyncio
async def test_setApprovalForAll_emits_event(erc1155_minted):
    erc1155, account, spender, _ = erc1155_minted

    tx_exec_info = await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, TRUE]
    )

    assert_event_emitted(
        tx_exec_info,
        from_address=erc1155.contract_address,
        name='ApprovalForAll',
        data=[
            account.contract_address,
            spender.contract_address,
            TRUE
        ]
    )


@pytest.mark.asyncio
async def test_setApprovalForAll_when_operator_was_set_as_not_approved(erc1155_minted):
    erc1155, account, spender, _ = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, FALSE]
    )

    await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, TRUE]
    )

    execution_info = await erc1155.isApprovedForAll(
        account.contract_address, spender.contract_address).invoke()
    assert execution_info.result == (TRUE,)


@pytest.mark.asyncio
async def test_setApprovalForAll_with_invalid_bool_arg(erc1155_minted):
    erc1155, account, spender, _ = erc1155_minted

    not_bool = 2

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'setApprovalForAll', [
                spender.contract_address,
                not_bool
            ]),
        reverted_with="ERC1155: approved is not a Cairo boolean")


@pytest.mark.asyncio
async def test_setApprovalForAll_owner_is_operator(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'setApprovalForAll', [
                account.contract_address,
                TRUE
            ]),
        reverted_with="ERC1155: setting approval status for self"
    )


@pytest.mark.asyncio
async def test_setApprovalForAll_from_zero_address(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    await assert_revert(
        erc1155.setApprovalForAll(account.contract_address, TRUE).invoke(),
        reverted_with="ERC1155: either the caller or operator is the zero address"
    )


@pytest.mark.asyncio
async def test_setApprovalForAll_operator_is_zero_address(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'setApprovalForAll', [
                ZERO_ADDRESS,
                TRUE
            ]),
        reverted_with="ERC1155: either the caller or operator is the zero address"
    )


#
# safeTransferFrom
#


@pytest.mark.asyncio
async def test_safeTransferFrom(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # check balance
    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)

    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (sub_uint(INIT_SUPPLY, AMOUNT),)


@pytest.mark.asyncio
async def test_safeTransferFrom_emits_events(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    tx_exec_info = await signer.send_transaction(
        account, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    assert_event_emitted(
        tx_exec_info,
        from_address=erc1155.contract_address,
        name='TransferSingle',
        data=[
            account.contract_address,
            account.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[0],
            *AMOUNT,
        ]
    )


@pytest.mark.asyncio
async def test_safeTransferFrom_from_operator(erc1155_minted):
    erc1155, account, spender, erc1155_holder = erc1155_minted

    # setApprovalForAll
    await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, TRUE]
    )

    # spender transfers tokens from account to erc1155_holder
    await signer.send_transaction(
        spender, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # erc1155_holder balance check
    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)


@pytest.mark.asyncio
async def test_safeTransferFrom_when_not_approved_or_owner(erc1155_minted):
    erc1155, account, spender, erc1155_holder = erc1155_minted

    # should fail when not approved or owner
    await assert_revert(signer.send_transaction(
        spender, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="ERC1155: either is not approved or the caller is the zero address"
    )


@pytest.mark.asyncio
async def test_safeTransferFrom_to_zero_address(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    # to zero address should be rejected
    await assert_revert(signer.send_transaction(
        account, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            ZERO_ADDRESS,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="ERC1155: cannot transfer to the zero address"
    )


@pytest.mark.asyncio
async def test_safeTransferFrom_from_zero_address(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    # caller address is `0` when not using an account contract
    await assert_revert(
        erc1155.safeTransferFrom(
            account.contract_address,
            erc1155_holder.contract_address,
            TOKENS[0],
            AMOUNT,
            DATA
        ).invoke(),
        reverted_with="ERC1155: either is not approved or the caller is the zero address"
    )


@pytest.mark.asyncio
async def test_safeTransferFrom_to_unsupported_contract(erc1155_unsupported):
    erc1155, account, _, _, unsupported = erc1155_unsupported

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'safeTransferFrom', [
                account.contract_address,
                unsupported.contract_address,
                *TOKENS[0],
                *AMOUNT,
                len(DATA),
                *DATA,
            ])
    )


@pytest.mark.asyncio
async def test_safeTransferFrom_to_account(erc1155_minted):
    erc1155, account, account2, _ = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'safeTransferFrom', [
            account.contract_address,
            account2.contract_address,
            *TOKENS[0],
            *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # check balance
    execution_info = await erc1155.balanceOf(account2.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)


@pytest.mark.asyncio
async def test_safeTransferFrom_invalid_uint256(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'safeTransferFrom', [
                account.contract_address,
                erc1155_holder.contract_address,
                *INVALID_UINT256,
                *AMOUNT,
                len(DATA),
                *DATA
            ]),
        reverted_with="ERC1155: tokenId is not a valid Uint256"
    )


#
# safeBatchTransferFrom
#


@pytest.mark.asyncio
async def test_safeBatchTransferFrom(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # check balances
    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)

    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (sub_uint(INIT_SUPPLY, AMOUNT),)

    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[1]).invoke()
    assert execution_info.result == (AMOUNT,)

    execution_info = await erc1155.balanceOf(account.contract_address, TOKENS[1]).invoke()
    assert execution_info.result == (sub_uint(INIT_SUPPLY, AMOUNT),)


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_emits_events(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    tx_exec_info = await signer.send_transaction(
        account, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    assert_event_emitted(
        tx_exec_info,
        from_address=erc1155.contract_address,
        name='TransferBatch',
        data=[
            account.contract_address,
            account.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
        ]
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_from_operator(erc1155_minted):
    erc1155, account, spender, erc1155_holder = erc1155_minted

    # setApprovalForAll
    await signer.send_transaction(
        account, erc1155.contract_address, 'setApprovalForAll', [
            spender.contract_address, TRUE]
    )

    # spender transfers tokens from account to erc1155_holder
    await signer.send_transaction(
        spender, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # erc1155_holder balance check
    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)

    execution_info = await erc1155.balanceOf(erc1155_holder.contract_address, TOKENS[1]).invoke()
    assert execution_info.result == (AMOUNT,)


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_when_not_approved_or_owner(erc1155_minted):
    erc1155, account, spender, erc1155_holder = erc1155_minted

    # should fail when not approved or owner
    await assert_revert(signer.send_transaction(
        spender, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            erc1155_holder.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="ERC1155: either is not approved or the caller is the zero address"
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_to_zero_address(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    # to zero address should be rejected
    await assert_revert(signer.send_transaction(
        account, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            ZERO_ADDRESS,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="ERC1155: cannot transfer to the zero address"
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_from_zero_address(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    # caller address is `0` when not using an account contract
    await assert_revert(
        erc1155.safeBatchTransferFrom(
            account.contract_address,
            erc1155_holder.contract_address,
            TOKENS,
            [AMOUNT, AMOUNT],
            DATA
        ).invoke(),
        reverted_with="ERC1155: either is not approved or the caller is the zero address"
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_to_unsupported_contract(erc1155_unsupported):
    erc1155, account, _, _, unsupported = erc1155_unsupported

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'safeBatchTransferFrom', [
                account.contract_address,
                unsupported.contract_address,
                2, *TOKENS[0], *TOKENS[1],
                2, *AMOUNT, *AMOUNT,
                len(DATA),
                *DATA,
            ])
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_to_account(erc1155_minted):
    erc1155, account, account2, _ = erc1155_minted

    await signer.send_transaction(
        account, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            account2.contract_address,
            2, *TOKENS[0], *TOKENS[1],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]
    )

    # check balance
    execution_info = await erc1155.balanceOf(account2.contract_address, TOKENS[0]).invoke()
    assert execution_info.result == (AMOUNT,)

    execution_info = await erc1155.balanceOf(account2.contract_address, TOKENS[1]).invoke()
    assert execution_info.result == (AMOUNT,)


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_invalid_uint256(erc1155_minted):
    erc1155, account, _, erc1155_holder = erc1155_minted

    await assert_revert(
        signer.send_transaction(
            account, erc1155.contract_address, 'safeBatchTransferFrom', [
                account.contract_address,
                erc1155_holder.contract_address,
                2, *TOKENS[0], *INVALID_UINT256,
                2, *AMOUNT, *AMOUNT,
                len(DATA),
                *DATA
            ]),
        reverted_with="ERC1155: tokenId is not a valid Uint256"
    )


@pytest.mark.asyncio
async def test_safeBatchTransferFrom_lengths_mismatch(erc1155_minted):
    erc1155, account, _, _ = erc1155_minted

    await assert_revert(signer.send_transaction(
        account, erc1155.contract_address, 'safeBatchTransferFrom', [
            account.contract_address,
            account.contract_address,
            1, *TOKENS[0],
            2, *AMOUNT, *AMOUNT,
            len(DATA),
            *DATA
        ]),
        reverted_with="ERC1155: ids and amounts length mismatch"
    )
