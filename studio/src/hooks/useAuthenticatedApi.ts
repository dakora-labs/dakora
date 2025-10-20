import { useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { createApiClient } from '../utils/api';

/**
 * Hook that provides an authenticated API client
 * Automatically includes Clerk authentication tokens in all API requests
 */
export function useAuthenticatedApi() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  
  const api = useMemo(() => {
    return createApiClient(getToken);
  }, [getToken]);
  
  return {
    api,
    isLoaded,
    isSignedIn,
  };
}
