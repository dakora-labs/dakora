import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { PromptEditPage } from './pages/PromptEditPage';
import { NewPromptPage } from './pages/NewPromptPage';
import { PromptLibraryPage } from './pages/PromptLibraryPage';
import { NewPromptPartPage } from './pages/NewPromptPartPage';
import { PromptPartPage } from './pages/PromptPartPage';
import { FEATURES } from './config/features';

function App() {
  if (AUTH_REQUIRED) {
    return (
      <>
        <SignedIn>
          <MainLayout>
            <Routes>
              <Route path="/" element={<Navigate to="/prompts" replace />} />
              <Route path="/prompts" element={<DashboardPage />} />
              <Route path="/prompts/new" element={<NewPromptPage />} />
              <Route path="/prompt/edit" element={<PromptEditPage />} />
              {FEATURES.PROMPT_PARTS && (
              <>
                <Route path="/library" element={<PromptLibraryPage />} />
                <Route path="/library/new" element={<NewPromptPartPage />} />
                <Route path="/library/part" element={<PromptPartPage />} />
              </>
            )}
            </Routes>
          </MainLayout>
        </SignedIn>
        <SignedOut>
          <RedirectToSignIn />
        </SignedOut>
      </>
    );
  }

  // Auth disabled: render app routes directly
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/prompts" replace />} />
        <Route path="/prompts" element={<DashboardPage />} />
        <Route path="/prompts/new" element={<NewPromptPage />} />
        <Route path="/prompt/edit" element={<PromptEditPage />} />
         {FEATURES.PROMPT_PARTS && (
          <>
            <Route path="/library" element={<PromptLibraryPage />} />
            <Route path="/library/new" element={<NewPromptPartPage />} />
            <Route path="/library/part" element={<PromptPartPage />} />
          </>
        )}
      </Routes>
    </MainLayout>
  );
}

export default App;