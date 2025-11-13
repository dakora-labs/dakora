import { UserButton } from '@clerk/clerk-react';

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';

export function AppTopBar() {
  return (
    <div className="h-12 border-b border-border bg-card flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <img 
            src="/logo-light.svg" 
            alt="Dakora Logo" 
            className="h-8 w-auto"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
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
