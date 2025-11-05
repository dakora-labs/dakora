# Landing Page Wireframe

Based on the new design screenshot, this document outlines the structure and components needed for the landing page.

## Page Structure

### 1. Navigation Bar
- **Logo**: Dakora logo with bird icon (left)
- **CTA Button**: "Star on GitHub" with star count (right)
- **Background**: Clean white with subtle border

### 2. Hero Section
- **Headline**: "Make every token count."
- **Subheadline**: "Open-source observability and cost control for your AI applications"
- **CTA Buttons**:
  - Primary: "Create Free Account" (blue)
  - Secondary: "View Docs" (white/outline)
- **Subtext**: "Free with a 1-click forever." (gray, centered)

### 3. Animated Diagram Section
- **Background**: Teal/turquoise gradient (#0D9488 or similar)
- **Content**: Abstract flowing lines animation representing data flow/architecture
- **Style**: Wireframe-style geometric paths with subtle animations
- **Text Below**: "Track every LLM call, understand where tokens go, and enforce cost policies — all without extra effort."
- **Three Pills**:
  - "Cost analytics"
  - "Pricing engine"
  - "Semantic insights"

### 4. Features Section: "Full visibility, total control."
- **Headline**: "Full visibility, total control."
- **Subheadline**: "Dakora provides the tools you need to understand and manage your AI application's costs and performance."
- **Layout**: 2x2 grid of feature cards

#### Feature Cards:
1. **Real-time Cost Analytics**
   - Icon placeholder (light gray box)
   - Description: "See down into every API call: exactly which models, users, and features are driving your token consumption and costs."

2. **Dynamic Policy Engine**
   - Icon placeholder (light gray box)
   - Description: "Set budget alerts, rate limits, and access controls. Prevent runaway costs and ensure compliance without touching your codebase."

3. **Performance Monitoring**
   - Icon placeholder (light gray box)
   - Description: "Track latency, error rates, and response quality. Identify performance bottlenecks and optimize your application's efficiency."

4. **Data Privacy & Security**
   - Icon placeholder (light gray box)
   - Description: "Self-host with confidence: capture data rules while your infrastructure, ensuring your sensitive data never leaves."

### 5. Integration Section: "Works with your stack"
- **Headline**: "Works with your stack"
- **Subheadline**: "Dakora integrates with the tools you already use, with more on the way."
- **Layout**: Grid of integration logos (4 columns)
  - Microsoft Agent Framework
  - OpenAI Agents
  - LangChain
  - Semantic Kernel

### 6. Deployment Options: "Start locally. Scale globally."
- **Headline**: "Start locally. Scale globally."
- **Subheadline**: "Get Dakora running in your machine in minutes. It's the perfect way to start. When you're ready for production our cloud platform is ready for you."

#### Two Columns:
1. **Local Development**
   - Icon: Terminal/CLI icon
   - Description: "Experiment freely on your local machine. Free and open-source forever."
   - Code snippet:
     ```
     $ Install with pip
     $ pip install dakora
     ```

2. **Ready for Production?**
   - Icon: Cloud icon
   - Description: "Transition to our managed cloud solution for enterprise-grade scalability, reliability, and support. Everything you need."
   - CTA: "Explore Dakora Cloud" (blue button)
   - Subtext: "Get started for free."

### 7. Social Proof
- **GitHub Stars**: "1,234 GitHub Stars" with star icon
- **Positioning**: Centered, prominent display

### 8. Open Source Statement
- **Headline**: "Dakora is proudly open-source."
- **Text**: "Here on trust the balance of AI observability. Your contributions and feedback shape the future of this tool."
- **CTA**: "Star Dakora on GitHub" (black button)

### 9. Footer
- **Copyright**: "© 2025 Dakora. All rights reserved."
- **Links**: Docs | GitHub | Twitter | Privacy Policy

## Design System Notes

### Colors
- **Primary**: Blue (#3B82F6 or similar)
- **Accent**: Teal/Turquoise (#0D9488)
- **Background**: Light gray (#F9FAFB)
- **Text**: Dark gray (#111827)
- **White**: #FFFFFF

### Typography
- **Headings**: Bold, large (text-5xl to text-6xl)
- **Body**: Regular, readable (text-lg to text-xl)
- **Code**: Monospace font

### Spacing
- **Section padding**: py-24 to py-32
- **Container max-width**: max-w-7xl
- **Card padding**: p-8 to p-12

### Components
- **Buttons**: Rounded-lg, bold text, clear hover states
- **Cards**: White background, rounded-2xl, shadow-lg
- **Pills**: Rounded-full, subtle background
- **Code blocks**: Dark background, syntax highlighting

## Animation Notes
- **Hero**: Fade in from bottom
- **Diagram**: Continuous flowing animation of lines
- **Feature cards**: Stagger animation on scroll
- **Hover effects**: Subtle lift and shadow increase
