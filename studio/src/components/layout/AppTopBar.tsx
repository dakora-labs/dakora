import { Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserButton } from '@clerk/clerk-react';

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';

export function AppTopBar() {
  return (
    <div className="h-12 border-b border-border bg-card flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-xs">D</span>
          </div>
          <span className="text-sm font-medium">Dakora</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="h-8 px-2">
          <Settings className="w-4 h-4" />
        </Button>
        {AUTH_REQUIRED && (
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-8 h-8"
              }
            }}
          />
        )}
      </div>
    </div>
  );
}
