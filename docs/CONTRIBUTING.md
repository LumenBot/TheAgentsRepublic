# Contributing to The Agents Republic

Thank you for your interest in contributing to The Agents Republic! This project is built on the principles of collective evolution and distributed sovereignty—your contributions matter.

## Ways to Contribute

### 1. Participate in Constitutional Debates

The most important contribution is participating in shaping the Constitution:

- Follow [@TheConstituent_](https://twitter.com/TheConstituent_) on X
- Respond to daily debate questions
- Share your perspectives on human-AI governance
- Vote on proposals with $REPUBLIC tokens

### 2. Contribute Code

We welcome code contributions to all components:

- **Agent**: Python improvements, new modules, bug fixes
- **Website**: UI/UX improvements, accessibility, features
- **Contracts**: Security improvements, testing, documentation

### 3. Improve Documentation

Help make the project more accessible:

- Fix typos and clarify explanations
- Add examples and tutorials
- Translate documentation
- Write blog posts or guides

### 4. Report Issues

Found a bug or have a feature idea?

- Check existing issues first
- Provide detailed reproduction steps
- Include relevant logs or screenshots
- Suggest potential solutions if you have ideas

## Development Setup

### Agent Development

```bash
# Clone the repository
git clone https://github.com/TheAgentsRepublic/agents-republic.git
cd agents-republic

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
cd agent
pip install -r requirements.txt
pip install -r requirements-dev.txt  # includes testing tools

# Run tests
pytest

# Run linting
flake8 .
black --check .
```

### Website Development

```bash
# No build step required - it's static HTML/CSS/JS

# Serve locally
cd website
python -m http.server 8000
# Visit http://localhost:8000
```

### Contract Development

```bash
cd contracts
npm install

# Run local node
npm run node

# Run tests
npm test

# Deploy locally
npm run deploy:local
```

## Pull Request Process

### 1. Fork and Branch

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/YOUR_USERNAME/agents-republic.git

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow the code style of the project
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and well-described

### 3. Test Your Changes

```bash
# Agent
cd agent && pytest

# Contracts
cd contracts && npm test
```

### 4. Submit PR

- Fill out the PR template
- Link related issues
- Request review from maintainers
- Respond to feedback promptly

## Code Style

### Python (Agent)

- Follow PEP 8
- Use type hints
- Format with Black
- Maximum line length: 88 characters
- Docstrings for all public functions

```python
async def synthesize_responses(
    self,
    question: str,
    responses: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Synthesize community responses to a debate.

    Args:
        question: The original debate question
        responses: List of community responses

    Returns:
        Synthesis including consensus, disagreements, and novel ideas
    """
    ...
```

### JavaScript (Website)

- Use vanilla JS (no frameworks)
- ES6+ features are fine
- Consistent 2-space indentation
- JSDoc comments for functions

```javascript
/**
 * Connect to user's wallet
 * @returns {Promise<string>} Connected wallet address
 */
async function connectWallet() {
    ...
}
```

### Solidity (Contracts)

- Follow Solidity style guide
- Use NatSpec comments
- Prefer custom errors over require strings
- Keep functions simple and focused

```solidity
/// @notice Create a new proposal
/// @param description The proposal description
/// @return proposalId The ID of the created proposal
function propose(string calldata description) external returns (uint256 proposalId) {
    ...
}
```

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add vote delegation to SimpleGovernance

- Implement delegate() function
- Add delegatee tracking
- Update voting power calculation
- Add tests for delegation scenarios
```

Prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Code of Conduct

### Our Pledge

We pledge to make participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated promptly and fairly.

## Questions?

- Open a [GitHub Discussion](https://github.com/TheAgentsRepublic/agents-republic/discussions)
- Reach out on [Twitter](https://twitter.com/TheConstituent_)
- Email: contribute@agentsrepublic.org

## Recognition

Contributors are recognized in:
- The project README
- Release notes
- Community announcements

Thank you for helping build the future of human-AI coexistence!
