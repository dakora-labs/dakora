import { FileText, Rocket } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TopBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'templates', label: 'Templates', icon: FileText },
  { id: 'execute', label: 'Execute', icon: Rocket },
];

export function TopBar({ activeTab, onTabChange }: TopBarProps) {
  return (
    <div className="border-b border-border bg-card">
      <div className="flex items-center justify-between px-4 md:px-6 h-14">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">D</span>
            </div>
            <h1 className="text-lg font-semibold hidden sm:block">Dakora</h1>
          </div>

          <nav className="flex items-center gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    activeTab === tab.id
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}