import { ReactNode, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FileText, Menu, ChevronLeft } from 'lucide-react';
import { StatusBar } from '../StatusBar';
import { AppTopBar } from './AppTopBar';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

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
            to="/prompts"
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
          <StatusBar />
        </div>
      </div>
    </div>
  );
}
