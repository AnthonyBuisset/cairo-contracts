# SPDX-License-Identifier: MIT
# OpenZeppelin Contracts for Cairo v0.1.0 (token/erc1155/interfaces/ERC1155Metadata_URI.cairo)

%lang starknet

from starkware.cairo.common.uint256 import Uint256

@contract_interface
namespace ERC1155Metadata_URI:
    func uri(tokenId : Uint256) -> (uri : felt):
    end
end
