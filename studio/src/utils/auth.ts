import { useAuth } from '@clerk/clerk-react';
import useNoopAuth from './noopAuth';

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';

// Provide a wrapper that selects the real Clerk hook or the noop hook.
export function useAuthToken() {
  return AUTH_REQUIRED ? useAuth() : useNoopAuth();
}

/**
 * Get auth headers for fetch requests
 */
export async function getAuthHeaders(getToken: () => Promise<string | null>): Promise<HeadersInit> {
  const token = await getToken();

  if (token) {
    return {
      'Authorization': `Bearer ${token}`,
    };
  }

  return {};
}
