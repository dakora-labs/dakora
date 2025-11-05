import { motion } from 'framer-motion';

export default function AnimatedDiagram() {
  return (
    <section className="py-12 md:py-20 px-4 md:px-6 bg-gradient-to-b from-white to-gray-50">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="relative"
        >
          {/* Dashboard mockup with shadow and depth */}
          <div className="relative bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-4 md:px-8 py-4 md:py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-xl md:text-2xl font-bold text-gray-900">Analytics Dashboard</h3>
                <p className="text-sm md:text-base text-gray-500 mt-1">Monitor project performance and budget usage</p>
              </div>
              <button className="flex items-center gap-2 px-3 md:px-4 py-2 text-sm md:text-base text-gray-600 hover:text-gray-900 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="font-medium">Settings</span>
              </button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6 p-4 md:p-8 bg-gray-50">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}
                transition={{ duration: 0.5, delay: 0.1 }}
                viewport={{ once: true }}
                className="bg-white rounded-xl p-3 md:p-6 shadow-sm border border-gray-100 cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2 md:mb-3">
                  <div className="text-xs md:text-sm text-gray-600 font-medium">Total Cost</div>
                  <motion.div
                    className="w-8 h-8 md:w-10 md:h-10 bg-blue-100 rounded-lg flex items-center justify-center"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <span className="text-base md:text-xl">💲</span>
                  </motion.div>
                </div>
                <div className="text-xl md:text-3xl font-bold text-gray-900">$127.43</div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}
                transition={{ duration: 0.5, delay: 0.2 }}
                viewport={{ once: true }}
                className="bg-white rounded-xl p-3 md:p-6 shadow-sm border border-gray-100 cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2 md:mb-3">
                  <div className="text-xs md:text-sm text-gray-600 font-medium">Executions</div>
                  <motion.div
                    className="w-8 h-8 md:w-10 md:h-10 bg-green-100 rounded-lg flex items-center justify-center"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <svg className="w-4 h-4 md:w-5 md:h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </motion.div>
                </div>
                <div className="text-xl md:text-3xl font-bold text-gray-900">8,492</div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="bg-white rounded-xl p-3 md:p-6 shadow-sm border border-gray-100 cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2 md:mb-3">
                  <div className="text-xs md:text-sm text-gray-600 font-medium">Avg Cost</div>
                  <motion.div
                    className="w-8 h-8 md:w-10 md:h-10 bg-purple-100 rounded-lg flex items-center justify-center"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <svg className="w-4 h-4 md:w-5 md:h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                    </svg>
                  </motion.div>
                </div>
                <div className="text-xl md:text-3xl font-bold text-gray-900">$0.0150</div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}
                transition={{ duration: 0.5, delay: 0.4 }}
                viewport={{ once: true }}
                className="bg-white rounded-xl p-3 md:p-6 shadow-sm border border-gray-100 cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2 md:mb-3">
                  <div className="text-xs md:text-sm text-gray-600 font-medium">Budget Remaining</div>
                  <motion.div
                    className="w-8 h-8 md:w-10 md:h-10 bg-orange-100 rounded-lg flex items-center justify-center"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <svg className="w-4 h-4 md:w-5 md:h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                    </svg>
                  </motion.div>
                </div>
                <div className="text-xl md:text-3xl font-bold text-gray-900">$372.57</div>
              </motion.div>
            </div>

            {/* Chart */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              viewport={{ once: true }}
              className="p-4 md:p-8 bg-white group"
            >
              <h4 className="text-base md:text-lg font-bold text-gray-900 mb-4 md:mb-6">Daily Cost Trend (Last 30 Days)</h4>
              <div className="relative h-64">
                <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
                  {/* Grid lines */}
                  <line x1="0" y1="0" x2="800" y2="0" stroke="#E5E7EB" strokeWidth="1" />
                  <line x1="0" y1="50" x2="800" y2="50" stroke="#E5E7EB" strokeWidth="1" />
                  <line x1="0" y1="100" x2="800" y2="100" stroke="#E5E7EB" strokeWidth="1" />
                  <line x1="0" y1="150" x2="800" y2="150" stroke="#E5E7EB" strokeWidth="1" />
                  <line x1="0" y1="200" x2="800" y2="200" stroke="#E5E7EB" strokeWidth="1" />

                  {/* Invisible hit area for easier hover */}
                  <motion.path
                    d="M 0 200 Q 100 180 200 120 T 400 40 T 600 120 T 800 180"
                    fill="none"
                    stroke="transparent"
                    strokeWidth="30"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, ease: "easeInOut" }}
                    className="cursor-pointer"
                  />

                  {/* Animated curve (visible line) */}
                  <motion.path
                    d="M 0 200 Q 100 180 200 120 T 400 40 T 600 120 T 800 180"
                    fill="none"
                    stroke="#3B82F6"
                    strokeWidth="3"
                    initial={{ pathLength: 0 }}
                    whileInView={{ pathLength: 1 }}
                    whileHover={{ strokeWidth: 4 }}
                    transition={{ duration: 2, ease: "easeInOut" }}
                    viewport={{ once: true }}
                    style={{ pointerEvents: "none" }}
                  />

                  {/* Area under curve */}
                  <motion.path
                    d="M 0 200 Q 100 180 200 120 T 400 40 T 600 120 T 800 180 L 800 200 Z"
                    fill="url(#gradient)"
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ duration: 1, delay: 0.5 }}
                    viewport={{ once: true }}
                  />

                  <defs>
                    <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
                    </linearGradient>
                  </defs>

                  {/* Data points */}
                  <motion.circle
                    cx="400"
                    cy="40"
                    r="4"
                    fill="#3B82F6"
                    initial={{ scale: 0 }}
                    whileInView={{ scale: 1 }}
                    transition={{ duration: 0.3, delay: 1 }}
                    viewport={{ once: true }}
                  />
                  <motion.circle
                    cx="800"
                    cy="180"
                    r="4"
                    fill="#3B82F6"
                    initial={{ scale: 0 }}
                    whileInView={{ scale: 1 }}
                    transition={{ duration: 0.3, delay: 1.1 }}
                    viewport={{ once: true }}
                  />
                </svg>

                {/* X-axis labels */}
                <div className="flex justify-between mt-2 text-sm text-gray-500">
                  <span>10/29</span>
                  <span>10/30</span>
                  <span>10/31</span>
                  <span>11/3</span>
                </div>
              </div>
            </motion.div>

            {/* Footer status */}
            <div className="bg-gray-50 border-t border-gray-200 px-4 md:px-8 py-3 md:py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3 md:gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-gray-600">Connected</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm text-gray-600">Healthy</span>
                </div>
                <div className="bg-white px-3 py-1 rounded-full border border-gray-200">
                  <span className="text-sm font-medium text-gray-700">3 prompts</span>
                </div>
              </div>
              <div className="text-sm text-gray-400">Dakora</div>
            </div>
          </div>

          {/* Floating elements for depth */}
          <motion.div
            className="absolute -top-4 -right-4 w-20 h-20 bg-blue-500 rounded-2xl opacity-20 blur-2xl"
            animate={{
              scale: [1, 1.2, 1],
              rotate: [0, 90, 0],
            }}
            transition={{
              duration: 8,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
          <motion.div
            className="absolute -bottom-4 -left-4 w-20 h-20 bg-purple-500 rounded-2xl opacity-20 blur-2xl"
            animate={{
              scale: [1, 1.3, 1],
              rotate: [0, -90, 0],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        </motion.div>

        {/* Description */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          viewport={{ once: true }}
          className="text-center mt-8 md:mt-16 px-4"
        >
          <p className="text-base md:text-xl text-gray-700 max-w-4xl mx-auto mb-6 md:mb-8">
            Track every LLM call, understand where tokens go, and enforce cost policies — all without extra effort.
          </p>

          <div className="flex flex-wrap gap-2 md:gap-3 justify-center">
            <span className="px-4 md:px-6 py-2 bg-blue-100 text-blue-700 rounded-full font-medium text-xs md:text-sm flex items-center gap-2">
              <svg className="w-3 h-3 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Real-time analytics
            </span>
            <span className="px-4 md:px-6 py-2 bg-blue-100 text-blue-700 rounded-full font-medium text-xs md:text-sm flex items-center gap-2">
              <svg className="w-3 h-3 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Cost tracking
            </span>
            <span className="px-4 md:px-6 py-2 bg-blue-100 text-blue-700 rounded-full font-medium text-xs md:text-sm flex items-center gap-2">
              <svg className="w-3 h-3 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Performance insights
            </span>
            <span className="px-4 md:px-6 py-2 bg-blue-100 text-blue-700 rounded-full font-medium text-xs md:text-sm flex items-center gap-2">
              <svg className="w-3 h-3 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Prompt optimization
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
