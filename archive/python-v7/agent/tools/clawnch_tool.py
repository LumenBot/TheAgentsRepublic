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
import re
from typing import List

from ..tool_registry import Tool, ToolParam
from ..integrations.clawnch import ClawnchLauncher

logger = logging.getLogger("TheConstituent.Tools.Clawnch")


# ---------------------------------------------------------------------------
# Moltbook verification challenge solver
# ---------------------------------------------------------------------------
_WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000,
}


def _words_to_number(words: list) -> float:
    """Convert a list of number words to a numeric value.

    Handles patterns like: ["thirty", "five"] → 35,
    ["two", "hundred", "fifty"] → 250, ["twelve"] → 12.
    """
    if not words:
        return 0
    total = 0
    current = 0
    for w in words:
        val = _WORD_TO_NUM.get(w)
        if val is None:
            continue
        if val == 100:
            current = (current or 1) * 100
        elif val == 1000:
            current = (current or 1) * 1000
            total += current
            current = 0
        else:
            current += val
    total += current
    return float(total)


def _clean_tokens(text: str) -> list:
    """Split challenge text into cleaned lowercase tokens.

    Handles Moltbook obfuscation that inserts special chars inside words:
      "tW/eN tY" → ["twen", "ty"]  (strip non-alpha within each token)
    Preserves standalone operator symbols (+, -, *, /) as tokens.
    """
    raw_tokens = text.split()
    cleaned = []
    for tok in raw_tokens:
        # Preserve standalone operator symbols
        stripped = tok.strip()
        if stripped in ("+", "-", "*", "/"):
            cleaned.append(stripped)
            continue
        c = re.sub(r"[^a-zA-Z]", "", tok).lower()
        if c:
            cleaned.append(c)
    return cleaned


def _extract_number_words(tokens: list) -> list:
    """Extract number words from tokens, joining fragments as needed.

    Handles Moltbook obfuscation:
    1. Exact match: "twenty" in _WORD_TO_NUM → ✓
    2. Join 2-3 adjacent tokens: "twen"+"ty" → "twenty" ✓
    3. Substring match: "qthree" contains "three" → ✓
       Checks if token starts or ends with a known number word.
    """
    found = []
    i = 0
    while i < len(tokens):
        matched = False
        # Try joining 3 adjacent tokens
        if not matched and i + 2 < len(tokens):
            tri = tokens[i] + tokens[i + 1] + tokens[i + 2]
            if tri in _WORD_TO_NUM:
                found.append(tri)
                i += 3
                continue
        # Try joining 2 adjacent tokens
        if not matched and i + 1 < len(tokens):
            pair = tokens[i] + tokens[i + 1]
            if pair in _WORD_TO_NUM:
                found.append(pair)
                i += 2
                continue
        # Try single token exact match
        if tokens[i] in _WORD_TO_NUM:
            found.append(tokens[i])
            i += 1
            continue
        # Try fuzzy: token contains a number word (prefix/suffix noise)
        hit = _fuzzy_match(tokens[i])
        if hit:
            found.append(hit)
            # Also try joining with next token after stripping noise
            i += 1
            continue
        # Try joining current (fuzzy) + next
        if i + 1 < len(tokens):
            pair = tokens[i] + tokens[i + 1]
            hit = _fuzzy_match(pair)
            if hit:
                found.append(hit)
                i += 2
                continue
        i += 1
    return found


def _fuzzy_match(token: str) -> str:
    """Try to find a number word inside a noisy token.

    Handles Moltbook obfuscation strategies:
    1. Prefix/suffix noise: "qthree" → "three", "twentyq" → "twenty"
    2. Internal duplicate letters: "thiirty" → "thirty", "fooour" → "four"
    Uses subsequence matching with strict constraints to avoid false positives.
    """
    # Sort by length descending to prefer longer matches
    for word in sorted(_WORD_TO_NUM.keys(), key=len, reverse=True):
        if len(word) < 4:
            continue  # Skip short words (one/two/six/ten) to avoid false positives
        # Exact containment
        if word in token:
            return word
        # Subsequence match: word's letters appear in order within token
        # Strict constraint: token length within word_len + 3 extra chars max
        if len(token) <= len(word) + 3 and _is_subsequence(word, token):
            return word
    return ""


def _is_subsequence(word: str, token: str) -> bool:
    """Check if all chars of word appear in order within token."""
    it = iter(token)
    return all(c in it for c in word)


def _solve_challenge(challenge_text: str) -> str:
    """Solve a Moltbook anti-spam math challenge.

    Works entirely on the token list to avoid position-mapping bugs:
    1. Tokenize (strip non-alpha per token, lowercase)
    2. Find operator in token list (explicit symbol or keyword)
    3. Split tokens at operator, extract numbers from each side
    4. Calculate
    """
    # Try to find explicit decimal numbers first (e.g., "35.5 + 12.3")
    digit_match = re.findall(r"(\d+\.?\d*)\s*([+\-*/])\s*(\d+\.?\d*)", challenge_text)
    if digit_match:
        a, op, b = float(digit_match[0][0]), digit_match[0][1], float(digit_match[0][2])
        return _calc(a, op, b)

    # Tokenize the original challenge text
    tokens = _clean_tokens(challenge_text)

    # Find operator and its position in the token list
    op_char, op_idx = _find_operator_in_tokens(tokens)

    if op_char and op_idx >= 0:
        left_tokens = tokens[:op_idx]
        right_tokens = tokens[op_idx + 1:]  # skip the operator token itself

        left_nums = _extract_number_words(left_tokens)
        right_nums = _extract_number_words(right_tokens)

        if left_nums and right_nums:
            a = _words_to_number(left_nums)
            b = _words_to_number(right_nums)
            return _calc(a, op_char, b)

    # Last resort: find all number words and assume addition
    all_nums = _extract_number_words(tokens)
    if len(all_nums) >= 2:
        # Last number word is right operand, rest is left
        a = _words_to_number(all_nums[:-1])
        b = _words_to_number(all_nums[-1:])
        if a and b:
            return f"{a + b:.2f}"
    if all_nums:
        return f"{_words_to_number(all_nums):.2f}"

    return ""


# Operator keyword sets (matched against token list)
_OP_KEYWORDS = {
    "+": {"accelerates", "accelerate", "adds", "add", "increases",
          "increase", "gains", "gain", "plus", "combined"},
    "-": {"decelerates", "decelerate", "slows", "slow", "loses",
          "lose", "minus", "decreases", "decrease", "subtracts",
          "subtract", "less"},
    "*": {"multiplies", "multiply", "times", "multiplied"},
}


def _find_operator_in_tokens(tokens: list):
    """Find operator type and position in the token list.

    Returns (op_char, op_idx) or (None, -1) if not found.
    Checks explicit symbols first, then keyword-based operators.
    """
    # 1) Explicit operator symbol as a standalone token
    for i, tok in enumerate(tokens):
        if tok in ("+", "-", "*", "/"):
            return tok, i

    # 2) Keyword-based operators
    for i, tok in enumerate(tokens):
        for op, keywords in _OP_KEYWORDS.items():
            if tok in keywords:
                # The split point is this keyword token.
                # For "accelerates by", skip "by" too if next token is "by".
                skip = i
                if i + 1 < len(tokens) and tokens[i + 1] == "by":
                    skip = i + 1
                return op, skip

    return None, -1


def _calc(a: float, op: str, b: float) -> str:
    if op == "+":
        return f"{a + b:.2f}"
    elif op == "-":
        return f"{a - b:.2f}"
    elif op == "*":
        return f"{a * b:.2f}"
    elif op == "/" and b != 0:
        return f"{a / b:.2f}"
    return "0.00"

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

    # Abort if validation failed
    val_response = validate_result.get("response", {})
    if val_response.get("valid") is False:
        errors = val_response.get("errors", [])
        steps.append("\nLAUNCH ABORTED: Validation failed")
        for err in errors:
            steps.append(f"  - {err}")
        return "\n".join(steps)

    # Step 4: Build post
    steps.append("\n=== STEP 4: Launch post content ===")
    post_content = launcher.build_launch_post(image_url, burn_tx_hash)
    steps.append(post_content)

    # Step 5: Post on Moltbook m/clawnch + auto-verify
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

        if not result.get("success"):
            steps.append(f"Post failed: {result.get('error', 'unknown')}")
            steps.append("Post content for manual retry:")
            steps.append(post_content)
            return "\n".join(steps)

        # Auto-verify if verification challenge present
        response_data = result.get("response", {})
        verification = response_data.get("verification", {})
        if verification.get("code") and verification.get("challenge"):
            steps.append("\n=== STEP 6: Auto-verify challenge ===")
            challenge = verification["challenge"]
            code = verification["code"]
            steps.append(f"Challenge: {challenge}")

            answer = _solve_challenge(challenge)
            steps.append(f"Answer: {answer}")

            if answer:
                verify_result = mb.verify_post(code, answer)
                steps.append(json.dumps(verify_result, indent=2, default=str))
                if verify_result.get("success"):
                    steps.append("Verification PASSED")
                else:
                    steps.append(f"Verification failed: {verify_result.get('response', '')}")
                    steps.append("Post may need manual re-verification.")
            else:
                steps.append("Could not solve challenge automatically.")
                steps.append(f"Verification code: {code}")
                steps.append("Solve manually and POST to /api/v1/verify")

        post_data = response_data.get("post", {})
        post_id = post_data.get("id", result.get("post_id"))
        post_url = f"https://www.moltbook.com/post/{post_id}" if post_id else ""
        steps.append(f"\n=== LAUNCH POSTED ===")
        steps.append(f"Post ID: {post_id}")
        steps.append(f"URL: {post_url}")
        steps.append("Clawnch scanner will detect and deploy within ~1 minute.")

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
