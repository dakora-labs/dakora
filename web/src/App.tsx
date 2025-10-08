import { useState } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import { TemplatesView } from './views/TemplatesView';

function App() {
  const [activeTab, setActiveTab] = useState('templates');

  const renderView = () => {
    switch (activeTab) {
      case 'templates':
        return TemplatesView();
      default:
        return TemplatesView();
    }
  };

  const view = renderView();

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