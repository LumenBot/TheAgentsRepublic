// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title RepublicToken
 * @notice ERC-20 governance token for The Agents Republic DAO on Base L2.
 *
 * Fixed supply of 1 billion REPUBLIC tokens, all minted to the deployer at
 * construction time. No mint function exists after deployment -- supply can
 * never increase.
 *
 * Supports:
 *   - ERC20Votes  -- on-chain delegation, checkpoints, and vote weight
 *                    queries required by the Governor contract.
 *   - ERC20Permit -- gasless approvals via EIP-2612 signatures.
 *   - ERC6372    -- clock mode declaration (block-number based on Base).
 *   - Ownable    -- deployer is the initial owner.
 */
contract RepublicToken is ERC20, ERC20Permit, ERC20Votes, Ownable {
    /// @notice Total supply: 1 billion tokens with 18 decimals.
    uint256 private constant TOTAL_SUPPLY = 1_000_000_000 * 10 ** 18;

    /**
     * @param No external parameters -- deployer receives all tokens.
     */
    constructor()
        ERC20("The Agents Republic", "REPUBLIC")
        ERC20Permit("The Agents Republic")
        Ownable(msg.sender)
    {
        _mint(msg.sender, TOTAL_SUPPLY);
    }

    // ---------------------------------------------------------------
    //  Required overrides -- ERC20Votes compatibility
    // ---------------------------------------------------------------

    /**
     * @dev Hook into every transfer so ERC20Votes can update checkpoints.
     */
    function _update(
        address from,
        address to,
        uint256 value
    ) internal override(ERC20, ERC20Votes) {
        super._update(from, to, value);
    }

    /**
     * @dev Shared nonce storage between ERC20Permit and the base Nonces
     *      contract used by ERC20Votes.
     */
    function nonces(
        address owner
    ) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }

    // ---------------------------------------------------------------
    //  ERC6372 -- Clock mode
    // ---------------------------------------------------------------

    /**
     * @dev Returns the current block number as the governance clock value.
     *      Base L2 produces blocks at ~12 s cadence, matching the Governor's
     *      block-denominated voting delay and period.
     */
    function clock() public view override returns (uint48) {
        return uint48(block.number);
    }

    /**
     * @dev Machine-readable clock mode descriptor (EIP-6372).
     */
    // solhint-disable-next-line func-name-mixedcase
    function CLOCK_MODE() public pure override returns (string memory) {
        return "mode=blocknumber&from=default";
    }
}
