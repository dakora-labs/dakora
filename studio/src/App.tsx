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
import { FeedbackProvider } from './contexts/FeedbackContext';
import { ExecutionsPage } from './pages/ExecutionsPage';
import { ExecutionDetailPage } from './pages/ExecutionDetailPage';
import { Toaster } from './components/ui/toaster';
import { OnboardingWrapper } from './components/OnboardingWrapper';

function App() {
  if (AUTH_REQUIRED) {
    return (
      <>
        <SignedIn>
        <UserContextProvider>
          <FeedbackProvider>
            <MainLayout>
              <Routes>
                <Route path="/" element={<ProjectRedirect />} />
                <Route path="/project/:projectSlug/*" element={
                  <OnboardingWrapper>
                    <Routes>
                      <Route path="dashboard" element={<ProjectDashboardPage />} />
                      <Route path="prompts" element={<DashboardPage />} />
                      <Route path="prompts/new" element={<NewPromptPage />} />
                      <Route path="prompt/edit" element={<PromptEditPage />} />
                      <Route path="prompt/optimize" element={<OptimizePromptPage />} />
                      <Route path="library" element={<PromptLibraryPage />} />
                      <Route path="library/new" element={<NewPromptPartPage />} />
                      <Route path="library/part" element={<PromptPartPage />} />
                      <Route path="executions" element={<ExecutionsPage />} />
                      <Route path="executions/:traceId" element={<ExecutionDetailPage />} />
                      <Route path="settings" element={<SettingsPage />} />
                    </Routes>
                  </OnboardingWrapper>
                } />
              </Routes>
            </MainLayout>
            <Toaster />
          </FeedbackProvider>
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
        <FeedbackProvider>
          <MainLayout>
            <Routes>
              <Route path="/" element={<Navigate to="/project/default/dashboard" replace />} />
              <Route path="/project/:projectSlug/*" element={
                <OnboardingWrapper>
                  <Routes>
                    <Route path="dashboard" element={<ProjectDashboardPage />} />
                    <Route path="prompts" element={<DashboardPage />} />
                    <Route path="prompts/new" element={<NewPromptPage />} />
                    <Route path="prompt/edit" element={<PromptEditPage />} />
                    <Route path="prompt/optimize" element={<OptimizePromptPage />} />
                    <Route path="library" element={<PromptLibraryPage />} />
                    <Route path="library/new" element={<NewPromptPartPage />} />
                    <Route path="library/part" element={<PromptPartPage />} />
                    <Route path="executions" element={<ExecutionsPage />} />
                    <Route path="executions/:traceId" element={<ExecutionDetailPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                  </Routes>
                </OnboardingWrapper>
              } />
            </Routes>
          </MainLayout>
          <Toaster />
        </FeedbackProvider>
      </UserContextProvider>
  );
}

export default App;
