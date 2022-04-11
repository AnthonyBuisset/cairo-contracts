# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (utils/constants.cairo)

%lang starknet

#
# Numbers
#

const UINT8_MAX = 256

#
# Interface Ids
#

# ERC165
const IERC165_ID = 0x01ffc9a7
const INVALID_ID = 0xffffffff

# Account
const IACCOUNT_ID = 0xf10dbd44

# ERC721
const IERC721_ID = 0x80ac58cd
const IERC721_RECEIVER_ID = 0x150b7a02
const IERC721_METADATA_ID = 0x5b5e139f
const IERC721_ENUMERABLE_ID = 0x780e9d63

# ERC1155
const IERC1155_ERC165 = 0xd9b67a26
const IERC1155_ERC165_TOKENRECEIVER = 0x4e2312e0
const IERC1155_ACCEPTED = 0xf23a6e61
const IERC1155_BATCH_ACCEPTED = 0xbc197c81
const IERC1155_METADATA_URI = 0x0e89341c
