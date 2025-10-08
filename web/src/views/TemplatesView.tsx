import { useState } from 'react';
import { TemplateList } from '../components/TemplateList';
import { TemplateEditor } from '../components/TemplateEditor';

export function TemplatesView() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  return {
    sidebar: (
      <TemplateList
        selectedTemplate={selectedTemplate}
        onSelectTemplate={setSelectedTemplate}
      />
    ),
    content: <TemplateEditor templateId={selectedTemplate} />,
  };
}