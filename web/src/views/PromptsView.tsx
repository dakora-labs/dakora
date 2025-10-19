import { useState } from 'react';
import { PromptList } from '../components/PromptList';
import { PromptEditor } from '../components/PromptEditor';

export function PromptsView() {
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);

  return {
    sidebar: (
      <PromptList
        selectedPrompt={selectedPrompt}
        onSelectPrompt={setSelectedPrompt}
      />
    ),
    content: <PromptEditor promptId={selectedPrompt} />,
  };
}