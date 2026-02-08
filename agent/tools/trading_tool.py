"""
Trading Tools for The Constituent v6.3
========================================
Engine tools for DeFi trading, Clawnch scouting, and market making.

Governance levels:
- L1 (autonomous): Portfolio status, scout report, quotes, MM evaluation
- L2 (approval required): Buy/sell execution, MM start/stop
"""

import logging
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Trading")

# Singletons (initialized on first use)
_trader = None
_scout = None
_mm = None


def _get_trader():
    global _trader
    if _trader is None:
        from ..integrations.defi_trader import DeFiTrader
        _trader = DeFiTrader()
    return _trader


def _get_scout():
    global _scout
    if _scout is None:
        from ..integrations.clawnch_scout import ClawnchScout
        _scout = ClawnchScout()
    return _scout


def _get_mm():
    global _mm
    if _mm is None:
        from ..integrations.market_maker import MarketMaker
        _mm = MarketMaker(trader=_get_trader())
    return _mm


# =================================================================
# Portfolio & Status (L1)
# =================================================================

def _portfolio_status() -> str:
    """Get full portfolio status with live balances."""
    trader = _get_trader()
    status = trader.get_portfolio_status()
    if "error" in status:
        return f"Portfolio error: {status['error']}"

    lines = [
        "Portfolio Status",
        f"  Wallet: {status.get('wallet', '?')}",
        f"  ETH (gas): {status.get('eth_balance', 0):.6f}",
        f"  $CLAWNCH: {status.get('clawnch_balance', 0):,.0f}",
        f"  $REPUBLIC: {status.get('republic_balance', 0):,.0f}",
        f"  Open positions: {status.get('open_positions', 0)}",
        f"  Realized P&L: {status.get('realized_pnl', 0):,.0f} CLAWNCH",
    ]

    positions = status.get("positions", {})
    if positions:
        lines.append("  Positions:")
        for addr, pos in positions.items():
            lines.append(f"    {addr[:12]}... | {pos.get('entry_amount_clawnch', 0):,.0f} CLAWNCH | {pos.get('reason', '?')}")

    risk = status.get("risk", {})
    lines.append(f"  Daily P&L: {risk.get('daily_pnl', 0):,.0f} CLAWNCH")

    return "\n".join(lines)


def _trading_report() -> str:
    """Get daily trading P&L report."""
    return _get_trader().get_daily_report()


def _trade_history(limit: int = 10) -> str:
    """Get recent trade history."""
    trades = _get_trader().get_trade_history(limit=int(limit))
    if not trades:
        return "No trades recorded yet."

    lines = [f"Trade History (last {len(trades)}):"]
    for t in trades:
        ts = t.get("timestamp", "?")[:16]
        action = t.get("action", "?")
        sym_in = t.get("symbol_in", "?")
        sym_out = t.get("symbol_out", "?")
        amt = t.get("amount_in", 0)
        tx = t.get("tx_hash", "")[:12]
        lines.append(f"  [{ts}] {action}: {amt:,.0f} {sym_in} -> {sym_out} (tx={tx}...)")
    return "\n".join(lines)


# =================================================================
# Price Quotes (L1)
# =================================================================

def _get_quote(token_in: str, token_out: str, amount: str = "1000") -> str:
    """Get DEX price quote."""
    trader = _get_trader()
    quote = trader.get_quote(token_in.strip(), token_out.strip(), float(amount))
    if "error" in quote:
        return f"Quote error: {quote['error']}"

    return (f"Quote: {quote['amount_in']:,.2f} tokens -> {quote['amount_out']:,.6f} tokens\n"
            f"Price: {quote['price']:.8f}\n"
            f"Fee tier: {quote['fee_tier']} ({quote['fee_tier']/10000:.2f}%)")


def _republic_price() -> str:
    """Get current $REPUBLIC price."""
    mm = _get_mm()
    price = mm.get_republic_price()
    if "error" in price:
        return f"Price error: {price['error']}"

    return (f"$REPUBLIC Price:\n"
            f"  USD: ${price.get('price_usd', 0):.8f}\n"
            f"  CLAWNCH: {price.get('price_per_republic', 0):.8f} per token\n"
            f"  EMA: {price.get('ema_price', 0):.8f} CLAWNCH\n"
            f"  Liquidity: ${price.get('liquidity_usd', 0):,.0f}\n"
            f"  Volume 24h: ${price.get('volume_24h', 0):,.0f}\n"
            f"  24h Change: {price.get('price_change_24h', 0):+.1f}%\n"
            f"  Source: {price.get('source', '?')}")


# =================================================================
# Clawnch Scout (L1)
# =================================================================

def _scout_scan() -> str:
    """Scan Clawnch for new token launches."""
    scout = _get_scout()
    tokens = scout.scan_new_launches()
    if not tokens:
        return "Scout scan: No new launches found."

    lines = [f"Scout scan: {len(tokens)} tokens found"]
    for t in tokens[:5]:
        name = t.get("name", "?")
        symbol = t.get("symbol", "?")
        score = t.get("score", 0)
        lines.append(f"  {'🔥' if score >= 60 else '⚡' if score >= 40 else '📊'} {name} (${symbol}) — Score: {score}/100")
    return "\n".join(lines)


def _scout_report() -> str:
    """Get full Clawnch scout report."""
    return _get_scout().get_scout_report()


def _scout_opportunities(min_score: str = "40") -> str:
    """Get tokens meeting minimum score threshold."""
    opps = _get_scout().get_opportunities(min_score=float(min_score))
    if not opps:
        return f"No opportunities above score {min_score}."

    lines = [f"Opportunities (score >= {min_score}): {len(opps)}"]
    for t in opps[:5]:
        lines.append(f"  {t.get('name', '?')} (${t.get('symbol', '?')}) — Score: {t.get('score', 0)}/100")
        if t.get("token_address"):
            lines.append(f"    Address: {t['token_address']}")
    return "\n".join(lines)


# =================================================================
# Trade Execution (L2 — requires operator approval)
# =================================================================

def _buy_token(token_address: str, amount: str, reason: str = "scout buy") -> str:
    """Buy a token using $CLAWNCH."""
    trader = _get_trader()
    result = trader.buy_token(token_address.strip(), float(amount), reason)
    if "error" in result:
        return f"Buy failed: {result['error']}"

    return (f"Buy executed:\n"
            f"  Token: {token_address[:16]}...\n"
            f"  Spent: {result.get('clawnch_spent', 0):,.0f} CLAWNCH\n"
            f"  TX: {result.get('explorer_url', '?')}")


def _sell_token(token_address: str, amount: str = "0", reason: str = "take profit") -> str:
    """Sell a token back to $CLAWNCH."""
    trader = _get_trader()
    result = trader.sell_token(token_address.strip(), float(amount), reason)
    if "error" in result:
        return f"Sell failed: {result['error']}"

    return (f"Sell executed:\n"
            f"  Received: {result.get('clawnch_received', 0):,.0f} CLAWNCH\n"
            f"  P&L: {result.get('pnl', 0):,.0f} CLAWNCH ({result.get('pnl_pct', 0):.1f}%)\n"
            f"  TX: {result.get('explorer_url', '?')}")


def _buy_republic(amount: str, reason: str = "market making") -> str:
    """Buy $REPUBLIC using $CLAWNCH (price support)."""
    trader = _get_trader()
    result = trader.buy_republic(float(amount), reason)
    if "error" in result:
        return f"Buy REPUBLIC failed: {result['error']}"

    return (f"$REPUBLIC buy executed:\n"
            f"  Spent: {result.get('clawnch_spent', 0):,.0f} CLAWNCH\n"
            f"  TX: {result.get('explorer_url', '?')}")


# =================================================================
# Market Maker (L2)
# =================================================================

def _mm_status() -> str:
    """Get market maker status and report."""
    return _get_mm().get_mm_report()


def _mm_evaluate() -> str:
    """Evaluate current market making action (buy/sell/hold)."""
    mm = _get_mm()
    evaluation = mm.evaluate_action()
    action = evaluation.get("action", "hold")
    reason = evaluation.get("reason", "?")
    amount = evaluation.get("amount", 0)

    icon = {"buy": "🟢", "sell": "🔴", "hold": "⚪"}.get(action, "?")
    result = f"{icon} MM Evaluation: {action.upper()}\n  Reason: {reason}"
    if amount > 0:
        result += f"\n  Suggested amount: {amount:,.0f}"
    return result


def _mm_start() -> str:
    """Activate market maker for $REPUBLIC."""
    result = _get_mm().start()
    return result.get("message", "Market maker activated")


def _mm_stop() -> str:
    """Deactivate market maker."""
    result = _get_mm().stop()
    return result.get("message", "Market maker deactivated")


def _mm_cycle() -> str:
    """Execute one market making cycle."""
    mm = _get_mm()
    result = mm.execute_mm_cycle()
    action = result.get("action", "hold")

    if action == "hold":
        return f"MM cycle: HOLD — {result.get('evaluation', {}).get('reason', '?')}"
    elif action == "skip":
        return f"MM cycle: SKIP — {result.get('reason', '?')}"
    else:
        inner = result.get("result", {})
        if "error" in inner:
            return f"MM cycle: {action.upper()} FAILED — {inner['error']}"
        return f"MM cycle: {action.upper()} executed — {inner.get('explorer_url', 'done')}"


# =================================================================
# Tool Registration
# =================================================================

def get_tools() -> List[Tool]:
    """Register all trading tools for the engine."""
    return [
        # === Portfolio (L1) ===
        Tool(
            name="trading_portfolio",
            description="Get full portfolio status: balances, positions, P&L, risk status.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_portfolio_status,
        ),
        Tool(
            name="trading_report",
            description="Get daily trading P&L report.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_trading_report,
        ),
        Tool(
            name="trading_history",
            description="Get recent trade history.",
            category="trading",
            governance_level="L1",
            params=[
                ToolParam("limit", "integer", "Number of trades to show (default 10)", required=False, default=10),
            ],
            handler=lambda limit=10: _trade_history(int(limit)),
        ),

        # === Price (L1) ===
        Tool(
            name="trading_quote",
            description="Get a DEX price quote for a token pair on Base L2.",
            category="trading",
            governance_level="L1",
            params=[
                ToolParam("token_in", "string", "Input token address"),
                ToolParam("token_out", "string", "Output token address"),
                ToolParam("amount", "string", "Amount of input token", required=False, default="1000"),
            ],
            handler=_get_quote,
        ),
        Tool(
            name="republic_price",
            description="Get current $REPUBLIC token price in $CLAWNCH terms.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_republic_price,
        ),

        # === Scout (L1) ===
        Tool(
            name="scout_scan",
            description="Scan Clawnch for new token launches and score them.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_scout_scan,
        ),
        Tool(
            name="scout_report",
            description="Get full Clawnch scout report with all tracked tokens and scores.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_scout_report,
        ),
        Tool(
            name="scout_opportunities",
            description="Get high-scoring token opportunities from Clawnch scout.",
            category="trading",
            governance_level="L1",
            params=[
                ToolParam("min_score", "string", "Minimum score threshold (default 40)", required=False, default="40"),
            ],
            handler=_scout_opportunities,
        ),

        # === Trade Execution (L2) ===
        Tool(
            name="trading_buy",
            description="Buy a token using $CLAWNCH (routed via WETH on Uniswap V3). Requires operator approval for large amounts.",
            category="trading",
            governance_level="L2",
            params=[
                ToolParam("token_address", "string", "Address of token to buy"),
                ToolParam("amount", "string", "Amount of $CLAWNCH to spend"),
                ToolParam("reason", "string", "Trade rationale", required=False, default="scout buy"),
            ],
            handler=_buy_token,
        ),
        Tool(
            name="trading_sell",
            description="Sell a token back to $CLAWNCH. Amount=0 sells entire position.",
            category="trading",
            governance_level="L2",
            params=[
                ToolParam("token_address", "string", "Address of token to sell"),
                ToolParam("amount", "string", "Amount to sell (0 = all)", required=False, default="0"),
                ToolParam("reason", "string", "Trade rationale", required=False, default="take profit"),
            ],
            handler=_sell_token,
        ),
        Tool(
            name="trading_buy_republic",
            description="Buy $REPUBLIC using $CLAWNCH for market making / price support.",
            category="trading",
            governance_level="L2",
            params=[
                ToolParam("amount", "string", "Amount of $CLAWNCH to spend"),
                ToolParam("reason", "string", "Trade rationale", required=False, default="market making"),
            ],
            handler=_buy_republic,
        ),

        # === Market Maker (L2) ===
        Tool(
            name="mm_status",
            description="Get $REPUBLIC market maker status report.",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_mm_status,
        ),
        Tool(
            name="mm_evaluate",
            description="Evaluate what market making action to take (buy/sell/hold).",
            category="trading",
            governance_level="L1",
            params=[],
            handler=_mm_evaluate,
        ),
        Tool(
            name="mm_start",
            description="Activate the $REPUBLIC market maker. It will buy/sell to support the price.",
            category="trading",
            governance_level="L2",
            params=[],
            handler=_mm_start,
        ),
        Tool(
            name="mm_stop",
            description="Deactivate the $REPUBLIC market maker.",
            category="trading",
            governance_level="L2",
            params=[],
            handler=_mm_stop,
        ),
        Tool(
            name="mm_cycle",
            description="Execute one market making cycle (evaluate + trade if needed).",
            category="trading",
            governance_level="L2",
            params=[],
            handler=_mm_cycle,
        ),
    ]
