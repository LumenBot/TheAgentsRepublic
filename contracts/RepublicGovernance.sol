// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/Governor.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";

/**
 * @title RepublicGovernance
 * @notice On-chain Governor contract for The Agents Republic DAO.
 *
 * Governance parameters (aligned with GOVERNANCE.md and TOKENOMICS.md):
 *   - Voting delay:       1 day   (7 200 blocks on Base at ~12 s/block)
 *   - Voting period:      7 days  (50 400 blocks)
 *   - Proposal threshold: 1 000 REPUBLIC tokens
 *   - Quorum:             10 % of total voting power
 *
 * Counting mode is simple (For / Against / Abstain).
 * Vote weight is derived from the RepublicToken (ERC20Votes) checkpoints.
 */
contract RepublicGovernance is
    Governor,
    GovernorSettings,
    GovernorCountingSimple,
    GovernorVotes,
    GovernorVotesQuorumFraction
{
    /**
     * @param _token Address of the RepublicToken (must implement IVotes).
     */
    constructor(
        IVotes _token
    )
        Governor("RepublicGovernance")
        GovernorSettings(
            7200,             // votingDelay  -- 1 day  (7 200 blocks on Base)
            50400,            // votingPeriod -- 7 days (50 400 blocks on Base)
            1000 * 10 ** 18   // proposalThreshold -- 1 000 REPUBLIC tokens
        )
        GovernorVotes(_token)
        GovernorVotesQuorumFraction(10) // 10 % quorum
    {}

    // ---------------------------------------------------------------
    //  Required overrides -- multiple-inheritance resolution
    // ---------------------------------------------------------------

    function votingDelay()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.votingDelay();
    }

    function votingPeriod()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.votingPeriod();
    }

    function proposalThreshold()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.proposalThreshold();
    }

    function quorum(
        uint256 blockNumber
    )
        public
        view
        override(Governor, GovernorVotesQuorumFraction)
        returns (uint256)
    {
        return super.quorum(blockNumber);
    }

    // ---------------------------------------------------------------
    //  Governor compatibility overrides
    // ---------------------------------------------------------------

    function state(
        uint256 proposalId
    ) public view override returns (ProposalState) {
        return super.state(proposalId);
    }

    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) public override returns (uint256) {
        return super.propose(targets, values, calldatas, description);
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override returns (uint48) {
        return super._queueOperations(
            proposalId, targets, values, calldatas, descriptionHash
        );
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override {
        super._executeOperations(
            proposalId, targets, values, calldatas, descriptionHash
        );
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override returns (uint256) {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }
}
