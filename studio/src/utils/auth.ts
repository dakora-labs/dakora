import { useAuth } from '@clerk/clerk-react';

/**
 * Hook to get the authentication token for API requests
 */
export function useAuthToken() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  
  return {
    getToken,
    isLoaded,
    isSignedIn,
  };
}

/**
 * Get auth headers for fetch requests
 * Call this inside a component that has access to Clerk context
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
