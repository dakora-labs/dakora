# Dakora Landing Page

Modern, animated landing page for Dakora built with Astro, Tailwind CSS, and Framer Motion.

## Features

- **Astro** - Fast, modern static site generator
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Smooth, beautiful animations
- **React** - For interactive components
- **GitHub Pages** - Automatic deployment

## Development

```bash
# Install dependencies
npm install

# Start dev server (localhost:4321)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Deployment

The site automatically deploys to GitHub Pages when changes are pushed to the `main` branch in the `landing/` directory.

## Structure

```
landing/
├── src/
│   ├── components/     # React components with animations
│   │   ├── Hero.tsx
│   │   ├── Features.tsx
│   │   ├── Playground.tsx
│   │   ├── QuickStart.tsx
│   │   ├── CTA.tsx
│   │   ├── Navigation.tsx
│   │   └── Footer.tsx
│   ├── layouts/        # Astro layouts
│   │   └── Layout.astro
│   ├── pages/          # Astro pages
│   │   └── index.astro
│   └── styles/         # Global styles
│       └── global.css
├── public/             # Static assets
└── astro.config.mjs    # Astro configuration
```

## Design Inspiration

The design is inspired by modern SaaS landing pages like Helicone and Honeycomb, featuring:
- Gradient backgrounds with animated blobs
- Smooth scroll animations
- Hover effects and micro-interactions
- Clean, professional typography
- Responsive design for all devices

## Learn More

- [Astro Documentation](https://docs.astro.build)
- [Tailwind CSS](https://tailwindcss.com)
- [Framer Motion](https://www.framer.com/motion)
