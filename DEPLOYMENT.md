# Deployment Guide

## Demo Mode Deployment

The Dakora playground can be deployed in demo mode with isolated user sessions.

### Railway Deployment (Easiest)

1. **Fork or push this repo to GitHub**

2. **Create Railway account**: Visit [railway.app](https://railway.app)

3. **Deploy from GitHub**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose this repository
   - Railway will auto-detect the Dockerfile

4. **Configure**:
   - No environment variables needed for demo mode
   - Railway will assign a public URL automatically

5. **Custom Domain** (Optional):
   - In Railway project settings → Networking
   - Add custom domain: `playground.dakora.io`
   - Follow DNS configuration instructions

6. **Done!** Visit your Railway URL or custom domain

### Alternative: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (from project root)
fly launch --dockerfile Dockerfile

# Deploy
fly deploy

# Set custom domain
fly certs add playground.dakora.io
```

### Alternative: Render.com

1. Create account at render.com
2. New → Web Service
3. Connect GitHub repository
4. Configure:
   - **Environment**: Docker
   - **Dockerfile path**: `Dockerfile`
   - **Port**: 8000
5. Deploy

### Local Docker Testing

```bash
# Build
docker build -t dakora-playground .

# Run
docker run -p 8000:8000 dakora-playground

# Visit http://localhost:8000
```

## Architecture

Demo mode features:
- Session-based isolation (cookie-based)
- Ephemeral storage in `/tmp/dakora-demo/{session_id}`
- Pre-populated example templates
- No persistent data across sessions
- 1-hour session timeout