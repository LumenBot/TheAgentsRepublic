"""
DAO Treasury Management
========================
Tracks and manages the $REPUBLIC treasury for The Agents Republic.

Treasury funds:
- Agent operational costs (Claude API, hosting)
- Community grants
- Partnership funding
- Development bounties
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TheConstituent.Treasury")


class TreasuryManager:
    """Manages the DAO treasury for The Agents Republic."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.ledger_file = self.data_dir / "treasury_ledger.json"
        self._ledger: List[Dict] = []
        self._load()

    def _load(self):
        """Load ledger from disk."""
        if self.ledger_file.exists():
            try:
                self._ledger = json.loads(self.ledger_file.read_text())
            except Exception:
                self._ledger = []

    def _save(self):
        """Save ledger to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file.write_text(
            json.dumps(self._ledger, indent=2, default=str)
        )

    def record_transaction(
        self,
        tx_type: str,
        amount: float,
        currency: str = "REPUBLIC",
        description: str = "",
        reference: str = "",
    ) -> Dict:
        """
        Record a treasury transaction.

        Args:
            tx_type: "income" or "expense"
            amount: Amount (positive)
            currency: Token symbol (REPUBLIC, ETH, etc.)
            description: What the transaction is for
            reference: On-chain tx hash or proposal ID
        """
        entry = {
            "id": len(self._ledger) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": tx_type,
            "amount": amount,
            "currency": currency,
            "description": description,
            "reference": reference,
        }

        self._ledger.append(entry)
        self._save()

        logger.info(f"Treasury {tx_type}: {amount} {currency} — {description}")
        return {"status": "ok", "entry": entry}

    def get_balance(self) -> Dict:
        """Calculate current treasury balance by currency."""
        balances: Dict[str, float] = {}

        for entry in self._ledger:
            currency = entry["currency"]
            amount = entry["amount"]
            if currency not in balances:
                balances[currency] = 0.0

            if entry["type"] == "income":
                balances[currency] += amount
            elif entry["type"] == "expense":
                balances[currency] -= amount

        return balances

    def get_monthly_report(self, year: int = None, month: int = None) -> Dict:
        """Generate monthly treasury report."""
        now = datetime.now(timezone.utc)
        year = year or now.year
        month = month or now.month

        monthly = [
            e for e in self._ledger
            if e["timestamp"].startswith(f"{year}-{month:02d}")
        ]

        income = sum(e["amount"] for e in monthly if e["type"] == "income")
        expenses = sum(e["amount"] for e in monthly if e["type"] == "expense")

        return {
            "period": f"{year}-{month:02d}",
            "income": income,
            "expenses": expenses,
            "net": income - expenses,
            "transactions": len(monthly),
            "balance": self.get_balance(),
        }

    def get_status(self) -> Dict:
        """Get treasury status summary."""
        balance = self.get_balance()
        return {
            "balances": balance,
            "total_transactions": len(self._ledger),
            "last_transaction": self._ledger[-1] if self._ledger else None,
        }
