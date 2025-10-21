import { useMemo } from 'react';
import { createApiClient } from '../utils/api';
import { useAuthToken } from '@/utils/auth';

/**
 * Hook that provides an authenticated API client
 * Automatically includes auth tokens when available; falls back to unauthenticated client when auth disabled
 */
export function useAuthenticatedApi() {
  const { getToken, isLoaded, isSignedIn } = useAuthToken();

  const api = useMemo(() => {
    // If no getToken is present (noop), createApiClient will behave unauthenticated
    return createApiClient(getToken);
  }, [getToken]);

  return {
    api,
    isLoaded,
    isSignedIn,
  };
}
