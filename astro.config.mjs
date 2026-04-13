// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://chairs.usersimple.com',
  redirects: {
    '/admin': '/admin/index.html',
  },
  integrations: [mdx(), sitemap()],

  vite: {
    plugins: [tailwindcss()],
    server: {
      watch: {
        ignored: ['**/.env', '**/.env.*']
      }
    }
  },
});