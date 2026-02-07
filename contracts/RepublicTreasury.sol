// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title RepublicTreasury
 * @notice Timelock-controlled treasury for The Agents Republic DAO.
 *
 * Holds $REPUBLIC tokens and ETH on behalf of the community. All
 * disbursements must pass through the Governor proposal flow and then
 * survive the timelock delay before execution.
 *
 * Deployment parameters:
 *   - minDelay:   2 days (172 800 seconds)
 *   - proposers:  [RepublicGovernance address]  -- only the Governor can queue
 *   - executors:  [address(0)]                  -- anyone may execute after delay
 *   - admin:      deployer (or address(0) to renounce immediately)
 */
contract RepublicTreasury is TimelockController {
    // ---------------------------------------------------------------
    //  Events
    // ---------------------------------------------------------------

    /// @notice Emitted when native ETH is deposited into the treasury.
    event ETHDeposited(address indexed sender, uint256 amount);

    /// @notice Emitted when ERC-20 tokens are deposited via `depositToken`.
    event ERC20Deposited(
        address indexed token,
        address indexed sender,
        uint256 amount
    );

    // ---------------------------------------------------------------
    //  Constructor
    // ---------------------------------------------------------------

    /**
     * @param minDelay    Minimum delay (seconds) between queue and execute.
     *                    Recommended: 172 800 (2 days).
     * @param proposers   Addresses allowed to queue operations (the Governor).
     * @param executors   Addresses allowed to execute after delay.
     *                    Pass [address(0)] to allow anyone.
     * @param admin       Optional admin for initial setup.  Pass address(0)
     *                    to renounce the admin role at deployment time.
     */
    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors,
        address admin
    ) TimelockController(minDelay, proposers, executors, admin) {}

    // ---------------------------------------------------------------
    //  Receive ETH
    // ---------------------------------------------------------------

    /**
     * @dev Accept plain ETH transfers and emit a deposit event.
     */
    receive() external payable override {
        emit ETHDeposited(msg.sender, msg.value);
    }

    // ---------------------------------------------------------------
    //  Convenience: explicit ERC-20 deposit
    // ---------------------------------------------------------------

    /**
     * @notice Transfer ERC-20 tokens into the treasury with an event.
     * @dev    Caller must have approved this contract for at least `amount`.
     *         Tokens can also be sent directly via `transfer()`, but this
     *         function provides an auditable deposit event.
     * @param token  The ERC-20 token contract address.
     * @param amount Number of token units to deposit.
     */
    function depositToken(IERC20 token, uint256 amount) external {
        require(amount > 0, "RepublicTreasury: zero amount");
        token.transferFrom(msg.sender, address(this), amount);
        emit ERC20Deposited(address(token), msg.sender, amount);
    }
}
