# Quick Start - Testing the Refactored Dakora

## Step 1: Test Import Structure

From project root:

```bash
python test_server.py
```

Expected output: All imports successful ✅

## Step 2: Install Server Dependencies

```bash
cd server
pip install -e .
```

## Step 3: Create Test Prompts

```bash
# From project root
mkdir -p prompts
cat > prompts/greeting.yaml << 'EOF'
id: greeting
version: 1.0.0
description: A simple greeting template
template: |
  Hello {{ name }}!
inputs:
  name:
    type: string
    required: true
EOF
```

## Step 4: Start the Server

```bash
cd server
export PROMPT_DIR=../prompts
uvicorn dakora_server.main:app --reload --port 8000
```

Expected: Server starts on http://localhost:8000

## Step 5: Test API Endpoints

In another terminal:

```bash
# Health check
curl http://localhost:8000/api/health

# List templates
curl http://localhost:8000/api/templates

# Get template
curl http://localhost:8000/api/templates/greeting

# Render template
curl -X POST http://localhost:8000/api/templates/greeting/render \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"name": "Alice"}}'
```

## Step 6: Install and Test CLI

```bash
cd cli
pip install -e .
dakora version
```

## Step 7: Install and Test Python SDK

```bash
cd packages/client-python
pip install -e .
```

Test with:

```python
import asyncio
from dakora_client import create_client

async def test():
    async with create_client("http://localhost:8000") as dakora:
        # List templates
        templates = await dakora.prompts.list()
        print(f"Templates: {templates}")

        # Render
        result = await dakora.prompts.render("greeting", {"name": "Alice"})
        print(f"Result: {result.rendered}")

asyncio.run(test())
```

## Step 8: Build Studio UI

```bash
cd studio
npm install
npm run build
```

This creates `studio/dist/` which the server will serve.

## Step 9: Test Full Docker Stack

Create `docker/.env`:

```bash
MODE=local
API_PORT=54321
STUDIO_PORT=3000
```

Start services:

```bash
cd docker
docker compose up
```

Access:
- API: http://localhost:54321/api/health
- Studio: http://localhost:3000

## Common Issues

### Import errors
- Make sure you're running from the correct directory
- Check that `__init__.py` files exist in all packages

### Server won't start
- Check PROMPT_DIR environment variable
- Verify prompts directory exists
- Check port isn't already in use

### Docker issues
- Make sure Docker is running
- Check docker-compose.yml paths are correct
- Verify .env file exists in docker/

## Next Steps After Everything Works

1. Update tests in `server/tests/` to work with new structure
2. Fix any remaining import issues in test files
3. Verify all API endpoints with the Studio UI
4. Test LLM execution with API keys
5. Test Azure registry support

## Need Help?

If something breaks, share the error message and I'll help fix it!