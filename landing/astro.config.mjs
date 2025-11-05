// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  site: 'https://dakora.io',
  base: '/',
  output: 'static',
  build: {
    assets: '_astro'
  },
  vite: {
    plugins: [tailwindcss()],
    build: {
      assetsInlineLimit: 0
    }
  },
  integrations: [react()]
});