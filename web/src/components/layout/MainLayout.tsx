import { ReactNode, useState } from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { StatusBar } from '../StatusBar';

interface MainLayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  sidebar: ReactNode;
  children: ReactNode;
}

export function MainLayout({ activeTab, onTabChange, sidebar, children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="h-screen bg-background flex flex-col">
      <TopBar activeTab={activeTab} onTabChange={onTabChange} />

      <div className="flex-1 flex overflow-hidden relative">
        {sidebarOpen && (
          <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)}>
            {sidebar}
          </Sidebar>
        )}

        {!sidebarOpen && (
          <div className="flex items-start pt-4 pl-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-md hover:bg-muted transition-colors"
              title="Show sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </button>
          </div>
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          {children}
        </div>
      </div>

      <StatusBar />
    </div>
  );
}