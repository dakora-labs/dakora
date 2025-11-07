import { useState, useEffect, ReactNode } from 'react';
import { useParams } from 'react-router-dom';
import { OnboardingTutorial } from './OnboardingTutorial';

interface OnboardingWrapperProps {
  children: ReactNode;
}

export function OnboardingWrapper({ children }: OnboardingWrapperProps) {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const { projectSlug } = useParams<{ projectSlug: string }>();

  useEffect(() => {
    const hasCompletedOnboarding = localStorage.getItem('dakora_onboarding_completed');

    if (!hasCompletedOnboarding && projectSlug) {
      const timer = setTimeout(() => {
        setShowOnboarding(true);
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [projectSlug]);

  return (
    <>
      {children}
      <OnboardingTutorial
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        projectSlug={projectSlug || 'default'}
      />
    </>
  );
}