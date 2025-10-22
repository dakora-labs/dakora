import { useMemo } from 'react';
import { createApiClient } from '../utils/api';
import { useAuthToken } from '@/utils/auth';
import { useUserContext } from '@/contexts/UserContext';

/**
 * Hook that provides an authenticated API client with project context
 * Automatically includes auth tokens when available; falls back to unauthenticated client when auth disabled
 */
export function useAuthenticatedApi() {
  const { getToken, isLoaded, isSignedIn } = useAuthToken();
  const { userContext, loading: contextLoading } = useUserContext();

  const api = useMemo(() => {
    // If no getToken is present (noop), createApiClient will behave unauthenticated
    return createApiClient(getToken);
  }, [getToken]);

  return {
    api,
    isLoaded,
    isSignedIn,
    projectId: userContext?.project_id,
    projectSlug: userContext?.project_slug,
    userContext,
    contextLoading,
  };
}
