import { useState } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import { TemplatesView } from './views/TemplatesView';
import { ExecuteView } from './views/ExecuteView';

function App() {
  const [activeTab, setActiveTab] = useState('templates');

  const templatesView = TemplatesView();
  const executeView = ExecuteView();

  const view = activeTab === 'execute' ? executeView : templatesView;

  return (
    <MainLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      sidebar={view.sidebar}
    >
      {view.content}
    </MainLayout>
  );
}

export default App;