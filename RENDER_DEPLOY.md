# Render Deployment Guide

This guide walks you through deploying Dakora to Render with Azure Blob Storage for prompt templates.

## Prerequisites

1. **Render Account** - Sign up at [render.com](https://render.com)
2. **Azure Storage Account** - Create a storage account and container for prompts
3. **Supabase Database** - Get your PostgreSQL connection string
4. **LLM API Keys** - OpenAI, Anthropic, etc.
5. **(Optional) Upstash Redis** - Free tier at [upstash.com](https://upstash.com)

## Step 1: Prepare Azure Blob Storage

1. Create an Azure Storage Account
2. Create a container named `prompts` (or your preferred name)
3. Get your connection string from Azure Portal:
   - Storage Account → Access keys → Connection string

## Step 2: Deploy to Render

### Option A: Using Blueprint (Recommended)

1. Push your code to GitHub (including `render.yaml`)
2. In Render Dashboard:
   - Click **New** → **Blueprint**
   - Connect your GitHub repository
   - Select `render.yaml`
   - Click **Apply**

### Option B: Manual Setup

Create two services manually:

**API Service:**
- Runtime: Docker
- Dockerfile Path: `./server/Dockerfile`
- Docker Context: `./server`
- Auto-deploy: Off (manual only)

**Studio Service:**
- Runtime: Docker
- Dockerfile Path: `./studio/Dockerfile`
- Docker Context: `./studio`
- Auto-deploy: Off (manual only)

## Step 3: Configure Environment Variables

### For `dakora-api` service:

```bash
# Database (Supabase)
DATABASE_URL=postgresql://postgres:[password]@[host]:[port]/postgres

# Azure Blob Storage (required)
AZURE_STORAGE_CONTAINER=prompts
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Redis (Upstash)
REDIS_URL=rediss://default:[password]@[host]:[port]

# Mode
MODE=production
```

### For `dakora-studio` service:

```bash
# Set this AFTER the API service is deployed
VITE_API_URL=https://dakora-api.onrender.com
```

## Step 4: Deploy

1. In Render Dashboard, go to **dakora-api** service
2. Click **Manual Deploy** → **Deploy latest commit**
3. Wait for deployment to complete (~3-5 minutes)
4. Copy the API URL (e.g., `https://dakora-api.onrender.com`)
5. Go to **dakora-studio** service
6. Update `VITE_API_URL` with the API URL from step 4
7. Click **Manual Deploy** → **Deploy latest commit**

## Step 5: Upload Prompt Templates

Upload your YAML template files to Azure Blob Storage:

```bash
# Using Azure CLI
az storage blob upload-batch \
  --account-name <your-account> \
  --destination prompts \
  --source ./prompts \
  --pattern "*.yaml"

# Or use Azure Portal / Storage Explorer
```

## Step 6: Test Deployment

1. Visit your Studio URL (e.g., `https://dakora-studio.onrender.com`)
2. You should see your prompt templates loaded from Azure
3. Test rendering and execution

## Cold Starts

⚠️ **Free tier services spin down after 15 minutes of inactivity.**
- First request after spin-down takes ~30 seconds
- Subsequent requests are instant
- Upgrade to paid plan to eliminate cold starts

## Troubleshooting

### Service won't start
- Check environment variables are set correctly
- View logs in Render Dashboard

### Templates not loading
- Verify Azure connection string is correct
- Check container name matches `AZURE_STORAGE_CONTAINER`
- Ensure YAML files exist in Azure container

### API connection fails
- Verify `VITE_API_URL` in Studio points to API URL
- Check CORS settings if needed

## Local Development

Local Docker Compose continues to work as before:

```bash
dakora start
```

Local setup uses local filesystem for prompts (no Azure needed).

## Cost Estimate

- **Render**: $0/month (free tier with cold starts)
- **Supabase**: $0/month (free tier)
- **Azure Blob Storage**: ~$0.01-0.10/month (minimal storage + requests)
- **Upstash Redis**: $0/month (free tier, optional)

**Total: Essentially free for low traffic**