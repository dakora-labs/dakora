# Quick Start - Clerk Authentication

## 🚀 Get Started in 3 Steps

### Step 1: Get Clerk Key

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Create app → API Keys → Copy Publishable Key

### Step 2: Add to Environment

```bash
cd studio
# Edit .env.local
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
```

### Step 3: Run

```bash
npm run dev
```

## 🔑 Where to Find Keys

### Frontend (Publishable Key)

- **Location**: Clerk Dashboard → API Keys → Publishable keys
- **Starts with**: `pk_test_` (development) or `pk_live_` (production)
- **Add to**: `studio/.env.local` as `VITE_CLERK_PUBLISHABLE_KEY`

## ✅ What's Already Done

- ✅ Clerk SDK installed
- ✅ ClerkProvider configured
- ✅ Protected routes set up
- ✅ Auth headers added to API calls
- ✅ UserButton in top bar

## ⏭️ What's Next

1. Add your Clerk Publishable Key to `.env.local`
2. Test frontend authentication
