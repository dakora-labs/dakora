import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { PromptEditPage } from './pages/PromptEditPage';
import { NewPromptPage } from './pages/NewPromptPage';

function App() {
  return (
    <>
      <SignedIn>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/prompts" replace />} />
            <Route path="/prompts" element={<DashboardPage />} />
            <Route path="/prompts/new" element={<NewPromptPage />} />
            <Route path="/prompt/edit" element={<PromptEditPage />} />
          </Routes>
        </MainLayout>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}

export default App;