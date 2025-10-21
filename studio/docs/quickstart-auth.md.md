# Quick Start - Authentication

This quick reference covers setting up Clerk authentication for Dakora. For comprehensive documentation, see the [Authentication Guide](/guides/authentication).

## 🚀 Frontend Setup (Clerk JWT) - 3 Steps

### Step 1: Get Clerk Publishable Key

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Navigate to **API Keys** section
3. Copy your **Publishable Key** (starts with `pk_test_` or `pk_live_`)

### Step 2: Configure Environment

Create or update `studio/.env.local`:

```bash
# Enable authentication
VITE_AUTH_REQUIRED=true

# Add your Clerk key
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE

# Backend API URL
VITE_API_URL=http://localhost:8000
```

### Step 3: Start Frontend

```bash
cd studio
npm install
npm run dev
```

The app will automatically:

- Show Clerk sign-in when needed
- Add authentication headers to API calls
- Handle token refresh automatically

## � Backend Setup (Optional)

If you want to enable authentication on the backend API:

```bash
# In .env or environment variables
AUTH_ENABLED=true
CLERK_JWT_ISSUER=https://your-domain.clerk.accounts.prod.liveblocks.io
CLERK_JWKS_URL=https://your-domain.clerk.accounts.prod.liveblocks.io/.well-known/jwks.json
DATABASE_URL=postgresql://user:password@localhost:5432/dakora
```

Get these values from your [Clerk Dashboard](https://dashboard.clerk.com) → API Keys

Then restart backend:

```bash
cd server
uvicorn dakora_server.main:app --reload --port 8000
```

## 🔑 Environment Variables Reference

### Frontend (studio/.env.local)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `VITE_AUTH_REQUIRED` | Yes | `true` or `false` | Set to `false` to disable auth |
| `VITE_CLERK_PUBLISHABLE_KEY` | If auth enabled | `pk_test_xxx` | Get from Clerk Dashboard |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API URL |

### Backend (.env)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `AUTH_ENABLED` | Yes | `true` or `false` | Set to `false` for dev mode |
| `CLERK_JWT_ISSUER` | If auth enabled | `https://...clerk.accounts.prod.liveblocks.io` | Get from Clerk Dashboard |
| `CLERK_JWKS_URL` | If auth enabled | `https://.../.well-known/jwks.json` | Get from Clerk Dashboard |
| `DATABASE_URL` | If auth enabled | `postgresql://...` | For storing authenticated data |

## ✅ What's Already Done

- ✅ Clerk SDK installed and configured
- ✅ ClerkProvider integrated with fallback support
- ✅ Protected routes set up with `SignedIn`/`SignedOut`
- ✅ Auth headers automatically added to API calls
- ✅ UserButton component in navigation
- ✅ 30 comprehensive integration tests passing
- ✅ Multi-tenant scoping implemented
- ✅ Dual-mode support (auth and no-auth)

## 📋 Authentication Modes

### Development Mode (No Auth)

Set in both frontend and backend `.env`:

```bash
VITE_AUTH_REQUIRED=false
AUTH_ENABLED=false
```

- All endpoints are public
- No Clerk setup needed
- Great for local development

### Production Mode (Auth Enabled)

Set in both frontend and backend `.env`:

```bash
VITE_AUTH_REQUIRED=true
AUTH_ENABLED=true
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY
CLERK_JWT_ISSUER=https://your-domain.clerk.accounts.prod.liveblocks.io
CLERK_JWKS_URL=https://your-domain.clerk.accounts.prod.liveblocks.io/.well-known/jwks.json
```

- Clerk authentication required
- API Key authentication supported
- Multi-tenant data isolation
- Returns 401 for unauthorized requests

## 🔑 API Key Authentication

API keys allow programmatic access without browser login:

```bash
# Use API key in requests
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/templates
```

API key generation and management endpoints are in development. See [Authentication Guide](/guides/authentication#api-key-authentication) for details.

## ⏭️ Next Steps

1. **Frontend Only**: Add `VITE_CLERK_PUBLISHABLE_KEY` and run `npm run dev`
2. **Full Auth**: Also configure backend variables and database
3. **Read Docs**: See [Authentication Guide](/guides/authentication) for complete details
4. **Test**: Use cURL or API client to verify auth works

## 🐛 Troubleshooting

**"Authenticate" button but no sign-in modal?**

- Verify `VITE_CLERK_PUBLISHABLE_KEY` is set correctly
- Check Clerk Dashboard for correct key
- Restart dev server after changing `.env`

**API returns 401?**

- Backend might not have auth enabled
- Check `AUTH_ENABLED` in backend `.env`
- Verify database is configured if auth enabled

**Token expired?**

- Clerk SDK handles token refresh automatically
- If issues persist, check browser console for errors

See [Authentication Guide](/guides/authentication#troubleshooting) for more help.
