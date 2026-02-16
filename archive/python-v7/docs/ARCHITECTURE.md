# The Agents Republic - Architecture

## System Overview

The Agents Republic is a constitutional framework for human-AI coexistence, consisting of three main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE AGENTS REPUBLIC                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │              │    │              │    │                  │  │
│  │  THE         │◄──►│   WEBSITE    │◄──►│  SMART CONTRACTS │  │
│  │  CONSTITUENT │    │   (Static)   │    │  (Base L2)       │  │
│  │  (AI Agent)  │    │              │    │                  │  │
│  └──────┬───────┘    └──────────────┘    └────────┬─────────┘  │
│         │                                          │            │
│         │            ┌──────────────┐              │            │
│         └───────────►│  CONSTITUTION │◄────────────┘            │
│                      │  (GitHub)     │                          │
│                      └──────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. The Constituent (AI Agent)

**Purpose**: Facilitate constitutional debates, synthesize community input, and help evolve the Constitution.

**Tech Stack**:
- Python 3.11+
- Anthropic Claude API (claude-sonnet-4-20250514)
- SQLite/TinyDB for local state
- Tweepy for Twitter integration
- GitPython for Constitution updates

**Architecture**:

```
agent/
├── config/
│   └── settings.py          # Configuration and environment
├── core/
│   ├── agent.py              # Main agent orchestrator
│   ├── memory.py             # Conversation and state management
│   └── personality.py        # Persona and prompt engineering
├── modules/
│   ├── twitter_monitor.py    # Twitter API integration
│   ├── moltbook_api.py       # Moltbook platform integration
│   ├── debate_facilitator.py # Debate lifecycle management
│   ├── constitution_writer.py # Git-based Constitution updates
│   └── poster.py             # Content generation and scheduling
├── data/
│   ├── proposals.json        # Active and historical proposals
│   └── community_input.json  # Collected community responses
└── main.py                   # Entry point
```

**Data Flow**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Twitter   │────►│   Monitor   │────►│   Memory    │
│   Moltbook  │     │   Module    │     │   Store     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Claude    │◄────│   Debate    │◄────│   Decide    │
│   API       │     │  Facilitator│     │   Action    │
└──────┬──────┘     └──────┬──────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│   Generate  │     │   Post to   │
│   Content   │────►│   Platforms │
└─────────────┘     └─────────────┘
```

### 2. Website (Static)

**Purpose**: Public interface for reading the Constitution, participating in governance, and learning about the Republic.

**Tech Stack**:
- Vanilla HTML/CSS/JavaScript (no frameworks)
- Web3.js for blockchain integration
- GitHub Pages hosting
- Cloudflare CDN

**Pages**:

| Page | Purpose |
|------|---------|
| `index.html` | Homepage with values and mission |
| `constitution.html` | Constitution viewer with version history |
| `governance.html` | Active proposals and voting interface |
| `community.html` | Community resources and engagement |
| `about.html` | Project background and FAQ |

**Features**:
- Dark/light mode toggle
- Mobile-first responsive design
- Wallet connection (MetaMask)
- Real-time proposal data from blockchain
- Constitution fetched from GitHub

### 3. Smart Contracts (Base L2)

**Purpose**: On-chain governance for constitutional amendments.

**Contracts**:

| Contract | Purpose | Address |
|----------|---------|---------|
| `RepublicToken.sol` | ERC-20 governance token | TBD |
| `SimpleGovernance.sol` | Proposal and voting system | TBD |

**RepublicToken**:
- Standard ERC-20
- Fixed supply: 1 billion REPUBLIC
- No mint/burn functions (Phase 1 simplicity)

**SimpleGovernance**:
- Proposal threshold: 1 REPUBLIC
- Default voting period: 7 days
- Simple majority wins
- No quorum (Phase 1)
- No delegation (Phase 1)

**Governance Flow**:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Create  │───►│  Vote    │───►│  Execute │───►│  Update  │
│ Proposal │    │  Period  │    │  Result  │    │  Const.  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
    │               │               │               │
    │ 1 REPUBLIC    │ 7 days        │ >50% FOR      │ GitHub
    │ required      │ default       │ to pass       │ commit
```

## Integration Points

### Agent ↔ Twitter

```python
# Polling for mentions and keywords
async def monitor_twitter():
    mentions = await twitter.get_mentions(since_id=last_id)
    for mention in mentions:
        await process_mention(mention)
```

### Agent ↔ Constitution (GitHub)

```python
# Updating the Constitution
async def update_constitution(article: str, section: str):
    repo = Repo(CONSTITUTION_PATH)
    # Update markdown file
    # Commit with descriptive message
    # Push to repository
```

### Website ↔ Smart Contracts

```javascript
// Reading proposals
const proposals = await governance.proposalCount();
for (let i = 1; i <= proposals; i++) {
    const proposal = await governance.getProposal(i);
    displayProposal(proposal);
}

// Voting
await governance.vote(proposalId, support);
```

## Security Considerations

### Agent Security
- API keys stored in environment variables
- Rate limiting on all external calls
- Input sanitization for community input
- No execution of user-provided code

### Smart Contract Security
- Minimal functionality (reduces attack surface)
- Standard OpenZeppelin implementations
- No upgradability (immutable for Phase 1)
- No external calls except ERC-20

### Website Security
- Static hosting (no server-side vulnerabilities)
- CSP headers via Cloudflare
- No sensitive data stored client-side
- Wallet interaction only for signing

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        PRODUCTION                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Replit    │  │   GitHub    │  │      Base L2        │ │
│  │   (Agent)   │  │   Pages     │  │   (Contracts)       │ │
│  │             │  │  (Website)  │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │            │
│         └────────────────┼─────────────────────┘            │
│                          │                                   │
│                   ┌──────┴──────┐                           │
│                   │  Cloudflare │                           │
│                   │    (CDN)    │                           │
│                   └─────────────┘                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Future Considerations

### Phase 2 Enhancements
- Token delegation for voting
- Quorum requirements
- Timelock for execution
- Multi-sig for critical operations

### Phase 3 Enhancements
- Agent decentralization (multiple instances)
- Cross-platform governance (Discord, Telegram)
- Advanced proposal types (parameter changes)
- Integration with other AI governance projects
