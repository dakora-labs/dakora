import { SignIn } from '@clerk/clerk-react';
import { motion } from 'framer-motion';

export function InviteOnlyLoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-6">
      <div className="max-w-6xl w-full grid lg:grid-cols-[1.2fr,1fr] gap-12 items-start lg:items-end">
        {/* Left side - Messaging */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-8"
        >
          <div className="flex items-center gap-3">
            <img 
              src="/logo-light.svg" 
              alt="Dakora Logo" 
              className="h-12 w-auto"
            />
          </div>

          <div className="space-y-4">
            <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 leading-tight">
              Welcome to<br />Dakora Studio
            </h1>
            <p className="text-xl text-gray-600 max-w-lg leading-relaxed">
              Track every LLM call. Control costs. Optimize prompts.
            </p>
          </div>

          <div className="space-y-4">
            <div className="bg-white/70 backdrop-blur-sm border border-blue-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start gap-4 mb-5">
                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-5 h-5 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 mb-2 text-lg">Invite-Only Access</h3>
                  <p className="text-sm text-gray-600 leading-relaxed mb-4">
                    Dakora is currently in invite-only mode. If you have received an invitation, 
                    use the sign-in form to access Studio.
                  </p>
                  <a
                    href="https://dakora.io"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-indigo-700 transition-all hover:shadow-lg hover:scale-105 active:scale-100 group text-sm"
                  >
                    <span>Request an Invite</span>
                    <svg
                      className="w-4 h-4 group-hover:translate-x-1 transition-transform"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      strokeWidth={2.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </a>
                </div>
              </div>
            </div>

            <div className="bg-white/70 backdrop-blur-sm border border-green-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-5 h-5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 mb-2 text-lg">Already have an account?</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    Use the sign-in form to access your workspace.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6 pt-4 flex-wrap">
            <a
              href="https://docs.dakora.io"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors flex items-center gap-2 group"
            >
              <svg className="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
              <span>Documentation</span>
            </a>
            <a
              href="https://github.com/dakora-labs/dakora"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors flex items-center gap-2 group"
            >
              <svg className="w-4 h-4 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 24 24">
                <path
                  fillRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  clipRule="evenodd"
                />
              </svg>
              <span>GitHub</span>
            </a>
          </div>
        </motion.div>

        {/* Right side - Sign In Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex items-end justify-center lg:justify-end"
        >
          <div className="w-full max-w-md">
            <SignIn
              appearance={{
                elements: {
                  rootBox: 'w-full',
                  card: 'shadow-2xl border-0 rounded-3xl bg-white/90 backdrop-blur-md',
                  headerTitle: 'text-3xl font-bold text-gray-900',
                  headerSubtitle: 'text-gray-600 text-base',
                  socialButtonsBlockButton: 'border-2 border-gray-200 hover:border-blue-500 hover:bg-blue-50 rounded-xl font-medium transition-all',
                  formButtonPrimary: 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 rounded-xl font-semibold py-3 shadow-lg hover:shadow-xl transition-all',
                  footerActionLink: 'text-blue-600 hover:text-blue-700 font-semibold',
                  formFieldInput: 'rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                  formFieldLabel: 'font-medium text-gray-700',
                  dividerLine: 'bg-gray-200',
                  dividerText: 'text-gray-500 font-medium',
                },
              }}
              signUpUrl={undefined}
              routing="hash"
              redirectUrl="/"
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
