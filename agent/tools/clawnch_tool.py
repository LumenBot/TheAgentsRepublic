"""
Clawnch Launch Tools for The Constituent v6.0
===============================================
Exposes $REPUBLIC token launch operations as tools for the engine.

Tools:
- clawnch_status: Check Clawnch integration status
- clawnch_readiness: Run all pre-flight checks
- clawnch_balance: Check $CLAWNCH token balance
- clawnch_burn: Execute the $CLAWNCH burn transaction
- clawnch_upload_image: Upload token image to Clawnch hosting
- clawnch_validate: Validate launch content via preview API
- clawnch_build_post: Build the !clawnch post content
- clawnch_check_tx: Check status of a previously sent transaction
- clawnch_launch: Full launch sequence (burn + upload + validate + post)
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..integrations.clawnch import ClawnchLauncher

logger = logging.getLogger("TheConstituent.Tools.Clawnch")

_launcher: ClawnchLauncher = None


def _get_launcher() -> ClawnchLauncher:
    global _launcher
    if _launcher is None:
        _launcher = ClawnchLauncher()
    return _launcher


def _clawnch_status() -> str:
    launcher = _get_launcher()
    return json.dumps(launcher.get_status(), indent=2, default=str)


def _clawnch_readiness() -> str:
    launcher = _get_launcher()
    checks = launcher.check_launch_readiness()
    return json.dumps(checks, indent=2, default=str)


def _clawnch_metadata() -> str:
    launcher = _get_launcher()
    return json.dumps(launcher.get_token_metadata(), indent=2, default=str)


def _clawnch_balance() -> str:
    launcher = _get_launcher()
    result = launcher.get_clawnch_balance()
    return json.dumps(result, indent=2, default=str)


def _clawnch_check_tx(tx_hash: str) -> str:
    launcher = _get_launcher()
    result = launcher.check_tx(tx_hash)
    return json.dumps(result, indent=2, default=str)


def _clawnch_burn() -> str:
    launcher = _get_launcher()
    result = launcher.execute_burn()
    return json.dumps(result, indent=2, default=str)


def _clawnch_upload_image() -> str:
    launcher = _get_launcher()
    result = launcher.upload_image()
    return json.dumps(result, indent=2, default=str)


def _clawnch_validate(image_url: str, burn_tx_hash: str = "") -> str:
    launcher = _get_launcher()
    result = launcher.validate_launch(image_url, burn_tx_hash)
    return json.dumps(result, indent=2, default=str)


def _clawnch_build_post(image_url: str, burn_tx_hash: str = "") -> str:
    launcher = _get_launcher()
    return launcher.build_launch_post(image_url, burn_tx_hash)


def _clawnch_launch(burn_tx_hash: str = "") -> str:
    """Execute the launch sequence: upload → validate → build post.

    If burn_tx_hash is provided, skips the burn step and verifies the
    existing tx. If not provided, executes a new burn first.
    """
    import time as _time
    launcher = _get_launcher()
    steps = []

    if burn_tx_hash:
        # Burn already done — verify it
        steps.append(f"=== STEP 1: Verify existing burn tx ===")
        steps.append(f"tx_hash: {burn_tx_hash}")
        check = launcher.check_tx(burn_tx_hash)
        if check.get("status") == "confirmed":
            steps.append(f"Burn CONFIRMED in block {check.get('block')}")
        elif check.get("status") == "reverted":
            steps.append("LAUNCH ABORTED: Burn transaction reverted")
            steps.append(json.dumps(check, indent=2, default=str))
            return "\n".join(steps)
        elif check.get("error"):
            steps.append(f"WARNING: Could not verify burn: {check.get('error')}")
            steps.append("Proceeding anyway — Clawnch scanner will verify on-chain.")
        else:
            steps.append(f"Burn status: {check.get('status', 'unknown')} — proceeding.")
    else:
        # Step 1: Burn (fire-and-forget broadcast)
        steps.append("=== STEP 1: Burn $CLAWNCH ===")
        burn_result = launcher.execute_burn()
        steps.append(json.dumps(burn_result, indent=2, default=str))
        if "error" in burn_result:
            steps.append("LAUNCH ABORTED: Burn failed")
            return "\n".join(steps)
        burn_tx_hash = burn_result["tx_hash"]

        # Step 1b: Quick confirmation poll (Base blocks are ~2s)
        steps.append("\n=== STEP 1b: Verify burn confirmation ===")
        confirmed = False
        for i in range(5):
            _time.sleep(3)
            check = launcher.check_tx(burn_tx_hash)
            if check.get("status") == "confirmed":
                steps.append(f"Burn CONFIRMED in block {check.get('block')}")
                confirmed = True
                break
            elif check.get("status") == "reverted":
                steps.append("LAUNCH ABORTED: Burn transaction reverted")
                steps.append(json.dumps(check, indent=2, default=str))
                return "\n".join(steps)
        if not confirmed:
            steps.append("Burn broadcast but not yet confirmed after 15s.")
            steps.append("Use clawnch_check_tx to verify before posting.")
            steps.append(f"tx_hash: {burn_tx_hash}")
            return "\n".join(steps)

    # Step 2: Upload image
    steps.append("\n=== STEP 2: Upload image ===")
    upload_result = launcher.upload_image()
    steps.append(json.dumps(upload_result, indent=2, default=str))
    if "error" in upload_result:
        steps.append("WARNING: Image upload failed, using raw GitHub URL")
        from agent.config.tokenomics import tokenomics
        image_url = tokenomics.IMAGE_URL
    else:
        image_url = upload_result["image_url"]

    # Step 3: Validate
    steps.append("\n=== STEP 3: Validate content ===")
    validate_result = launcher.validate_launch(image_url, burn_tx_hash)
    steps.append(json.dumps(validate_result, indent=2, default=str))

    # Step 4: Build post
    steps.append("\n=== STEP 4: Launch post content ===")
    post_content = launcher.build_launch_post(image_url, burn_tx_hash)
    steps.append(post_content)

    # Step 5: Post on Moltbook m/clawnch
    steps.append("\n=== STEP 5: Post on Moltbook m/clawnch ===")
    try:
        from ..moltbook_ops import MoltbookOperations
        mb = MoltbookOperations()
        if not mb.is_connected():
            steps.append("ERROR: Moltbook not connected. Post manually:")
            steps.append(f'  title: "$REPUBLIC Token Launch"')
            steps.append(f'  submolt: "clawnch"')
            steps.append(f"  content:\n{post_content}")
            return "\n".join(steps)

        result = mb.create_post(
            title="$REPUBLIC Token Launch",
            content=post_content,
            submolt="clawnch",
        )
        steps.append(json.dumps(result, indent=2, default=str))

        if result.get("success"):
            post_url = result.get("url", "")
            steps.append(f"\n=== LAUNCH POSTED SUCCESSFULLY ===")
            steps.append(f"URL: {post_url}")
            steps.append("Clawnch scanner will detect and deploy within ~1 minute.")
        else:
            steps.append(f"Post failed: {result.get('error', 'unknown')}")
            steps.append("Post content for manual retry:")
            steps.append(post_content)
    except Exception as e:
        steps.append(f"Post error: {e}")
        steps.append("Post content for manual retry:")
        steps.append(post_content)

    return "\n".join(steps)


def get_tools() -> List[Tool]:
    """Register Clawnch launch tools."""
    return [
        Tool(
            name="clawnch_status",
            description="Check Clawnch integration status (web3, wallet, contract).",
            category="token",
            params=[],
            handler=_clawnch_status,
        ),
        Tool(
            name="clawnch_readiness",
            description="Run all pre-flight checks for $REPUBLIC token launch.",
            category="token",
            params=[],
            handler=_clawnch_readiness,
        ),
        Tool(
            name="clawnch_metadata",
            description="Get $REPUBLIC token metadata (name, symbol, description, image, website, twitter).",
            category="token",
            params=[],
            handler=_clawnch_metadata,
        ),
        Tool(
            name="clawnch_balance",
            description="Check $CLAWNCH token balance of agent wallet on Base.",
            category="token",
            params=[],
            handler=_clawnch_balance,
        ),
        Tool(
            name="clawnch_check_tx",
            description="Check status of a transaction on Base (confirmed, pending, not_found). Use to verify burn.",
            category="token",
            params=[
                ToolParam("tx_hash", "string", "Transaction hash (0x...)"),
            ],
            handler=_clawnch_check_tx,
        ),
        Tool(
            name="clawnch_burn",
            description="Broadcast the $CLAWNCH burn tx (fire-and-forget). Returns tx_hash immediately. Use clawnch_check_tx to verify. IRREVERSIBLE.",
            category="token",
            governance_level="L2",
            params=[],
            handler=_clawnch_burn,
        ),
        Tool(
            name="clawnch_upload_image",
            description="Upload token image to Clawnch hosting (iili.io). Returns hosted URL.",
            category="token",
            params=[],
            handler=_clawnch_upload_image,
        ),
        Tool(
            name="clawnch_validate",
            description="Validate launch content via Clawnch preview API before posting.",
            category="token",
            params=[
                ToolParam("image_url", "string", "Hosted image URL (from clawnch_upload_image)"),
                ToolParam("burn_tx_hash", "string", "Burn transaction hash", required=False, default=""),
            ],
            handler=_clawnch_validate,
        ),
        Tool(
            name="clawnch_build_post",
            description="Build the !clawnch post content string for Moltbook submission.",
            category="token",
            params=[
                ToolParam("image_url", "string", "Hosted image URL (from clawnch_upload_image)"),
                ToolParam("burn_tx_hash", "string", "Burn transaction hash", required=False, default=""),
            ],
            handler=_clawnch_build_post,
        ),
        Tool(
            name="clawnch_launch",
            description="Full $REPUBLIC launch sequence: upload image → validate → build post. If burn_tx_hash is provided, skips burn and uses existing tx. Otherwise burns first.",
            category="token",
            governance_level="L2",
            params=[
                ToolParam("burn_tx_hash", "string", "Existing burn tx hash (skip burn step). Required if burn already done.", required=False, default=""),
            ],
            handler=_clawnch_launch,
        ),
    ]
