import { sentryVitePlugin } from "@sentry/vite-plugin";

/**
 * Sentry source map upload configuration
 *
 * This config is used during production builds to automatically upload
 * source maps to Sentry for better error tracking.
 *
 * Required environment variables:
 * - SENTRY_AUTH_TOKEN: Authentication token from Sentry
 * - SENTRY_ORG: Organization slug (dakora)
 * - SENTRY_PROJECT: Project slug (javascript-react)
 */
export function getSentryPlugin() {
  const authToken = process.env.SENTRY_AUTH_TOKEN;
  const org = process.env.SENTRY_ORG || "dakora";
  const project = process.env.SENTRY_PROJECT || "javascript-react";

  // Only upload source maps if auth token is provided
  if (!authToken) {
    console.log("⚠️  SENTRY_AUTH_TOKEN not found - skipping source map upload");
    return null;
  }

  console.log(`✓ Sentry source maps will be uploaded to ${org}/${project}`);

  return sentryVitePlugin({
    org,
    project,
    authToken,

    // Upload source maps during build
    sourcemaps: {
      assets: "./dist/**",
      filesToDeleteAfterUpload: "./dist/**/*.map", // Delete source maps after upload for security
    },

    // Disable telemetry for CI/CD environments
    telemetry: false,
  });
}