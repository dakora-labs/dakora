import { ReactNode, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { FileText, Menu, ChevronLeft, Library, Settings } from 'lucide-react';
import { StatusBar } from '../StatusBar';
import { AppTopBar } from './AppTopBar';
import { cn } from '@/lib/utils';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const { projectSlug: paramProjectSlug } = useParams<{ projectSlug: string }>();
  const { projectSlug: contextProjectSlug } = useAuthenticatedApi();

  // Use projectSlug from route params if available, otherwise from context
  const projectSlug = paramProjectSlug || contextProjectSlug || 'default';

  const isActive = (path: string) => location.pathname.includes(path);

  return (
    <div className="h-screen bg-background flex flex-col">
      <AppTopBar />
      <div className="flex-1 flex overflow-hidden">
      <div
        className={cn(
          "flex flex-col border-r border-border bg-card transition-all duration-200",
          sidebarOpen ? "w-64" : "w-16"
        )}
      >
        <nav className="flex-1 p-3 pt-4">
          <Link
            to={`/project/${projectSlug}/prompts`}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-normal transition-colors mb-1",
              isActive('/prompts')
                ? "bg-muted hover:bg-muted"
                : "hover:bg-muted/50"
            )}
          >
            <FileText className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
            {sidebarOpen && <span>Prompts</span>}
          </Link>
          <Link
            to={`/project/${projectSlug}/library`}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-normal transition-colors mb-1",
              isActive('/library')
                ? "bg-muted hover:bg-muted"
                : "hover:bg-muted/50"
            )}
          >
            <Library className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
            {sidebarOpen && <span>Library</span>}
          </Link>

          {sidebarOpen && (
            <div className="mt-6 mb-2 px-3">
              <div className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">
                Manage
              </div>
            </div>
          )}
          {!sidebarOpen && (
            <div className="mt-6 mb-2 h-px bg-border" />
          )}

          <Link
            to={`/project/${projectSlug}/settings`}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-normal transition-colors mb-1",
              isActive('/settings')
                ? "bg-muted hover:bg-muted"
                : "hover:bg-muted/50"
            )}
          >
            <Settings className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
            {sidebarOpen && <span>Settings</span>}
          </Link>
        </nav>

        <div className="p-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-10 h-10 flex items-center justify-center rounded-lg border border-border bg-background hover:bg-muted transition-colors"
          >
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto">
            {children}
          </div>
          <StatusBar projectSlug={projectSlug} />
        </div>
      </div>
    </div>
  );
}
