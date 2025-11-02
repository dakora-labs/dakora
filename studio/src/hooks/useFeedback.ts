import { useState, useEffect, useCallback } from 'react';

interface FeedbackState {
  promptsCreated: number;
  executionsCompleted: number;
  lastFeedbackShown: number | null;
  lastFeedbackSubmitted: number | null;
  feedbackDisabled: boolean;
  triggerHistory: {
    promptCreation?: number;
    execution?: number;
  };
}

const STORAGE_KEY = 'dakora_feedback_state';
const DAYS_BETWEEN_PROMPTS = 7;
const PROMPT_THRESHOLD = 2;
const EXECUTION_THRESHOLD = 5;

function getStoredState(): FeedbackState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to parse feedback state:', error);
  }

  return {
    promptsCreated: 0,
    executionsCompleted: 0,
    lastFeedbackShown: null,
    lastFeedbackSubmitted: null,
    feedbackDisabled: false,
    triggerHistory: {},
  };
}

function saveState(state: FeedbackState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save feedback state:', error);
  }
}

function shouldShowFeedback(state: FeedbackState): boolean {
  if (state.feedbackDisabled) {
    return false;
  }

  const now = Date.now();
  const daysSinceLastShown = state.lastFeedbackShown
    ? (now - state.lastFeedbackShown) / (1000 * 60 * 60 * 24)
    : Infinity;

  if (daysSinceLastShown < DAYS_BETWEEN_PROMPTS) {
    return false;
  }

  return true;
}

export function useFeedback() {
  const [state, setState] = useState<FeedbackState>(getStoredState);
  const [showDialog, setShowDialog] = useState(false);

  useEffect(() => {
    saveState(state);
  }, [state]);

  const trackPromptCreated = useCallback(() => {
    setState((prev) => {
      const newCount = prev.promptsCreated + 1;
      const newState = {
        ...prev,
        promptsCreated: newCount,
      };

      if (newCount >= PROMPT_THRESHOLD && shouldShowFeedback(newState)) {
        const now = Date.now();
        const daysSinceLastTrigger = prev.triggerHistory.promptCreation
          ? (now - prev.triggerHistory.promptCreation) / (1000 * 60 * 60 * 24)
          : Infinity;

        if (daysSinceLastTrigger >= DAYS_BETWEEN_PROMPTS) {
          setShowDialog(true);
          return {
            ...newState,
            lastFeedbackShown: now,
            triggerHistory: {
              ...newState.triggerHistory,
              promptCreation: now,
            },
          };
        }
      }

      return newState;
    });
  }, []);

  const trackExecutionCompleted = useCallback(() => {
    setState((prev) => {
      const newCount = prev.executionsCompleted + 1;
      const newState = {
        ...prev,
        executionsCompleted: newCount,
      };

      if (newCount >= EXECUTION_THRESHOLD && shouldShowFeedback(newState)) {
        const now = Date.now();
        const daysSinceLastTrigger = prev.triggerHistory.execution
          ? (now - prev.triggerHistory.execution) / (1000 * 60 * 60 * 24)
          : Infinity;

        if (daysSinceLastTrigger >= DAYS_BETWEEN_PROMPTS) {
          setShowDialog(true);
          return {
            ...newState,
            lastFeedbackShown: now,
            triggerHistory: {
              ...newState.triggerHistory,
              execution: now,
            },
          };
        }
      }

      return newState;
    });
  }, []);

  const openFeedbackDialog = useCallback(() => {
    setShowDialog(true);
    setState((prev) => ({
      ...prev,
      lastFeedbackShown: Date.now(),
    }));
  }, []);

  const handleFeedbackSubmitted = useCallback((dontShowAgain: boolean) => {
    setState((prev) => ({
      ...prev,
      lastFeedbackSubmitted: Date.now(),
      feedbackDisabled: dontShowAgain,
    }));
  }, []);

  const resetFeedbackState = useCallback(() => {
    const initialState: FeedbackState = {
      promptsCreated: 0,
      executionsCompleted: 0,
      lastFeedbackShown: null,
      lastFeedbackSubmitted: null,
      feedbackDisabled: false,
      triggerHistory: {},
    };
    setState(initialState);
    saveState(initialState);
  }, []);

  return {
    showDialog,
    setShowDialog,
    trackPromptCreated,
    trackExecutionCompleted,
    openFeedbackDialog,
    handleFeedbackSubmitted,
    resetFeedbackState,
    state,
  };
}