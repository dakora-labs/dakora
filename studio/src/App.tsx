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
import { ProjectRedirect } from './components/ProjectRedirect';
import { UserContextProvider } from './contexts/UserContext';

function App() {
  if (AUTH_REQUIRED) {
    return (
      <>
        <SignedIn>
          <UserContextProvider>
            <MainLayout>
              <Routes>
                <Route path="/" element={<ProjectRedirect />} />
                <Route path="/project/:projectSlug/prompts" element={<DashboardPage />} />
                <Route path="/project/:projectSlug/prompts/new" element={<NewPromptPage />} />
                <Route path="/project/:projectSlug/prompt/edit" element={<PromptEditPage />} />
                {FEATURES.PROMPT_PARTS && (
                <>
                  <Route path="/project/:projectSlug/library" element={<PromptLibraryPage />} />
                  <Route path="/project/:projectSlug/library/new" element={<NewPromptPartPage />} />
                  <Route path="/project/:projectSlug/library/part" element={<PromptPartPage />} />
                </>
              )}
              </Routes>
            </MainLayout>
          </UserContextProvider>
        </SignedIn>
        <SignedOut>
          <RedirectToSignIn />
        </SignedOut>
      </>
    );
  }

  // Auth disabled: use default project for local dev
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/project/default/prompts" replace />} />
        <Route path="/project/:projectSlug/prompts" element={<DashboardPage />} />
        <Route path="/project/:projectSlug/prompts/new" element={<NewPromptPage />} />
        <Route path="/project/:projectSlug/prompt/edit" element={<PromptEditPage />} />
         {FEATURES.PROMPT_PARTS && (
          <>
            <Route path="/project/:projectSlug/library" element={<PromptLibraryPage />} />
            <Route path="/project/:projectSlug/library/new" element={<NewPromptPartPage />} />
            <Route path="/project/:projectSlug/library/part" element={<PromptPartPage />} />
          </>
        )}
      </Routes>
    </MainLayout>
  );
}

export default App;