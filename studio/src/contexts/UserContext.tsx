import { createContext, useContext, useState, useEffect, useCallback, ReactNode, useMemo } from 'react';
import { createApiClient, type UserContext } from '../utils/api';
import { useAuthToken } from '@/utils/auth';

interface UserContextState {
  userContext: UserContext | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const UserContextContext = createContext<UserContextState | undefined>(undefined);

interface UserContextProviderProps {
  children: ReactNode;
}

export function UserContextProvider({ children }: UserContextProviderProps) {
  const { getToken, isLoaded } = useAuthToken();
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const api = useMemo(() => createApiClient(getToken), [getToken]);

  const fetchContext = useCallback(async () => {
    if (!isLoaded) return;

    try {
      setLoading(true);
      setError(null);
      const context = await api.getUserContext();
      setUserContext(context);
    } catch (err) {
      console.error('Failed to fetch user context:', err);
      setError(err instanceof Error ? err.message : 'Failed to load context');
      setUserContext(null);
    } finally {
      setLoading(false);
    }
  }, [api, isLoaded]);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  const value = useMemo(
    () => ({
      userContext,
      loading,
      error,
      refetch: fetchContext,
    }),
    [userContext, loading, error, fetchContext]
  );

  return (
    <UserContextContext.Provider value={value}>
      {children}
    </UserContextContext.Provider>
  );
}

export function useUserContext() {
  const context = useContext(UserContextContext);
  if (!context) {
    throw new Error('useUserContext must be used within UserContextProvider');
  }
  return context;
}
