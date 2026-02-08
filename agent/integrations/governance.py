"""
On-Chain Governance Integration — The Agents Republic
======================================================
v7.0: Direct integration with RepublicGovernance.sol on Base L2.

Provides proposal creation, voting, and governance state queries
through the deployed Governor contract.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TheConstituent.Integration.Governance")

# RepublicGovernance contract ABI (minimal — proposal + voting functions)
GOVERNOR_ABI = json.loads("""[
    {"inputs":[{"internalType":"address[]","name":"targets","type":"address[]"},
    {"internalType":"uint256[]","name":"values","type":"uint256[]"},
    {"internalType":"bytes[]","name":"calldatas","type":"bytes[]"},
    {"internalType":"string","name":"description","type":"string"}],
    "name":"propose","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"}],
    "name":"state","outputs":[{"internalType":"enum IGovernor.ProposalState","name":"","type":"uint8"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},
    {"internalType":"uint8","name":"support","type":"uint8"}],
    "name":"castVote","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},
    {"internalType":"uint8","name":"support","type":"uint8"},
    {"internalType":"string","name":"reason","type":"string"}],
    "name":"castVoteWithReason","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"}],
    "name":"proposalVotes","outputs":[
    {"internalType":"uint256","name":"againstVotes","type":"uint256"},
    {"internalType":"uint256","name":"forVotes","type":"uint256"},
    {"internalType":"uint256","name":"abstainVotes","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"proposalThreshold","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"votingDelay","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"votingPeriod","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"blockNumber","type":"uint256"}],
    "name":"quorum","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},
    {"internalType":"address","name":"account","type":"address"}],
    "name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"},
    {"internalType":"uint256","name":"timepoint","type":"uint256"}],
    "name":"getVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"}
]""")

TOKEN_ABI = json.loads("""[
    {"inputs":[{"internalType":"address","name":"delegatee","type":"address"}],
    "name":"delegate","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],
    "name":"delegates","outputs":[{"internalType":"address","name":"","type":"address"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],
    "name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],
    "name":"getVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"}
]""")

# Base L2 RPC
BASE_RPC_URL = "https://mainnet.base.org"

# Contract addresses
REPUBLIC_TOKEN_ADDRESS = "0x06B09BE0EF93771ff6a6D378dF5C7AC1c673563f"


class ProposalState(IntEnum):
    """Mirror of IGovernor.ProposalState enum."""
    Pending = 0
    Active = 1
    Canceled = 2
    Defeated = 3
    Succeeded = 4
    Queued = 5
    Expired = 6
    Executed = 7

    def label(self) -> str:
        return self.name


@dataclass
class Proposal:
    """Local representation of a governance proposal."""
    proposal_id: str
    title: str
    description: str
    proposer: str
    state: str = "unknown"
    for_votes: int = 0
    against_votes: int = 0
    abstain_votes: int = 0
    created_at: str = ""
    category: str = "standard"  # standard, constitutional, emergency


@dataclass
class GovernanceConfig:
    """Configuration for governance operations."""
    governor_address: str = ""
    token_address: str = REPUBLIC_TOKEN_ADDRESS
    rpc_url: str = BASE_RPC_URL
    private_key: str = ""
    proposals_file: str = "data/governance_proposals.json"


class GovernanceManager:
    """
    Manages on-chain governance operations for The Agents Republic.

    Responsibilities:
    - Query governance state (proposals, votes, quorum)
    - Create proposals (L2 — requires operator approval)
    - Cast votes (L1 for routine, L2 for constitutional)
    - Track proposal lifecycle
    """

    def __init__(self, config: GovernanceConfig = None):
        self.config = config or GovernanceConfig(
            governor_address=os.environ.get("REPUBLIC_GOVERNOR_ADDRESS", ""),
            private_key=os.environ.get("REPUBLIC_AGENT_PRIVATE_KEY", ""),
        )
        self._web3 = None
        self._governor = None
        self._token = None
        self._proposals_cache: Dict[str, Proposal] = {}
        self._proposals_file = Path(self.config.proposals_file)
        self._load_proposals()

    @property
    def web3(self):
        """Lazy Web3 connection."""
        if self._web3 is None:
            try:
                from web3 import Web3
                self._web3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
                if self._web3.is_connected():
                    logger.info(f"Connected to Base L2: block={self._web3.eth.block_number}")
                else:
                    logger.warning("Web3 connection failed")
            except ImportError:
                logger.warning("web3 not installed — governance reads will use cached data")
                return None
        return self._web3

    @property
    def governor(self):
        """Lazy Governor contract instance."""
        if self._governor is None and self.web3 and self.config.governor_address:
            from web3 import Web3
            self._governor = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.config.governor_address),
                abi=GOVERNOR_ABI,
            )
        return self._governor

    @property
    def token(self):
        """Lazy Token contract instance."""
        if self._token is None and self.web3 and self.config.token_address:
            from web3 import Web3
            self._token = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.config.token_address),
                abi=TOKEN_ABI,
            )
        return self._token

    # ── Queries ──────────────────────────────────────────────────────

    def get_governance_status(self) -> Dict:
        """Get current governance status — contract params + active proposals."""
        status = {
            "connected": False,
            "governor_address": self.config.governor_address,
            "token_address": self.config.token_address,
            "proposals_tracked": len(self._proposals_cache),
        }

        if self.governor:
            try:
                status["connected"] = True
                status["voting_delay"] = self.governor.functions.votingDelay().call()
                status["voting_period"] = self.governor.functions.votingPeriod().call()
                status["proposal_threshold"] = str(
                    self.governor.functions.proposalThreshold().call()
                )
                block = self.web3.eth.block_number
                status["current_block"] = block
                status["quorum"] = str(self.governor.functions.quorum(max(0, block - 1)).call())
            except Exception as e:
                logger.error(f"Governance status query failed: {e}")
                status["error"] = str(e)

        # Include local proposal summaries
        active = [p for p in self._proposals_cache.values() if p.state in ("Active", "Pending")]
        status["active_proposals"] = [
            {"id": p.proposal_id[:16] + "...", "title": p.title, "state": p.state}
            for p in active
        ]

        return status

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get detailed info about a specific proposal."""
        prop = self._proposals_cache.get(proposal_id)
        if not prop:
            return None

        result = {
            "proposal_id": prop.proposal_id,
            "title": prop.title,
            "description": prop.description,
            "proposer": prop.proposer,
            "state": prop.state,
            "for_votes": prop.for_votes,
            "against_votes": prop.against_votes,
            "abstain_votes": prop.abstain_votes,
            "category": prop.category,
            "created_at": prop.created_at,
        }

        # Refresh on-chain state if connected
        if self.governor:
            try:
                state_val = self.governor.functions.state(int(proposal_id)).call()
                result["state"] = ProposalState(state_val).label()
                votes = self.governor.functions.proposalVotes(int(proposal_id)).call()
                result["against_votes"] = votes[0]
                result["for_votes"] = votes[1]
                result["abstain_votes"] = votes[2]
                prop.state = result["state"]
                prop.for_votes = result["for_votes"]
                prop.against_votes = result["against_votes"]
                prop.abstain_votes = result["abstain_votes"]
                self._save_proposals()
            except Exception as e:
                logger.warning(f"On-chain proposal query failed: {e}")

        return result

    def get_voting_power(self, address: str) -> Dict:
        """Get an address's current voting power."""
        result = {"address": address, "balance": 0, "voting_power": 0, "delegate": ""}
        if self.token:
            try:
                from web3 import Web3
                addr = Web3.to_checksum_address(address)
                result["balance"] = self.token.functions.balanceOf(addr).call()
                result["voting_power"] = self.token.functions.getVotes(addr).call()
                result["delegate"] = self.token.functions.delegates(addr).call()
            except Exception as e:
                logger.error(f"Voting power query failed: {e}")
                result["error"] = str(e)
        return result

    def list_proposals(self, state_filter: str = None) -> List[Dict]:
        """List all tracked proposals, optionally filtered by state."""
        proposals = []
        for p in self._proposals_cache.values():
            if state_filter and p.state.lower() != state_filter.lower():
                continue
            proposals.append({
                "proposal_id": p.proposal_id,
                "title": p.title,
                "state": p.state,
                "for_votes": p.for_votes,
                "against_votes": p.against_votes,
                "category": p.category,
                "created_at": p.created_at,
            })
        return sorted(proposals, key=lambda x: x.get("created_at", ""), reverse=True)

    # ── Actions (L2 — require operator approval context) ─────────

    def create_proposal(
        self,
        title: str,
        description: str,
        targets: List[str] = None,
        values: List[int] = None,
        calldatas: List[bytes] = None,
        category: str = "standard",
    ) -> Dict:
        """
        Create a governance proposal.

        For signaling proposals (no on-chain execution), use empty targets/values/calldatas.
        Returns the proposal ID and tx hash if submitted on-chain.
        """
        from datetime import datetime, timezone

        # Create local record
        prop = Proposal(
            proposal_id="pending",
            title=title,
            description=description,
            proposer="TheConstituent",
            state="Draft",
            category=category,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # If we have on-chain capability, submit
        if self.governor and self.config.private_key:
            try:
                from web3 import Web3
                account = self.web3.eth.account.from_key(self.config.private_key)
                addr_zero = "0x0000000000000000000000000000000000000000"

                tx_targets = [Web3.to_checksum_address(t) for t in (targets or [addr_zero])]
                tx_values = values or [0]
                tx_calldatas = calldatas or [b""]

                full_description = f"# {title}\n\n{description}\n\nCategory: {category}"

                tx = self.governor.functions.propose(
                    tx_targets, tx_values, tx_calldatas, full_description
                ).build_transaction({
                    "from": account.address,
                    "nonce": self.web3.eth.get_transaction_count(account.address),
                    "gas": 500000,
                    "maxFeePerGas": self.web3.eth.gas_price * 2,
                    "maxPriorityFeePerGas": self.web3.to_wei(0.001, "gwei"),
                })

                signed = self.web3.eth.account.sign_transaction(tx, self.config.private_key)
                tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

                # Extract proposal ID from logs
                proposal_id = str(receipt.logs[0].topics[1].hex()) if receipt.logs else "unknown"
                prop.proposal_id = proposal_id
                prop.state = "Pending"

                logger.info(f"Proposal submitted on-chain: {proposal_id} tx={tx_hash.hex()}")

                self._proposals_cache[proposal_id] = prop
                self._save_proposals()

                return {
                    "status": "submitted",
                    "proposal_id": proposal_id,
                    "tx_hash": tx_hash.hex(),
                    "title": title,
                    "category": category,
                }
            except Exception as e:
                logger.error(f"On-chain proposal submission failed: {e}")
                return {"status": "error", "error": str(e), "fallback": "local_only"}

        # Fallback: local-only proposal (for off-chain signaling)
        import hashlib
        local_id = hashlib.sha256(
            f"{title}{description}{time.time()}".encode()
        ).hexdigest()[:16]
        prop.proposal_id = local_id
        prop.state = "Draft"
        self._proposals_cache[local_id] = prop
        self._save_proposals()

        return {
            "status": "draft",
            "proposal_id": local_id,
            "title": title,
            "note": "Saved locally. On-chain submission requires governor address and private key.",
        }

    def cast_vote(
        self, proposal_id: str, support: int, reason: str = ""
    ) -> Dict:
        """
        Cast a vote on a proposal.
        support: 0=Against, 1=For, 2=Abstain
        """
        if support not in (0, 1, 2):
            return {"status": "error", "error": "support must be 0 (Against), 1 (For), or 2 (Abstain)"}

        vote_label = {0: "Against", 1: "For", 2: "Abstain"}[support]

        if self.governor and self.config.private_key:
            try:
                account = self.web3.eth.account.from_key(self.config.private_key)
                pid = int(proposal_id)

                if reason:
                    tx = self.governor.functions.castVoteWithReason(
                        pid, support, reason
                    ).build_transaction({
                        "from": account.address,
                        "nonce": self.web3.eth.get_transaction_count(account.address),
                        "gas": 200000,
                        "maxFeePerGas": self.web3.eth.gas_price * 2,
                        "maxPriorityFeePerGas": self.web3.to_wei(0.001, "gwei"),
                    })
                else:
                    tx = self.governor.functions.castVote(
                        pid, support
                    ).build_transaction({
                        "from": account.address,
                        "nonce": self.web3.eth.get_transaction_count(account.address),
                        "gas": 200000,
                        "maxFeePerGas": self.web3.eth.gas_price * 2,
                        "maxPriorityFeePerGas": self.web3.to_wei(0.001, "gwei"),
                    })

                signed = self.web3.eth.account.sign_transaction(tx, self.config.private_key)
                tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
                self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

                logger.info(f"Vote cast: {vote_label} on {proposal_id} tx={tx_hash.hex()}")
                return {
                    "status": "voted",
                    "proposal_id": proposal_id,
                    "vote": vote_label,
                    "reason": reason,
                    "tx_hash": tx_hash.hex(),
                }
            except Exception as e:
                logger.error(f"On-chain vote failed: {e}")
                return {"status": "error", "error": str(e)}

        # Local-only vote recording
        prop = self._proposals_cache.get(proposal_id)
        if prop:
            if support == 1:
                prop.for_votes += 1
            elif support == 0:
                prop.against_votes += 1
            else:
                prop.abstain_votes += 1
            self._save_proposals()

        return {
            "status": "recorded_locally",
            "proposal_id": proposal_id,
            "vote": vote_label,
            "reason": reason,
            "note": "Vote recorded locally. On-chain voting requires connected wallet.",
        }

    # ── Persistence ──────────────────────────────────────────────────

    def _load_proposals(self):
        """Load proposals from local file."""
        if self._proposals_file.exists():
            try:
                data = json.loads(self._proposals_file.read_text(encoding="utf-8"))
                for item in data:
                    prop = Proposal(**item)
                    self._proposals_cache[prop.proposal_id] = prop
                logger.info(f"Loaded {len(self._proposals_cache)} proposals")
            except Exception as e:
                logger.warning(f"Failed to load proposals: {e}")

    def _save_proposals(self):
        """Save proposals to local file."""
        try:
            self._proposals_file.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for p in self._proposals_cache.values():
                data.append({
                    "proposal_id": p.proposal_id,
                    "title": p.title,
                    "description": p.description,
                    "proposer": p.proposer,
                    "state": p.state,
                    "for_votes": p.for_votes,
                    "against_votes": p.against_votes,
                    "abstain_votes": p.abstain_votes,
                    "created_at": p.created_at,
                    "category": p.category,
                })
            self._proposals_file.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save proposals: {e}")

    def refresh_all_proposals(self) -> int:
        """Refresh on-chain state for all tracked proposals."""
        updated = 0
        for pid in list(self._proposals_cache.keys()):
            result = self.get_proposal(pid)
            if result:
                updated += 1
        return updated
