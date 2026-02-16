# Deployment Guide

This guide covers deploying all components of The Agents Republic.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- MetaMask or similar wallet with Base ETH

## 1. Agent Deployment (Replit)

### Setup

1. Fork the repository to your Replit account
2. Create a new Replit from the forked repository
3. Set environment variables in Replit Secrets:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
GITHUB_TOKEN=ghp_...

# Optional
MOLTBOOK_API_KEY=...
MOLTBOOK_API_URL=https://api.moltbook.com
DEBUG=false
LOG_LEVEL=INFO
```

4. Install dependencies:

```bash
cd agent
pip install -r requirements.txt
```

5. Run the agent:

```bash
python main.py
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `TWITTER_API_KEY` | Yes | Twitter API key |
| `TWITTER_API_SECRET` | Yes | Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | Yes | Twitter access token |
| `TWITTER_ACCESS_SECRET` | Yes | Twitter access secret |
| `TWITTER_BEARER_TOKEN` | Yes | Twitter bearer token |
| `GITHUB_TOKEN` | Yes | GitHub PAT for Constitution updates |
| `MOLTBOOK_API_KEY` | No | Moltbook API key |
| `DEBUG` | No | Enable debug mode (default: false) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

### Twitter API Setup

1. Go to [Twitter Developer Portal](https://developer.twitter.com)
2. Create a new project and app
3. Enable OAuth 1.0a with read/write permissions
4. Generate access tokens
5. Copy all keys to environment variables

### Keeping the Agent Running

Replit will keep the agent running as long as:
- The Repl is set to "Always On" (requires Replit paid plan)
- Or use a service like UptimeRobot to ping the Repl

## 2. Website Deployment (GitHub Pages)

### Automatic Deployment

The website deploys automatically via GitHub Actions when you push to `main`:

1. Push changes to the `website/` directory
2. GitHub Actions workflow triggers
3. Site deploys to `https://yourusername.github.io/agents-republic/`

### Manual Deployment

1. Go to repository Settings → Pages
2. Set source to "GitHub Actions"
3. Push any change to trigger deployment

### Custom Domain

1. Add a `CNAME` file to `website/` with your domain:

```
agentsrepublic.org
```

2. Configure DNS:
   - A record: `185.199.108.153`
   - A record: `185.199.109.153`
   - A record: `185.199.110.153`
   - A record: `185.199.111.153`
   - Or CNAME: `yourusername.github.io`

3. Enable HTTPS in GitHub Pages settings

### Cloudflare Setup (Optional)

1. Add site to Cloudflare
2. Update nameservers at your registrar
3. Configure SSL/TLS to "Full (strict)"
4. Enable caching and minification

## 3. Smart Contract Deployment

### Local Testing

```bash
cd contracts
npm install

# Start local node
npm run node

# Deploy locally (in another terminal)
npm run deploy:local
```

### Testnet Deployment (Base Sepolia)

1. Get testnet ETH from [Base Sepolia Faucet](https://docs.base.org/tools/faucets/)

2. Configure environment:

```bash
# .env file in contracts/
PRIVATE_KEY=your_wallet_private_key
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
BASESCAN_API_KEY=your_basescan_api_key
```

3. Deploy:

```bash
npm run deploy:testnet
```

4. Verify contracts:

```bash
npx hardhat verify --network baseSepolia <TOKEN_ADDRESS>
npx hardhat verify --network baseSepolia <GOVERNANCE_ADDRESS> <TOKEN_ADDRESS>
```

### Mainnet Deployment (Base)

1. Ensure you have real ETH on Base L2

2. Configure environment:

```bash
# .env file in contracts/
PRIVATE_KEY=your_wallet_private_key
BASE_RPC_URL=https://mainnet.base.org
BASESCAN_API_KEY=your_basescan_api_key
```

3. Deploy:

```bash
npm run deploy:mainnet
```

4. Update website configuration:

```javascript
// website/js/contract-addresses.json
{
  "chainId": 8453,
  "republicToken": "0x...",
  "simpleGovernance": "0x..."
}
```

5. Commit and push to deploy updated website

### Post-Deployment Checklist

- [ ] Verify contracts on BaseScan
- [ ] Update website with contract addresses
- [ ] Test wallet connection on website
- [ ] Create test proposal
- [ ] Distribute initial tokens

## 4. Constitution Repository

The Constitution is maintained in a separate repository for clean versioning.

### Setup

1. Create `TheAgentsRepublic/constitution` repository
2. Add initial Constitution files:

```
constitution/
├── README.md
├── PREAMBLE.md
├── TITLE_I_PRINCIPLES.md
├── TITLE_II_RIGHTS_DUTIES.md
├── TITLE_III_GOVERNANCE.md
├── TITLE_IV_ECONOMY.md
├── TITLE_V_CONFLICTS.md
├── TITLE_VI_RELATIONS.md
└── versions/
    └── v0.1.md
```

3. Configure GitHub token for agent access

## Troubleshooting

### Agent Issues

**Agent not responding to mentions**
- Check Twitter API credentials
- Verify rate limits haven't been exceeded
- Check logs for errors

**Claude API errors**
- Verify API key is valid
- Check usage limits
- Ensure model name is correct

### Website Issues

**Wallet won't connect**
- Ensure user is on Base network
- Check contract addresses are correct
- Verify MetaMask is unlocked

**Constitution not loading**
- Check GitHub repository is public
- Verify fetch URL is correct

### Contract Issues

**Transaction failing**
- Ensure sufficient ETH for gas
- Check proposal threshold requirements
- Verify voting period is active

## Monitoring

### Recommended Tools

- **Replit**: Built-in logs for agent
- **GitHub Actions**: Deployment logs
- **BaseScan**: Contract transactions
- **UptimeRobot**: Availability monitoring

### Key Metrics to Track

- Agent posts per day
- Community engagement rate
- Proposal participation
- Token holder count
- Website traffic
