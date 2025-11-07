import { motion } from 'framer-motion';
import { useInView } from 'framer-motion';
import { useRef } from 'react';

const steps = [
  {
    number: "1",
    title: "Initialize Project",
    code: "dakora init",
    description: "Creates configuration file and example templates"
  },
  {
    number: "2",
    title: "Create Template",
    code: `id: greeting
version: 1.0.0
description: A personalized greeting template
template: |
  Hello {{ name }}!
  {% if age %}You are {{ age }} years old.{% endif %}
inputs:
  name:
    type: string
    required: true
  age:
    type: number
    required: false`,
    description: "Define your prompt template with type-safe inputs",
    lang: "yaml"
  },
  {
    number: "3",
    title: "Use in Python",
    code: `from dakora import Vault

vault = Vault("dakora.yaml")
template = vault.get("greeting")
result = template.render(name="Alice", age=25)
print(result)`,
    description: "Integrate prompts into your application",
    lang: "python"
  }
];

export default function QuickStart() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 px-4 bg-white" id="quickstart">
      <div className="container mx-auto max-w-5xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl font-black text-gray-900 mb-4">Quick Start</h2>
          <p className="text-xl text-gray-600">Get up and running in minutes</p>
        </motion.div>

        <div className="space-y-12">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
              transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
              className="relative"
            >
              <div className="flex items-start gap-6">
                <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg">
                  {step.number}
                </div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold text-gray-900 mb-3">{step.title}</h3>
                  <div className="bg-gray-900 rounded-xl p-6 mb-3 relative overflow-x-auto">
                    <div className="absolute top-3 right-3 bg-indigo-600 text-white text-xs font-bold px-2 py-1 rounded">
                      {step.lang || 'bash'}
                    </div>
                    <pre className="text-green-400 font-mono text-sm overflow-x-auto">
                      <code>{step.code}</code>
                    </pre>
                  </div>
                  <p className="text-gray-600">{step.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
