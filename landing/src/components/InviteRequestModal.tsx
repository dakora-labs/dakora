import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface InviteRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function InviteRequestModal({ isOpen, onClose }: InviteRequestModalProps) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [useCase, setUseCase] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Use localhost for development, production API for production
      const apiUrl = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000/api/public/invite-request'
        : 'https://api.dakora.io/api/public/invite-request';
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name, company, use_case: useCase }),
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle rate limiting with a friendly message
        if (response.status === 429) {
          throw new Error('Whoa there! You\'ve made too many requests. Please wait a few minutes and try again. 🕐');
        }
        throw new Error(data.message || 'Failed to send request');
      }

      // Check if already invited (still a success case, but different message)
      if (data.status === 'already_invited' || data.status === 'already_exists') {
        setError(data.message);
        setLoading(false);
        return;
      }

      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setEmail('');
        setName('');
        setCompany('');
        setUseCase('');
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send invite request. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-8"
          >
            {success ? (
              <div className="text-center space-y-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">Request Received!</h3>
                <p className="text-gray-600">
                  We'll review your request and send your invitation within 24 hours. Check your inbox (and spam folder)!
                </p>
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">Request Invite</h2>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                      Email <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      id="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="you@company.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="John Doe"
                    />
                  </div>

                  <div>
                    <label htmlFor="company" className="block text-sm font-medium text-gray-700 mb-1">
                      Company
                    </label>
                    <input
                      type="text"
                      id="company"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Acme Inc"
                    />
                  </div>

                  <div>
                    <label htmlFor="useCase" className="block text-sm font-medium text-gray-700 mb-1">
                      What will you use Dakora for?
                    </label>
                    <textarea
                      id="useCase"
                      value={useCase}
                      onChange={(e) => setUseCase(e.target.value)}
                      rows={3}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      placeholder="e.g., Track costs for our AI chatbot"
                    />
                  </div>

                  {error && (
                    <div className="text-amber-700 text-sm bg-amber-50 p-3 rounded-lg border border-amber-200">
                      <div className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{error}</span>
                      </div>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-500 text-white font-semibold py-3 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Sending...' : 'Request Invite'}
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    We'll review your request and send your invitation within 24 hours.
                  </p>
                </form>
              </>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
