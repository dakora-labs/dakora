import { motion } from 'framer-motion';
import { useRef } from 'react';
import { useInView } from 'framer-motion';

export default function Discord() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 px-6 bg-white">
      <div className="container mx-auto max-w-4xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Join our community.
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Connect with other developers, get help, and share your feedback. We're here to support you.
          </p>
          <a
            href="https://discord.gg/QSRRcFjzE8"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-3 px-8 py-4 bg-[#5865F2] text-white font-semibold rounded-lg hover:bg-[#4752C4] transition-all hover:-translate-y-0.5 shadow-lg hover:shadow-xl"
          >
            <img src="/discord-icon.svg" alt="Discord" className="w-6 h-6 brightness-0 invert" />
            Join us on Discord
          </a>
        </motion.div>
      </div>
    </section>
  );
}
