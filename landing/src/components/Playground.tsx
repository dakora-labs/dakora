import { motion } from 'framer-motion';
import { useInView } from 'framer-motion';
import { useRef } from 'react';

const playgroundFeatures = [
  {
    icon: "✏️",
    title: "Live Template Editing",
    description: "Real-time syntax highlighting and validation"
  },
  {
    icon: "🧪",
    title: "Interactive Testing",
    description: "Test templates instantly with custom inputs"
  },
  {
    icon: "📱",
    title: "Mobile Responsive",
    description: "Works perfectly on all devices"
  },
  {
    icon: "🎨",
    title: "Modern UI",
    description: "Built with shadcn/ui components"
  }
];

export default function Playground() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 px-4 bg-gradient-to-br from-slate-50 to-slate-100" id="playground">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-5xl font-black text-gray-900 mb-4">🎯 Interactive Playground</h2>
          <p className="text-xl text-gray-700 font-semibold mb-2">
            Try it now at{' '}
            <a
              href="https://playground.dakora.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-700 underline decoration-2"
            >
              playground.dakora.io
            </a>
            {' '}— no installation required!
          </p>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Experience the exact same playground that runs locally with{' '}
            <code className="bg-gray-200 px-2 py-1 rounded text-sm font-mono">dakora playground</code>
            , now available in your browser.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-12 text-center"
        >
          <motion.a
            href="https://playground.dakora.io/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-10 py-5 rounded-xl font-bold text-xl shadow-2xl hover:bg-indigo-700 transition-colors"
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Launch Web Playground
          </motion.a>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -50 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="relative"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur-2xl opacity-20" />
            <img
              src="/playground-interface.png"
              alt="Dakora Playground Interface"
              className="relative rounded-2xl shadow-2xl border-4 border-white"
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 50 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="space-y-6"
          >
            {playgroundFeatures.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
                transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                className="flex gap-4 items-start bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow"
              >
                <div className="text-3xl flex-shrink-0">{feature.icon}</div>
                <div>
                  <h4 className="text-lg font-bold text-gray-900 mb-2">{feature.title}</h4>
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}