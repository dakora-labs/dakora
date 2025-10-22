import { useMemo, useState, useEffect } from 'react';
import { createApiClient, type UserContext } from '../utils/api';
import { useAuthToken } from '@/utils/auth';

/**
 * Hook that provides an authenticated API client with project context
 * Automatically includes auth tokens when available; falls back to unauthenticated client when auth disabled
 */
export function useAuthenticatedApi() {
  const { getToken, isLoaded, isSignedIn } = useAuthToken();
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [contextLoading, setContextLoading] = useState(true);

  const api = useMemo(() => {
    // If no getToken is present (noop), createApiClient will behave unauthenticated
    return createApiClient(getToken);
  }, [getToken]);

  useEffect(() => {
    if (!isLoaded) return;

    const fetchContext = async () => {
      try {
        const context = await api.getUserContext();
        setUserContext(context);
      } catch (err) {
        console.error('Failed to fetch user context:', err);
        setUserContext(null);
      } finally {
        setContextLoading(false);
      }
    };

    fetchContext();
  }, [api, isLoaded]);

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
