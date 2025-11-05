import { motion } from 'framer-motion';
import { useRef } from 'react';
import { useInView } from 'framer-motion';

const integrations = [
  { name: "Microsoft Agent Framework", category: "Framework", available: true },
  { name: "OpenAI Agents", category: "Provider", available: false },
  { name: "LangChain", category: "Framework", available: false },
  { name: "Semantic Kernel", category: "Framework", available: false }
];

export default function Integrations() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 px-6 bg-white">
      <div className="container mx-auto max-w-6xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Works with your stack
          </h2>
          <p className="text-xl text-gray-600">
            Dakora integrates with the tools you already use, with more on the way.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {integrations.map((integration, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={`bg-white rounded-xl p-8 border border-gray-200 flex flex-col items-center justify-center text-center transition-all relative ${
                integration.available
                  ? 'hover:shadow-lg hover:-translate-y-1'
                  : 'opacity-50 cursor-not-allowed'
              }`}
            >
              {!integration.available && (
                <div className="absolute top-3 right-3">
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                    Coming Soon
                  </span>
                </div>
              )}

              {/* Logo placeholder with specific styling for each */}
              {integration.name === "Microsoft Agent Framework" ? (
                <img
                  src="/logos/maf-logo.jpg"
                  alt="Microsoft Agent Framework"
                  className="w-20 h-20 mb-4 object-contain"
                />
              ) : integration.name === "OpenAI Agents" ? (
                <div className="w-20 h-20 mb-4 bg-black rounded-xl flex items-center justify-center">
                  <span className="text-white font-bold text-2xl">AI</span>
                </div>
              ) : integration.name === "LangChain" ? (
                <div className="w-20 h-20 mb-4 relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-green-400 to-emerald-600 rounded-xl"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-12 h-1 bg-white rounded-full"></div>
                  </div>
                </div>
              ) : (
                <div className="w-20 h-20 mb-4 relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-white font-bold text-xl">SK</span>
                  </div>
                </div>
              )}
              <h3 className={`font-semibold text-sm mb-1 ${integration.available ? 'text-gray-900' : 'text-gray-600'}`}>
                {integration.name}
              </h3>
              <p className="text-xs text-gray-500">{integration.category}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center mt-12"
        >
          <p className="text-lg text-gray-600 flex items-center justify-center gap-2">
            <span className="text-2xl">✨</span>
            <span>Many more integrations coming soon</span>
            <span className="text-2xl">✨</span>
          </p>
        </motion.div>
      </div>
    </section>
  );
}
