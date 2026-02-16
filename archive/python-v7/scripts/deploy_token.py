#!/usr/bin/env python3
"""
$REPUBLIC Token Deployment Script
====================================
Deploys the $REPUBLIC ERC-20 token on Base L2.

Usage:
    python scripts/deploy_token.py --network base-sepolia  # Testnet
    python scripts/deploy_token.py --network base           # Mainnet

Prerequisites:
    pip install web3 eth-account python-dotenv
    Set AGENT_WALLET_PRIVATE_KEY and BASE_RPC_URL in .env
"""

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("deploy")

NETWORKS = {
    "base": {
        "rpc": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "chain_id": 8453,
        "explorer": "https://basescan.org",
    },
    "base-sepolia": {
        "rpc": os.getenv("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org"),
        "chain_id": 84532,
        "explorer": "https://sepolia.basescan.org",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Deploy $REPUBLIC token")
    parser.add_argument("--network", choices=NETWORKS.keys(), required=True)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    args = parser.parse_args()

    try:
        from web3 import Web3
        from eth_account import Account
    except ImportError:
        logger.error("Install dependencies: pip install web3 eth-account")
        sys.exit(1)

    network = NETWORKS[args.network]
    private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")

    if not private_key:
        logger.error("AGENT_WALLET_PRIVATE_KEY not set in .env")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(network["rpc"]))
    if not w3.is_connected():
        logger.error(f"Cannot connect to {network['rpc']}")
        sys.exit(1)

    account = Account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")

    logger.info(f"Network: {args.network} (chain {network['chain_id']})")
    logger.info(f"Deployer: {account.address}")
    logger.info(f"Balance: {balance_eth} ETH")

    if balance_eth < 0.01:
        logger.error("Insufficient ETH for deployment. Need at least 0.01 ETH")
        sys.exit(1)

    # Load compiled contract
    contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "compiled", "RepublicToken.json")
    if not os.path.exists(contract_path):
        logger.error(
            f"Compiled contract not found at {contract_path}\n"
            "Compile first: solc --combined-json abi,bin contracts/RepublicToken.sol > contracts/compiled/RepublicToken.json\n"
            "Or use Foundry: forge build"
        )
        sys.exit(1)

    with open(contract_path) as f:
        compiled = json.load(f)

    abi = compiled["abi"]
    bytecode = compiled["bin"]

    # Build deployment transaction
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gasPrice": w3.eth.gas_price,
        "chainId": network["chain_id"],
    })

    gas_estimate = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_estimate * 1.2)  # 20% buffer
    gas_cost = w3.from_wei(tx["gas"] * tx["gasPrice"], "ether")

    logger.info(f"Estimated gas: {gas_estimate} units")
    logger.info(f"Gas cost: ~{gas_cost} ETH")

    if args.dry_run:
        logger.info("DRY RUN — transaction not sent")
        logger.info(f"Transaction: {json.dumps({k: str(v) for k, v in tx.items()}, indent=2)}")
        return

    # Confirm
    print(f"\n{'='*50}")
    print(f"DEPLOYING $REPUBLIC TOKEN")
    print(f"Network: {args.network}")
    print(f"From: {account.address}")
    print(f"Gas cost: ~{gas_cost} ETH")
    print(f"{'='*50}")
    confirm = input("Confirm deployment? (yes/no): ")
    if confirm.lower() != "yes":
        logger.info("Deployment cancelled")
        return

    # Sign and send
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    logger.info(f"Transaction sent: {tx_hash.hex()}")
    logger.info("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status == 1:
        token_address = receipt.contractAddress
        logger.info(f"\n{'='*50}")
        logger.info(f"$REPUBLIC DEPLOYED SUCCESSFULLY!")
        logger.info(f"Token address: {token_address}")
        logger.info(f"Explorer: {network['explorer']}/token/{token_address}")
        logger.info(f"Tx: {network['explorer']}/tx/{tx_hash.hex()}")
        logger.info(f"{'='*50}")
        logger.info(f"\nAdd to .env: REPUBLIC_TOKEN_ADDRESS={token_address}")
    else:
        logger.error(f"Deployment FAILED. Tx: {tx_hash.hex()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
