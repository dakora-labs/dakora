import { cn } from '@/lib/utils';

import logoMark from '@/assets/logo-mark.svg';
import logoWordmarkDark from '@/assets/logo-wordmark-dark.svg';
import logoWordmarkLight from '@/assets/logo-wordmark-light.svg';

type LogoProps = {
  className?: string;
};

export function DakoraMark({ className }: LogoProps) {
  return (
    <img
      src={logoMark}
      alt="Dakora mark"
      className={cn("h-8 w-8", className)}
    />
  );
}

export function DakoraWordmark({ className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center h-6", className)}>
      <img
        src={logoWordmarkLight}
        alt="Dakora"
        className="block h-full w-auto dark:hidden"
      />
      <img
        src={logoWordmarkDark}
        alt="Dakora"
        className="hidden h-full w-auto dark:block"
      />
    </span>
  );
}
