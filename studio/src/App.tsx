import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectDashboardPage } from './pages/ProjectDashboardPage';
import { PromptEditPage } from './pages/PromptEditPage';
import { NewPromptPage } from './pages/NewPromptPage';
import { PromptLibraryPage } from './pages/PromptLibraryPage';
import { NewPromptPartPage } from './pages/NewPromptPartPage';
import { PromptPartPage } from './pages/PromptPartPage';
import { SettingsPage } from './pages/SettingsPage';
import { OptimizePromptPage } from './pages/OptimizePromptPage';
import { ProjectRedirect } from './components/ProjectRedirect';
import { UserContextProvider } from './contexts/UserContext';
import { ExecutionsPage } from './pages/ExecutionsPage';
import { ExecutionDetailPage } from './pages/ExecutionDetailPage';
import { Toaster } from './components/ui/toaster';

function App() {
  if (AUTH_REQUIRED) {
    return (
      <>
        <SignedIn>
        <UserContextProvider>
          <MainLayout>
            <Routes>
              <Route path="/" element={<ProjectRedirect />} />
              <Route path="/project/:projectSlug/dashboard" element={<ProjectDashboardPage />} />
              <Route path="/project/:projectSlug/prompts" element={<DashboardPage />} />
              <Route path="/project/:projectSlug/prompts/new" element={<NewPromptPage />} />
              <Route path="/project/:projectSlug/prompt/edit" element={<PromptEditPage />} />
              <Route path="/project/:projectSlug/prompt/optimize" element={<OptimizePromptPage />} />
              <Route path="/project/:projectSlug/library" element={<PromptLibraryPage />} />
              <Route path="/project/:projectSlug/library/new" element={<NewPromptPartPage />} />
              <Route path="/project/:projectSlug/library/part" element={<PromptPartPage />} />
              <Route path="/project/:projectSlug/executions" element={<ExecutionsPage />} />
              <Route path="/project/:projectSlug/executions/:traceId" element={<ExecutionDetailPage />} />
              <Route path="/project/:projectSlug/settings" element={<SettingsPage />} />
            </Routes>
          </MainLayout>
          <Toaster />
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
      <UserContextProvider>
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/project/default/dashboard" replace />} />
        <Route path="/project/:projectSlug/dashboard" element={<ProjectDashboardPage />} />
        <Route path="/project/:projectSlug/prompts" element={<DashboardPage />} />
        <Route path="/project/:projectSlug/prompts/new" element={<NewPromptPage />} />
        <Route path="/project/:projectSlug/prompt/edit" element={<PromptEditPage />} />
        <Route path="/project/:projectSlug/prompt/optimize" element={<OptimizePromptPage />} />
        <Route path="/project/:projectSlug/library" element={<PromptLibraryPage />} />
        <Route path="/project/:projectSlug/library/new" element={<NewPromptPartPage />} />
        <Route path="/project/:projectSlug/library/part" element={<PromptPartPage />} />
        <Route path="/project/:projectSlug/executions" element={<ExecutionsPage />} />
        <Route path="/project/:projectSlug/executions/:traceId" element={<ExecutionDetailPage />} />
        <Route path="/project/:projectSlug/settings" element={<SettingsPage />} />
      </Routes>
    </MainLayout>
    <Toaster />
    </UserContextProvider>
  );
}

export default App;
