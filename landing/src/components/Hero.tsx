import { motion } from 'framer-motion';
import { useState } from 'react';
import InviteRequestModal from './InviteRequestModal';

export default function Hero() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <section className="pt-24 md:pt-32 pb-12 md:pb-20 px-4 md:px-6 bg-white">
        <div className="container mx-auto max-w-5xl">
          <div className="text-center space-y-6 md:space-y-8">
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 leading-tight px-4"
            >
              Make every token count.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-lg sm:text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto px-4"
            >
              Track every LLM call. Control costs. Optimize prompts. All from one open-source platform.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-wrap gap-4 justify-center pt-4"
            >
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-8 py-3 bg-blue-500 text-white font-semibold rounded-lg hover:bg-blue-600 transition-all hover:-translate-y-0.5 shadow-md hover:shadow-lg"
              >
                Request Invite
              </button>
            <a
              href="https://docs.dakora.io"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-3 bg-white text-gray-700 font-semibold rounded-lg border-2 border-gray-300 hover:border-gray-400 transition-all hover:-translate-y-0.5 inline-block"
            >
              View Docs
            </a>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-sm text-gray-500"
          >
            Open-source and free to self-host. Always.
          </motion.p>
        </div>
      </div>
    </section>

    <InviteRequestModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </>
  );
}