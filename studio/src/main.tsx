import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import * as Sentry from "@sentry/react";
import App from './App.tsx';
import './index.css';
import { hideClerkBadge } from './utils/hideClerkBadge';
import { ClerkProvider } from '@clerk/clerk-react';

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';

// Initialize Sentry only in cloud mode (when auth is required)
if (AUTH_REQUIRED) {
  const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;

  if (SENTRY_DSN) {
    Sentry.init({
      dsn: SENTRY_DSN,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
        Sentry.feedbackIntegration({
          colorScheme: "system",
          // Don't auto-inject - we'll use our custom Report Bug button
          autoInject: false,
        }),
      ],
      // Performance Monitoring
      tracesSampleRate: 1.0, // Capture 100% of transactions for performance monitoring
      // Distributed Tracing - connects frontend traces to backend API traces (cloud only)
      tracePropagationTargets: [
        /^https:\/\/[^/]*\.dakora\.ai\//,
        /^https:\/\/api\.dakora\.ai\//,
      ],
      // Session Replay
      replaysSessionSampleRate: 0.1, // 10% of sessions
      replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors
      // Send default PII (IP address, user agent)
      sendDefaultPii: true,
      environment: import.meta.env.MODE,
    });
  }
}

if (AUTH_REQUIRED) {
  const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

  if (!PUBLISHABLE_KEY) {
    throw new Error("Missing Clerk Publishable Key");
  }

  // Hide Clerk badge for cleaner development UI
  hideClerkBadge();

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ClerkProvider 
        publishableKey={PUBLISHABLE_KEY}
        signInFallbackRedirectUrl="/"
        signUpFallbackRedirectUrl="/"
      >
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ClerkProvider>
    </React.StrictMode>,
  );
} else {
  // Auth disabled: render app without Clerk
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );
}