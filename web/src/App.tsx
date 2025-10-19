import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { PromptEditPage } from './pages/PromptEditPage';
import { NewPromptPage } from './pages/NewPromptPage';

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/prompts" replace />} />
        <Route path="/prompts" element={<DashboardPage />} />
        <Route path="/prompts/new" element={<NewPromptPage />} />
        <Route path="/prompt/edit" element={<PromptEditPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;