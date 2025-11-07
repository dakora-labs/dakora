import { motion } from 'framer-motion';
import { useRef } from 'react';
import { useInView } from 'framer-motion';

const features = [
  {
    title: "Real-time Cost Analytics",
    description: "See down into every API call: exactly which models, users, and features are driving your token consumption and costs."
  },
  {
    title: "Dynamic Policy Engine",
    description: "Set budget alerts, rate limits, and access controls. Prevent runaway costs and ensure compliance without touching your codebase."
  },
  {
    title: "Performance Monitoring",
    description: "Track latency, error rates, and response quality. Identify performance bottlenecks and optimize your application's efficiency."
  },
  {
    title: "Prompt Management & Optimization",
    description: "Version control your prompts, test with real data, and optimize performance with AI-powered suggestions."
  }
];

function FeatureCard({ feature, index }: { feature: typeof features[0], index: number }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  // Special rendering for Real-time Cost Analytics
  if (feature.title === "Real-time Cost Analytics") {
    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
        transition={{ duration: 0.5, delay: index * 0.1 }}
        className="bg-white rounded-2xl p-8 border border-gray-200 hover:shadow-lg transition-all"
      >
        {/* Executions Page Mockup */}
        <div className="w-full mb-6 bg-gray-50 rounded-lg p-4 border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="mb-3">
            <h4 className="text-sm font-bold text-gray-900">Executions</h4>
            <p className="text-xs text-gray-500">Inspect agent runs, token usage, and costs</p>
          </div>

          {/* Scrollable Container - only on mobile */}
          <div className="overflow-x-auto md:overflow-x-visible -mx-4 md:mx-0 px-4 md:px-0">
            <div className="min-w-[600px] md:min-w-0">
              {/* Summary Stats */}
              <div className="grid grid-cols-5 gap-2 mb-3">
                <div>
                  <div className="text-xs text-gray-500">Page Cost</div>
                  <div className="text-sm font-bold text-green-600">US$0.0002</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Total Tokens</div>
                  <div className="text-sm font-bold text-blue-600">1,466</div>
                  <div className="text-xs text-gray-400">↓972 ↑494</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Avg Latency</div>
                  <div className="text-sm font-bold text-purple-600">1544ms</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">With Templates</div>
                  <div className="text-sm font-bold text-blue-600">24 / 25</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Avg Cost/Exec</div>
                  <div className="text-sm font-bold text-orange-600">US$0.0000</div>
                </div>
              </div>

              {/* Execution Rows */}
              <div className="space-y-2">
                {/* Row 1 */}
                <div className="bg-white rounded p-2 border border-gray-100">
                  <div className="grid grid-cols-5 gap-2 items-center text-xs">
                    <div>
                      <div className="text-gray-500">2d ago</div>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">azure_openai</span>
                    </div>
                    <div className="text-gray-600">gpt-4o-mini</div>
                    <div>
                      <span className="text-green-600 font-medium">16 → 23</span>
                      <div className="text-gray-400">Total: 39</div>
                    </div>
                    <div>
                      <div className="text-gray-600">4,640 ms</div>
                      <span className="px-2 py-0.5 bg-gray-900 text-white rounded text-xs">Normal</span>
                    </div>
                    <div className="text-green-600 font-medium">US$0.0000</div>
                  </div>
                </div>

                {/* Row 2 */}
                <div className="bg-white rounded p-2 border border-gray-100">
                  <div className="grid grid-cols-5 gap-2 items-center text-xs">
                    <div>
                      <div className="text-gray-500">5d ago</div>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">azure_openai</span>
                    </div>
                    <div className="text-gray-600">gpt-4o-mini</div>
                    <div>
                      <span className="text-green-600 font-medium">42 → 25</span>
                      <div className="text-gray-400">Total: 67</div>
                    </div>
                    <div>
                      <div className="text-gray-600">1,428 ms</div>
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">Fast</span>
                    </div>
                    <div className="text-green-600 font-medium">US$0.0000</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
        <p className="text-gray-600 leading-relaxed">{feature.description}</p>
      </motion.div>
    );
  }

  // Special rendering for Dynamic Policy Engine
  if (feature.title === "Dynamic Policy Engine") {
    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
        transition={{ duration: 0.5, delay: index * 0.1 }}
        className="bg-white rounded-2xl p-8 border border-gray-200 hover:shadow-lg transition-all"
      >
        {/* Budget Controls Mockup */}
        <div className="w-full mb-6 bg-white rounded-lg p-4 border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="mb-4">
            <h4 className="text-sm font-bold text-gray-900 mb-1">Budget Controls</h4>
            <p className="text-xs text-gray-500">Set monthly spending limits to prevent cost overruns</p>
          </div>

          {/* Monthly Budget */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-gray-900 mb-2">Monthly Budget (USD)</div>
            <input
              type="text"
              placeholder="No limit"
              className="w-full px-3 py-2 border border-gray-200 rounded text-xs text-gray-500"
              disabled
            />
            <p className="text-xs text-gray-400 mt-1">Leave empty for unlimited spending</p>
          </div>

          {/* Enforcement Mode */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-gray-900 mb-2">Enforcement Mode</div>
            <div className="px-3 py-2 border border-gray-200 rounded text-xs text-gray-900 bg-gray-50 flex items-center justify-between">
              <span>Strict - Block executions when exceeded</span>
              <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <p className="text-xs text-gray-400 mt-1">Agent executions will be blocked when budget is exceeded</p>
          </div>

          {/* Warning Threshold */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-gray-900 mb-2">Warning Threshold: 80%</div>
            <div className="relative">
              <div className="w-full h-2 bg-gray-200 rounded-full">
                <div className="w-4/5 h-2 bg-gray-900 rounded-full"></div>
              </div>
              <div className="absolute top-0 right-1/5 -translate-x-1/2 -translate-y-1">
                <div className="w-4 h-4 bg-white border-2 border-gray-900 rounded-full"></div>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2">Show warning when budget reaches this percentage</p>
          </div>

          {/* Save Button */}
          <button className="px-4 py-2 bg-gray-900 text-white text-xs font-semibold rounded">
            Save Budget Settings
          </button>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
        <p className="text-gray-600 leading-relaxed">{feature.description}</p>
      </motion.div>
    );
  }

  // Special rendering for Performance Monitoring
  if (feature.title === "Performance Monitoring") {
    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
        transition={{ duration: 0.5, delay: index * 0.1 }}
        className="bg-white rounded-2xl p-8 border border-gray-200 hover:shadow-lg transition-all"
      >
        {/* Trace Detail Mockup */}
        <div className="w-full mb-6 bg-gray-50 rounded-lg p-4 border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="mb-3">
            <h4 className="text-sm font-bold text-gray-900">Trace Detail</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-500 font-mono">9c31f50c-a6bf...</span>
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">azure_openai</span>
            </div>
          </div>

          {/* Stat Cards */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            {/* Total Tokens */}
            <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <span className="text-xs font-semibold text-blue-700">TOTAL TOKENS</span>
              </div>
              <div className="text-xl font-bold text-blue-900">39</div>
              <div className="flex items-center gap-2 mt-1 text-xs">
                <span className="text-green-600">↓ 16</span>
                <span className="text-blue-600">↑ 23</span>
              </div>
            </div>

            {/* Cost */}
            <div className="bg-green-50 rounded-lg p-3 border border-green-100">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-green-600 rounded flex items-center justify-center">
                  <span className="text-white text-xs font-bold">$</span>
                </div>
                <span className="text-xs font-semibold text-green-700">COST (USD)</span>
              </div>
              <div className="text-xl font-bold text-green-900">$0.0000</div>
              <div className="text-xs text-green-600 mt-1">$0.0004 per 1K</div>
            </div>

            {/* Latency */}
            <div className="bg-purple-50 rounded-lg p-3 border border-purple-100">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-purple-600 rounded flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-xs font-semibold text-purple-700">LATENCY (MS)</span>
              </div>
              <div className="text-xl font-bold text-purple-900">4,640</div>
              <div className="text-xs text-purple-600 mt-1">4.64 seconds</div>
            </div>

            {/* Messages */}
            <div className="bg-orange-50 rounded-lg p-3 border border-orange-100">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-orange-600 rounded flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <span className="text-xs font-semibold text-orange-700">MESSAGES</span>
              </div>
              <div className="text-xl font-bold text-orange-900">2</div>
              <div className="text-xs text-orange-600 mt-1">1 template</div>
            </div>
          </div>

          {/* Template Info */}
          <div className="bg-white rounded p-2 border border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">#1</span>
              <span className="text-xs text-blue-600 font-medium">simple_question</span>
              <span className="text-xs text-gray-400">v1.0.0</span>
            </div>
          </div>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
        <p className="text-gray-600 leading-relaxed">{feature.description}</p>
      </motion.div>
    );
  }

  // Special rendering for Prompt Management & Optimization
  if (feature.title === "Prompt Management & Optimization") {
    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
        transition={{ duration: 0.5, delay: index * 0.1 }}
        className="bg-white rounded-2xl p-8 border border-gray-200 hover:shadow-lg transition-all"
      >
        {/* Prompt Editor Mockup */}
        <div className="w-full mb-6 bg-gray-50 rounded-lg p-4 border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-gray-900">social_media_campaign</span>
              <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">v1</span>
            </div>
            <button className="px-3 py-1 bg-purple-600 text-white text-xs font-semibold rounded flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Optimize
            </button>
          </div>

          {/* Variables */}
          <div className="mb-3">
            <div className="text-xs font-semibold text-gray-700 mb-2">Variables</div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">campaign_brief</span>
                <span className="text-gray-400">(string)</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">platforms</span>
                <span className="text-gray-400">(array&lt;string&gt;)</span>
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="bg-white rounded p-3 border border-gray-200 text-xs font-mono leading-relaxed">
            <div className="text-gray-700">You are a helpful AI assistant.</div>
            <div className="text-gray-700 mt-2">Task: Create social media posts...</div>
            <div className="text-gray-500 mt-2">Campaign Brief:</div>
            <div className="text-purple-600">{"{{ campaign_brief }}"}</div>
          </div>

          {/* Run Button */}
          <button className="w-full mt-3 px-4 py-2 bg-gray-900 text-white text-xs font-semibold rounded flex items-center justify-center gap-2">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z"/>
            </svg>
            Run Prompt
          </button>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
        <p className="text-gray-600 leading-relaxed">{feature.description}</p>
      </motion.div>
    );
  }

  // Default rendering for other features
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="bg-white rounded-2xl p-8 border border-gray-200 hover:shadow-lg transition-all"
    >
      <div className="w-full h-32 bg-gray-100 rounded-lg mb-6 flex items-center justify-center text-gray-400 text-sm">
        [Icon Placeholder]
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
      <p className="text-gray-600 leading-relaxed">{feature.description}</p>
    </motion.div>
  );
}

export default function Features() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 px-6 bg-gray-50" id="features">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Full visibility, total control.
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Dakora provides the tools you need to understand and manage your AI application's costs and performance.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {features.map((feature, index) => (
            <FeatureCard key={index} feature={feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}