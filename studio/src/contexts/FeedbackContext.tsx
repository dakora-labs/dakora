import { createContext, useContext, ReactNode } from 'react';
import { useFeedback } from '@/hooks/useFeedback';
import { FeedbackDialog } from '@/components/FeedbackDialog';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useToast } from '@/hooks/use-toast';

interface FeedbackContextType {
  openFeedbackDialog: () => void;
  trackPromptCreated: () => void;
  trackExecutionCompleted: () => void;
}

const FeedbackContext = createContext<FeedbackContextType | undefined>(undefined);

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { api } = useAuthenticatedApi();
  const { toast } = useToast();
  const {
    showDialog,
    setShowDialog,
    trackPromptCreated,
    trackExecutionCompleted,
    openFeedbackDialog,
    handleFeedbackSubmitted,
  } = useFeedback();

  const handleSubmit = async (rating: number, feedback: string, dontShowAgain: boolean) => {
    try {
      await api.submitFeedback({
        rating,
        feedback: feedback || undefined,
      });

      handleFeedbackSubmitted(dontShowAgain);

      toast({
        title: 'Thank you for your feedback!',
        description: 'We appreciate you taking the time to help us improve Dakora.',
      });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      toast({
        title: 'Failed to submit feedback',
        description: 'Please try again later.',
        variant: 'destructive',
      });
      throw error;
    }
  };

  return (
    <FeedbackContext.Provider
      value={{
        openFeedbackDialog,
        trackPromptCreated,
        trackExecutionCompleted,
      }}
    >
      {children}
      <FeedbackDialog
        open={showDialog}
        onOpenChange={setShowDialog}
        onSubmit={handleSubmit}
      />
    </FeedbackContext.Provider>
  );
}

export function useFeedbackContext() {
  const context = useContext(FeedbackContext);
  if (context === undefined) {
    throw new Error('useFeedbackContext must be used within a FeedbackProvider');
  }
  return context;
}