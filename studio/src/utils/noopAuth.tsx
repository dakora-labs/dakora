import { useMemo } from 'react';

/**
 * Minimal noop auth implementation used when auth is disabled.
 * Mirrors the shape returned by @clerk/clerk-react's useAuth where needed.
 */
export function useNoopAuth() {
  const getToken = useMemo(() => async () => null, []);
  const isLoaded = true;
  const isSignedIn = false;

  return {
    getToken,
    isLoaded,
    isSignedIn,
  } as const;
}

export default useNoopAuth;
