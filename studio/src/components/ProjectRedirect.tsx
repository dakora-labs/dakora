import { Navigate } from 'react-router-dom';
import { useUserContext } from '@/contexts/UserContext';

/**
 * Redirects authenticated users to their default project.
 * Uses UserContext to get project_slug and redirects to /project/{project_slug}/prompts
 */
export function ProjectRedirect() {
  const { userContext, loading, error } = useUserContext();

  // Show loading state while fetching context
  if (loading) {
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
        <p className="text-destructive">Failed to load project</p>
      </div>
    );
  }

  // Show loading while fetching project
  if (!userContext?.project_slug) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  // Redirect to project-scoped route
  return <Navigate to={`/project/${userContext.project_slug}/prompts`} replace />;
}