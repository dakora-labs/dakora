# Landing Page Style Guide

## Color Palette

### Primary Colors
```css
--primary-50:  #EFF6FF   /* Lightest blue - backgrounds */
--primary-100: #DBEAFE   /* Very light blue - hover states */
--primary-200: #BFDBFE   /* Light blue - borders */
--primary-300: #93C5FD   /* Baby blue - accents */
--primary-400: #60A5FA   /* Medium blue - interactive elements */
--primary-500: #3B82F6   /* Jira blue - primary CTA */
--primary-600: #2563EB   /* Dark blue - hover on primary */
--primary-700: #1D4ED8   /* Darker blue - active states */
```

### Grayscale
```css
--gray-50:  #F9FAFB   /* Page background */
--gray-100: #F3F4F6   /* Section backgrounds */
--gray-200: #E5E7EB   /* Borders */
--gray-300: #D1D5DB   /* Dividers */
--gray-400: #9CA3AF   /* Placeholder text */
--gray-500: #6B7280   /* Secondary text */
--gray-600: #4B5563   /* Body text */
--gray-700: #374151   /* Headings */
--gray-800: #1F2937   /* Dark headings */
--gray-900: #111827   /* Darkest text */
```

### Accent Colors
```css
--accent-blue:  #0EA5E9   /* Sky blue - links */
--accent-teal:  #14B8A6   /* Teal - success states */
--success:      #10B981   /* Green - success */
--warning:      #F59E0B   /* Amber - warning */
--error:        #EF4444   /* Red - error */
```

### Semantic Colors
```css
--background:     #FFFFFF   /* White - cards, modals */
--surface:        #F9FAFB   /* Light gray - page background */
--border:         #E5E7EB   /* Gray - borders */
--text-primary:   #111827   /* Dark gray - main text */
--text-secondary: #6B7280   /* Medium gray - secondary text */
--text-tertiary:  #9CA3AF   /* Light gray - tertiary text */
```

## Typography

### Font Families
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'Fira Code', 'Monaco', 'Courier New', monospace;
```

### Font Sizes
```css
--text-xs:   0.75rem   /* 12px */
--text-sm:   0.875rem  /* 14px */
--text-base: 1rem      /* 16px */
--text-lg:   1.125rem  /* 18px */
--text-xl:   1.25rem   /* 20px */
--text-2xl:  1.5rem    /* 24px */
--text-3xl:  1.875rem  /* 30px */
--text-4xl:  2.25rem   /* 36px */
--text-5xl:  3rem      /* 48px */
--text-6xl:  3.75rem   /* 60px */
--text-7xl:  4.5rem    /* 72px */
```

### Font Weights
```css
--font-normal:    400
--font-medium:    500
--font-semibold:  600
--font-bold:      700
--font-extrabold: 800
```

### Line Heights
```css
--leading-tight:   1.25
--leading-snug:    1.375
--leading-normal:  1.5
--leading-relaxed: 1.625
--leading-loose:   2
```

## Spacing

### Base Unit: 4px
```css
--space-0:  0
--space-1:  0.25rem  /* 4px */
--space-2:  0.5rem   /* 8px */
--space-3:  0.75rem  /* 12px */
--space-4:  1rem     /* 16px */
--space-5:  1.25rem  /* 20px */
--space-6:  1.5rem   /* 24px */
--space-8:  2rem     /* 32px */
--space-10: 2.5rem   /* 40px */
--space-12: 3rem     /* 48px */
--space-16: 4rem     /* 64px */
--space-20: 5rem     /* 80px */
--space-24: 6rem     /* 96px */
--space-32: 8rem     /* 128px */
```

## Border Radius
```css
--radius-sm:   0.25rem  /* 4px - small elements */
--radius-md:   0.5rem   /* 8px - buttons, inputs */
--radius-lg:   0.75rem  /* 12px - cards */
--radius-xl:   1rem     /* 16px - large cards */
--radius-2xl:  1.5rem   /* 24px - hero sections */
--radius-full: 9999px   /* Fully rounded - pills, badges */
```

## Shadows
```css
--shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.1);
--shadow-xl:  0 20px 25px -5px rgb(0 0 0 / 0.1);
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
```

## Animations

### Durations
```css
--duration-fast:   150ms
--duration-normal: 300ms
--duration-slow:   500ms
```

### Easings
```css
--ease-in:     cubic-bezier(0.4, 0, 1, 1)
--ease-out:    cubic-bezier(0, 0, 0.2, 1)
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)
```

### Common Animations
```css
/* Fade in from bottom */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Scale on hover */
@keyframes scaleUp {
  to {
    transform: scale(1.05);
  }
}

/* Floating animation */
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
```

## Component Styles

### Buttons
```css
/* Primary Button */
background: var(--primary-500);
color: white;
padding: 12px 24px;
border-radius: var(--radius-md);
font-weight: var(--font-semibold);
transition: all var(--duration-normal) var(--ease-out);

hover: background: var(--primary-600);
hover: transform: translateY(-2px);
hover: box-shadow: var(--shadow-lg);

/* Secondary Button */
background: white;
color: var(--primary-500);
border: 2px solid var(--primary-500);
```

### Cards
```css
background: white;
border-radius: var(--radius-xl);
padding: var(--space-8);
box-shadow: var(--shadow-md);
border: 1px solid var(--border);

hover: box-shadow: var(--shadow-xl);
hover: transform: translateY(-4px);
transition: all var(--duration-normal) var(--ease-out);
```

### Pills/Tags
```css
background: var(--primary-100);
color: var(--primary-700);
padding: 6px 16px;
border-radius: var(--radius-full);
font-size: var(--text-sm);
font-weight: var(--font-medium);
```

## Layout

### Max Widths
```css
--container-sm:  640px
--container-md:  768px
--container-lg:  1024px
--container-xl:  1280px
--container-2xl: 1536px
```

### Breakpoints
```css
--screen-sm:  640px
--screen-md:  768px
--screen-lg:  1024px
--screen-xl:  1280px
--screen-2xl: 1536px
```

## Usage Guidelines

### Do's
- Use baby blue (primary-300 to primary-500) for primary actions and highlights
- Keep backgrounds light (gray-50, white) for easy reading
- Use subtle shadows for depth
- Maintain consistent spacing using the 4px grid
- Use semibold or bold for headings
- Keep animations subtle and purposeful

### Don'ts
- Avoid dark backgrounds on main content areas
- Don't use pure black (#000000) - use gray-900 instead
- Avoid mixing too many accent colors on one screen
- Don't use animations longer than 500ms
- Avoid small font sizes below 14px for body text
