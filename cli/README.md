# Dakora CLI

Minimal CLI for managing the Dakora Platform.

## Installation

```bash
pip install dakora
```

## Commands

```bash
# Initialize new project
dakora init

# Start platform (Docker)
dakora start

# Stop platform
dakora stop

# Link to cloud instance
dakora link https://api.dakora.cloud

# Show version
dakora version
```

## Usage

After installation, the `dakora` command will be available globally.

For local development with Docker:

1. `dakora init` - Creates `prompts/` directory and `docker/` config
2. `dakora start` - Launches API server, Studio UI, PostgreSQL, and Redis
3. Access API at http://localhost:54321
4. Access Studio at http://localhost:3000