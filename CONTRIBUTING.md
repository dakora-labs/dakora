# Contributing to Dakora

Thanks for your interest in contributing to Dakora! This guide will help you get started.

## Getting Help

- **Discord**: [Join our community](https://discord.gg/QSRRcFjzE8)
- **Email**: bogdan@dakora.io
- **Issues**: [GitHub Issues](https://github.com/dakora-labs/dakora/issues)

## Quick Setup

**Prerequisites:**
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) package manager

**Clone and install:**

```bash
git clone https://github.com/dakora-labs/dakora.git
cd dakora
export PATH="$HOME/.local/bin:$PATH"
uv sync
```

## Running the Platform

**Docker (recommended):**

```bash
dakora start
```

Access at:
- Studio: http://localhost:3000
- API: http://localhost:54321

**Development mode (server only):**

```bash
cd server
export PATH="$HOME/.local/bin:$PATH"
uv run uvicorn dakora_server.main:app --reload --port 8000
```

**Studio UI development:**

```bash
cd studio
npm install
npm run dev
```

## Testing

```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH"
uv run python -m pytest

# Run specific categories
uv run python server/tests/test_runner.py unit
uv run python server/tests/test_runner.py integration

# Run specific file
uv run python -m pytest server/tests/test_file.py -v
```

**When contributing:**
- Add tests for new functionality
- Ensure all existing tests pass
- Follow existing test patterns in `server/tests/`

## Submitting Changes

1. **Fork and create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write clear, focused commits
   - Add tests where applicable
   - Update docs if needed

3. **Run tests:**
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   uv run python -m pytest
   ```

4. **Push and create PR:**
   ```bash
   git push -u origin feature/your-feature-name
   ```

5. **Create Pull Request:**
   - Target the `main` branch
   - Fill out the PR template
   - Request review from maintainers
   - All CI checks must pass

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) to keep our git history clean and enable automated changelog generation.

**Format:**
```
<type>(<scope>): <description>
```

**Examples:**
```bash
feat(agents): add LangChain support
fix(client): handle connection timeout errors
docs: update MAF integration guide
chore: bump dependencies to latest versions
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

**Scope** (optional): `agents`, `client`, `server`, `cli`, `studio`

**Breaking changes:**
```bash
feat(client)!: remove deprecated render() method

BREAKING CHANGE: render() is now execute()
```

## What We're Looking For

- Bug fixes and improvements
- Documentation improvements
- New examples and integrations
- Test coverage improvements
- Performance optimizations

## Code Guidelines

- **Python**: Type hints required, async/await for I/O, Pydantic for validation
- **TypeScript**: Use TypeScript for all new frontend code
- **Tests**: Integration tests must be marked with `@pytest.mark.integration`
- **Formatting**: Run `black` before committing

For detailed guidelines, see [CLAUDE.md](CLAUDE.md).

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.