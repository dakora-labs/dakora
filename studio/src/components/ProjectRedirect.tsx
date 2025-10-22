import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';

/**
 * Redirects authenticated users to their default project.
 * Fetches user context from /api/me/context and redirects to /project/{project_slug}/prompts
 */
export function ProjectRedirect() {
  const { api, isLoaded } = useAuthenticatedApi();
  const [projectSlug, setProjectSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;

    const fetchUserContext = async () => {
      try {
        const context = await api.getUserContext();
        setProjectSlug(context.project_slug);
      } catch (err) {
        console.error('Failed to fetch user context:', err);
        setError('Failed to load project');
      }
    };

    fetchUserContext();
  }, [api, isLoaded]);

  // Show loading state while auth loads
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  // Show loading while fetching project
  if (!projectSlug) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  // Redirect to project-scoped route
  return <Navigate to={`/project/${projectSlug}/prompts`} replace />;
}