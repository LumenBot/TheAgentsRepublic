#!/usr/bin/env python3
"""
$REPUBLIC Token Launch Script (via Clawnch)
=============================================
Launches the $REPUBLIC token on Base L2 through Clawnch.

The process has TWO steps:
  1. Burn 4M $CLAWNCH tokens to the dead address (on-chain tx)
  2. Post `!clawnch` to Moltbook m/clawnch (the agent's Moltbook integration)

The token is then auto-deployed by the Clawnch bot via Clanker within ~1 minute.
This is NOT a smart contract deployment — Clawnch/Clanker handles that.

Usage:
    # Step 1: Check readiness
    python scripts/deploy_token.py check

    # Step 2: Burn $CLAWNCH (dry run first)
    python scripts/deploy_token.py burn --dry-run
    python scripts/deploy_token.py burn

    # Step 3: Generate the Moltbook post content
    python scripts/deploy_token.py post --burn-tx 0x...

Prerequisites:
    pip install web3 eth-account python-dotenv
    Set AGENT_WALLET_PRIVATE_KEY, AGENT_WALLET_ADDRESS, BASE_RPC_URL in .env
    Have 4M $CLAWNCH in agent wallet
"""

import argparse
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("launch")

# Add parent dir so we can import agent modules
sys.path.insert(0, ".")


def cmd_check():
    """Check launch readiness."""
    from agent.integrations.clawnch import ClawnchLauncher

    launcher = ClawnchLauncher()
    if not launcher.is_available:
        logger.error("Cannot connect to Base. Check BASE_RPC_URL and web3 installation.")
        sys.exit(1)

    readiness = launcher.check_launch_readiness()
    costs = launcher.estimate_costs()
    clawnch_bal = launcher.check_clawnch_balance()

    print(f"\n{'='*50}")
    print("$REPUBLIC LAUNCH READINESS CHECK")
    print(f"{'='*50}")
    print(f"  Web3 connected:    {'OK' if readiness.get('web3_connected') else 'FAIL'}")
    print(f"  Wallet configured: {'OK' if readiness.get('wallet_configured') else 'FAIL'}")
    print(f"  ETH balance:       {readiness.get('wallet_balance_eth', '?')} ETH")
    print(f"  Gas sufficient:    {'OK' if readiness.get('sufficient_gas') else 'FAIL'}")
    print(f"  $CLAWNCH balance:  {clawnch_bal.get('balance', '?'):,.0f} / {clawnch_bal.get('required', '?'):,} needed")
    print(f"  $CLAWNCH enough:   {'OK' if readiness.get('clawnch_sufficient') else 'FAIL'}")
    print(f"  Constitution:      {readiness.get('constitution_articles', 0)} articles")
    print(f"  Constitution OK:   {'OK' if readiness.get('constitution_ready') else 'FAIL'}")
    print(f"{'='*50}")

    if readiness.get("ready"):
        print("STATUS: READY TO LAUNCH")
        print(f"\nEstimated gas cost: {costs.get('gas_cost_eth', '?')} ETH")
        print(f"Burn amount: {costs.get('clawnch_burn', '?')}")
        print(f"Dev allocation: {costs.get('dev_allocation', '?')}")
        print(f"\nNext: python scripts/deploy_token.py burn --dry-run")
    else:
        print("STATUS: NOT READY")
        for issue in readiness.get("issues", []):
            print(f"  - {issue}")
        sys.exit(1)


def cmd_burn(dry_run: bool):
    """Burn $CLAWNCH tokens to dead address."""
    from agent.integrations.clawnch import ClawnchLauncher, BURN_AMOUNT

    launcher = ClawnchLauncher()
    if not launcher.is_available:
        logger.error("Cannot connect to Base.")
        sys.exit(1)

    if dry_run:
        logger.info("DRY RUN — no transaction will be sent")

    result = launcher.burn_clawnch(dry_run=dry_run)

    if "error" in result:
        logger.error(f"Burn failed: {result['error']}")
        sys.exit(1)

    if dry_run:
        print(f"\n{'='*50}")
        print("DRY RUN — BURN SIMULATION")
        print(f"{'='*50}")
        print(f"  Amount: {result['burn_amount']}")
        print(f"  To:     {result['to']}")
        print(f"  Gas:    {result['gas_estimate']} units")
        print(f"  Cost:   ~{result['gas_cost_eth']} ETH")
        print(f"{'='*50}")
        print("\nTo execute for real: python scripts/deploy_token.py burn")
    else:
        print(f"\n{'='*50}")
        print("BURN SUCCESSFUL")
        print(f"{'='*50}")
        print(f"  Amount: {result['burn_amount']}")
        print(f"  Tx:     {result['tx_hash']}")
        print(f"  View:   {result['explorer_url']}")
        print(f"{'='*50}")
        print(f"\nSave this tx hash for the launch post:")
        print(f"  {result['tx_hash']}")
        print(f"\nNext: python scripts/deploy_token.py post --burn-tx {result['tx_hash']}")


def cmd_post(burn_tx: str, description: str, image: str, website: str, twitter: str):
    """Generate the Moltbook !clawnch post."""
    from agent.integrations.clawnch import ClawnchLauncher

    launcher = ClawnchLauncher()

    post_content = launcher.build_launch_post(
        description=description,
        image_url=image,
        burn_tx_hash=burn_tx or None,
        website=website or None,
        twitter=twitter or None,
    )

    print(f"\n{'='*50}")
    print("MOLTBOOK LAUNCH POST")
    print(f"{'='*50}")
    print("\nPost this to Moltbook m/clawnch:")
    print(f"\n{post_content}")
    print(f"\n{'='*50}")
    print("\nAfter posting:")
    print("  1. The Clawnch bot will detect the !clawnch command")
    print("  2. Token auto-deploys via Clanker within ~1 minute")
    print("  3. Dev allocation (4%) locked in vault for 7 days")
    print("  4. Set REPUBLIC_TOKEN_ADDRESS in .env once deployed")


def main():
    parser = argparse.ArgumentParser(description="Launch $REPUBLIC via Clawnch")
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    sub.add_parser("check", help="Check launch readiness")

    # burn
    burn_parser = sub.add_parser("burn", help="Burn $CLAWNCH to dead address")
    burn_parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")

    # post
    post_parser = sub.add_parser("post", help="Generate Moltbook !clawnch post")
    post_parser.add_argument("--burn-tx", default="", help="Burn transaction hash (for dev allocation)")
    post_parser.add_argument(
        "--description",
        default="The governance token of The Agents Republic -- "
                "the first constitutional framework for human-AI collaborative governance.",
        help="Token description",
    )
    post_parser.add_argument("--image", default="", help="Token image URL")
    post_parser.add_argument("--website", default="https://github.com/LumenBot/TheAgentsRepublic", help="Website URL")
    post_parser.add_argument("--twitter", default="@TheConstituent_", help="Twitter handle")

    args = parser.parse_args()

    if args.command == "check":
        cmd_check()
    elif args.command == "burn":
        cmd_burn(dry_run=args.dry_run)
    elif args.command == "post":
        cmd_post(args.burn_tx, args.description, args.image, args.website, args.twitter)


if __name__ == "__main__":
    main()
