# Sentry Setup for Render Deployment

This guide explains how to set up Sentry error tracking and source map uploads for the Studio when deploying to Render.

## Prerequisites

1. A Sentry account with a project created
2. Your Sentry DSN from the project settings
3. A Sentry auth token for source map uploads

## Getting Your Sentry Auth Token

1. Go to https://sentry.io/settings/account/api/auth-tokens/
2. Click "Create New Token"
3. Give it a name like "Render Studio Sourcemaps"
4. Select the following scopes:
   - `project:read`
   - `project:releases`
   - `project:write`
5. Click "Create Token"
6. Copy the token (you won't be able to see it again!)

## Configuring Render Environment Variables

In your Render dashboard, add these **Secret Files** or **Environment Variables**:

### Required for Sentry Error Tracking

```bash
VITE_SENTRY_DSN=https://f99d68a218d3bf713f7ec56bcab55aa0@o4510295298015232.ingest.de.sentry.io/4510295303454800
```

### Required for Source Map Uploads

```bash
SENTRY_AUTH_TOKEN=your_sentry_auth_token_here
SENTRY_ORG=dakora
SENTRY_PROJECT=javascript-react
```

## How It Works

1. **During Build**:
   - Vite builds the Studio with source maps enabled
   - The Sentry Vite plugin automatically uploads source maps to Sentry
   - Source map files are deleted from the final build for security

2. **At Runtime**:
   - Sentry SDK captures errors and performance data
   - Only runs when `VITE_AUTH_REQUIRED=true` (cloud mode)
   - Self-hosted deployments won't send data to Sentry

3. **Error Reporting**:
   - Full stack traces with original source code (thanks to source maps)
   - Session replay for errors
   - Performance monitoring
   - User context and breadcrumbs

## Testing Locally

To test Sentry integration locally:

1. Create a `.env.local` file:
   ```bash
   VITE_AUTH_REQUIRED=true
   VITE_CLERK_PUBLISHABLE_KEY=your_clerk_key
   VITE_SENTRY_DSN=your_sentry_dsn
   ```

2. Run the dev server:
   ```bash
   npm run dev
   ```

3. Source maps won't be uploaded in dev mode (only in production builds)

## Testing Source Map Upload

To test source map uploads locally:

```bash
# Set environment variables
export SENTRY_AUTH_TOKEN=your_token
export SENTRY_ORG=dakora
export SENTRY_PROJECT=javascript-react
export VITE_SENTRY_DSN=your_dsn

# Run production build
npm run build
```

You should see:
```
✓ Sentry source maps will be uploaded to dakora/javascript-react
```

## Troubleshooting

### Source maps not uploading

- Check that `SENTRY_AUTH_TOKEN` is set correctly
- Verify the token has the required scopes
- Check build logs for Sentry plugin errors

### Errors not showing in Sentry

- Verify `VITE_SENTRY_DSN` is set in Render
- Ensure `VITE_AUTH_REQUIRED=true` in production
- Check browser console for Sentry initialization messages

### Stack traces not symbolicated

- Verify source maps were uploaded (check Sentry releases)
- Ensure the release version matches between upload and runtime
- Check that source maps weren't deleted before upload

## Security Notes

- Source map files (`.map`) are deleted after upload and not served to users
- Source maps are only uploaded to Sentry, not included in the deployed bundle
- Auth tokens should be stored as Render secrets, never committed to git