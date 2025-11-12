import { ReactNode, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Activity, FileText, Menu, ChevronLeft, Library, Settings, LayoutDashboard, Shield } from 'lucide-react';
import { StatusBar } from '../StatusBar';
import { AppTopBar } from './AppTopBar';
import { cn } from '@/lib/utils';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useUser } from '@clerk/clerk-react';

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const { projectSlug: paramProjectSlug } = useParams<{ projectSlug: string }>();
  const { projectSlug: contextProjectSlug, userContext } = useAuthenticatedApi();
  const { user } = useUser();

  // Use projectSlug from route params if available, otherwise from context
  const projectSlug = paramProjectSlug || contextProjectSlug || 'default';

  // Check if user is platform admin
  // Priority 1: Check Clerk public_metadata (most reliable for UI)
  // Priority 2: Check backend user context (auth_ctx.is_platform_admin)
  const isPlatformAdmin = AUTH_REQUIRED && (
    user?.publicMetadata?.platform_role === 'admin' ||
    userContext?.is_platform_admin === true
  );

  const isActive = (path: string) => location.pathname.includes(path);

  const navigationSections = [
    {
      key: 'main',
      title: null as string | null,
      items: [
        {
          label: 'Dashboard',
          icon: LayoutDashboard,
          to: `/project/${projectSlug}/dashboard`,
          match: '/dashboard',
        },
        {
          label: 'Prompts',
          icon: FileText,
          to: `/project/${projectSlug}/prompts`,
          match: '/prompts',
        },
        {
          label: 'Library',
          icon: Library,
          to: `/project/${projectSlug}/library`,
          match: '/library',
        },
      ],
    },
    {
      key: 'observability',
      title: 'Observability',
      items: [
        {
          label: 'Executions',
          icon: Activity,
          to: `/project/${projectSlug}/executions`,
          match: '/executions',
        },
      ],
    },
    {
      key: 'manage',
      title: 'Manage',
      items: [
        {
          label: 'Settings',
          icon: Settings,
          to: `/project/${projectSlug}/settings`,
          match: '/settings',
        },
      ],
    },
  ];

  // Add admin section if user is platform admin
  if (isPlatformAdmin) {
    navigationSections.push({
      key: 'admin',
      title: 'Admin',
      items: [
        {
          label: 'Invitations',
          icon: Shield,
          to: '/admin/invitations',
          match: '/admin/invitations',
        },
      ],
    });
  }

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
          {navigationSections.map((section, index) => (
            <div key={section.key} className={cn(index > 0 && "mt-6")}>
              {section.title && (
                sidebarOpen ? (
                  <div className="mb-2 px-3">
                    <div className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">
                      {section.title}
                    </div>
                  </div>
                ) : (
                  <div className="mb-2 h-px bg-border" />
                )
              )}

              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-normal transition-colors mb-1",
                      isActive(item.match)
                        ? "bg-muted hover:bg-muted"
                        : "hover:bg-muted/50"
                    )}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                    {sidebarOpen && <span>{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
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
