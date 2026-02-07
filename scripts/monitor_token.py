#!/usr/bin/env python3
"""
$REPUBLIC Token Monitor
========================
Post-launch monitoring for $REPUBLIC token on Base L2.

Usage:
    python scripts/monitor_token.py                  # One-time check
    python scripts/monitor_token.py --watch --interval 60  # Continuous monitoring
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("monitor")


def check_token():
    """Check token status on Base."""
    try:
        from web3 import Web3
    except ImportError:
        logger.error("Install: pip install web3")
        sys.exit(1)

    rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    token_address = os.getenv("REPUBLIC_TOKEN_ADDRESS")
    wallet_address = os.getenv("AGENT_WALLET_ADDRESS")

    if not token_address:
        logger.error("REPUBLIC_TOKEN_ADDRESS not set — token not deployed yet?")
        return None

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        logger.error(f"Cannot connect to {rpc_url}")
        return None

    # ERC20 minimal ABI for balanceOf, totalSupply, name, symbol
    erc20_abi = [
        {"constant": True, "inputs": [], "name": "name", "outputs": [{"type": "string"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "type": "function"},
        {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "type": "function"},
    ]

    token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)

    try:
        name = token.functions.name().call()
        symbol = token.functions.symbol().call()
        total_supply = token.functions.totalSupply().call()
        decimals = token.functions.decimals().call()

        info = {
            "name": name,
            "symbol": symbol,
            "total_supply": total_supply / (10 ** decimals),
            "decimals": decimals,
            "address": token_address,
        }

        if wallet_address:
            balance = token.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            info["wallet_balance"] = balance / (10 ** decimals)
            info["wallet_address"] = wallet_address

        logger.info(f"Token: {name} ({symbol})")
        logger.info(f"Address: {token_address}")
        logger.info(f"Total Supply: {info['total_supply']:,.0f}")
        if wallet_address:
            logger.info(f"Agent Wallet: {wallet_address}")
            logger.info(f"Agent Balance: {info['wallet_balance']:,.0f} {symbol}")

        return info

    except Exception as e:
        logger.error(f"Error reading token: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Monitor $REPUBLIC token")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    args = parser.parse_args()

    if args.watch:
        logger.info(f"Watching $REPUBLIC (every {args.interval}s)...")
        while True:
            check_token()
            print("---")
            time.sleep(args.interval)
    else:
        result = check_token()
        if not result:
            sys.exit(1)


if __name__ == "__main__":
    main()
