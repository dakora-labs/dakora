import { ReactNode } from 'react';
import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export function Sidebar({ isOpen, onToggle, children }: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onToggle}
        />
      )}

      <div
        className={cn(
          "fixed md:relative inset-y-0 left-0 z-50 md:z-0",
          "transform transition-transform duration-200 ease-in-out",
          "w-80 bg-card border-r border-border",
          "flex flex-col",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="flex items-center justify-end p-2 border-b border-border">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="h-8 w-8 hover:bg-muted"
            title="Hide sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>

        {children}
      </div>
    </>
  );
}