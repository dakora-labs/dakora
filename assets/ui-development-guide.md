# UI Development Guide

This guide provides comprehensive information for developing and working with the Dakora Studio UI, a React-based web interface for template development and testing.

## Tech Stack

- **React 18** + TypeScript - UI framework with type safety
- **Vite** - Fast build tool and development server
- **React Router** - Client-side routing
- **shadcn/ui** - Component library built on Radix UI
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Icon library

## Project Structure

```text
studio/
├── src/
│   ├── App.tsx                      # Main app with routing
│   ├── main.tsx                     # Entry point
│   ├── index.css                    # Global styles
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── MainLayout.tsx       # Layout container with sidebar
│   │   │   ├── TopBar.tsx           # Top navigation bar
│   │   │   └── Sidebar.tsx          # Collapsible sidebar navigation
│   │   │
│   │   ├── PromptList.tsx           # Template list component
│   │   ├── PromptEditor.tsx         # Template editing component with YAML
│   │   ├── StatusBar.tsx            # Footer status bar
│   │   ├── NewPromptDialog.tsx      # New template creation dialog
│   │   │
│   │   ├── optimization/
│   │   │   ├── OptimizationProgress.tsx  # Progress indicator during optimization
│   │   │   ├── OptimizationResults.tsx   # Side-by-side results comparison
│   │   │   └── OptimizationHistory.tsx   # History list of optimizations
│   │   │
│   │   └── ui/                      # shadcn/ui components (auto-generated)
│   │       ├── button.tsx
│   │       ├── dialog.tsx
│   │       ├── input.tsx
│   │       ├── card.tsx
│   │       └── ...
│   │
│   ├── pages/
│   │   ├── DashboardPage.tsx        # Template browser with search
│   │   ├── PromptEditPage.tsx       # Template editor page
│   │   ├── OptimizePromptPage.tsx   # Prompt optimization interface
│   │   └── NewPromptPage.tsx        # New template creation page
│   │
│   ├── views/
│   │   ├── PromptsView.tsx          # Prompts tab view
│   │   └── ExecuteView.tsx          # Execution/comparison view
│   │
│   ├── hooks/
│   │   └── useApi.ts                # API client hooks (usePrompts, useOptimize, etc.)
│   │
│   ├── utils/
│   │   └── api.ts                   # API utility functions and client setup
│   │
│   └── lib/
│       └── utils.ts                 # Utility functions (cn, etc.)
│
├── public/                          # Static assets
├── dist/                            # Built output (gitignored)
├── index.html                       # HTML template
├── vite.config.ts                   # Vite configuration
├── tailwind.config.js               # Tailwind configuration
├── tsconfig.json                    # TypeScript configuration
├── components.json                  # shadcn/ui configuration
├── package.json                     # Dependencies
└── Dockerfile                       # Nginx production image
```

## Development Workflow

### Running the Development Server

```bash
# Navigate to studio directory
cd studio

# Install dependencies (first time only)
npm install

# Start development server (with hot reload)
npm run dev

# Development server runs on http://localhost:5173
# API proxy configured in vite.config.ts to point to backend
```

### Building for Production

```bash
# Build optimized production bundle
npm run build

# Output goes to studio/dist/

# Preview production build locally
npm run preview
```

### Adding shadcn/ui Components

```bash
# Add individual components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add input

# Components are added to src/components/ui/
# Automatically configured for Tailwind and TypeScript
```

## Key Components

### Layout Components

#### MainLayout.tsx
- Main application layout container
- Includes TopBar, Sidebar, and main content area
- Handles sidebar state (collapsed/expanded)
- Provides consistent layout across all pages

#### TopBar.tsx
- Top navigation bar
- Project/workspace selector
- User menu and settings
- Breadcrumb navigation

#### Sidebar.tsx
- Collapsible sidebar navigation
- Route navigation (Dashboard, Prompts, Settings, etc.)
- Active route highlighting
- Collapse/expand toggle

### Core Components

#### PromptEditor.tsx
- YAML template editor with syntax highlighting
- Live validation
- Input schema editor
- Preview functionality
- Save/cancel actions

#### PromptList.tsx
- List of templates with search/filter
- Template metadata display
- Quick actions (edit, delete, duplicate)
- Sorting and pagination

#### NewPromptDialog.tsx
- Modal dialog for creating new templates
- Form validation
- Template ID generation
- Initial structure setup

### Optimization Components

#### OptimizationProgress.tsx
- Real-time progress indicator
- Shows current optimization step
- Loading states and animations
- Cancel optimization option

#### OptimizationResults.tsx
- Side-by-side comparison view
- Original vs. optimized template
- Diff highlighting
- Insights categorized by type (clarity, specificity, efficiency)
- Token reduction metrics
- Apply/reject actions

#### OptimizationHistory.tsx
- List of past optimization runs
- Filterable by date, status
- Quick view of insights
- Re-apply previous optimizations

## Pages

### DashboardPage.tsx
- Template browser with grid/list view
- Search and filter functionality
- Quick stats (total templates, recent activity)
- Create new template button

### PromptEditPage.tsx
- Full template editing interface
- Tabbed view (Template, Execute, History)
- PromptsView for editing template content
- ExecuteView for testing with inputs
- Execution history display

### OptimizePromptPage.tsx
- Prompt optimization interface
- One-click optimization trigger
- Progress tracking
- Results comparison
- Optimization history
- Apply optimized template

### NewPromptPage.tsx
- New template creation wizard
- Template metadata form
- Initial template content
- Input schema setup
- Preview before save

## Views (Tab Components)

### PromptsView.tsx
- Template content editing tab
- YAML editor integration
- Input schema management
- Metadata editing
- Version control

### ExecuteView.tsx
- Template execution tab
- Input form generation from schema
- Model selection
- Execute button with loading states
- Output display
- Error handling
- Execution history

## API Integration

### useApi.ts Hook

Custom React hooks for API operations:

```typescript
// Prompt operations
const { prompts, loading, error, refetch } = usePrompts(projectId)
const { createPrompt, loading } = useCreatePrompt(projectId)
const { updatePrompt, loading } = useUpdatePrompt(projectId, promptId)
const { deletePrompt, loading } = useDeletePrompt(projectId, promptId)

// Execution operations
const { execute, loading, result } = useExecutePrompt(projectId, promptId)
const { executions, loading } = useExecutionHistory(projectId, promptId)

// Optimization operations
const { optimize, loading, result } = useOptimizePrompt(projectId, promptId)
const { runs, loading } = useOptimizationHistory(projectId, promptId)

// Workspace/project operations
const { workspaces, loading } = useWorkspaces()
const { projects, loading } = useProjects(workspaceId)
```

### api.ts Utilities

Core API client setup and utility functions:

```typescript
import { api } from '@/utils/api'

// API client is pre-configured with:
// - Base URL from environment
// - Error handling
// - Authentication headers
// - Response parsing

// Example usage
const prompts = await api.get(`/api/projects/${projectId}/prompts`)
const result = await api.post(`/api/projects/${projectId}/prompts`, data)
```

## Styling Guidelines

### Tailwind CSS

- Use Tailwind utility classes for all styling
- Follow shadcn/ui component patterns
- Use CSS variables for theming (defined in index.css)
- Responsive design with mobile-first approach

### Theme Configuration

Themes are defined in `index.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 222.2 47.4% 11.2%;
  /* ... more theme variables */
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* ... dark theme overrides */
}
```

### Component Styling Best Practices

1. **Use shadcn/ui components** - Consistent, accessible, themeable
2. **Compose utilities** - Use `cn()` helper for conditional classes
3. **Follow spacing scale** - Use Tailwind's spacing system (p-4, m-2, gap-6)
4. **Semantic colors** - Use theme variables instead of hardcoded colors
5. **Responsive breakpoints** - sm, md, lg, xl, 2xl

## Routing

React Router configuration in `App.tsx`:

```typescript
<Routes>
  <Route path="/" element={<MainLayout />}>
    <Route index element={<DashboardPage />} />
    <Route path="prompts/:promptId" element={<PromptEditPage />} />
    <Route path="prompts/:promptId/optimize" element={<OptimizePromptPage />} />
    <Route path="prompts/new" element={<NewPromptPage />} />
    {/* ... more routes */}
  </Route>
</Routes>
```

## State Management

- **Local component state** - useState for simple UI state
- **API state** - Custom hooks (useApi.ts) with loading/error states
- **URL state** - React Router for navigation and route params
- **Form state** - Controlled components with React Hook Form (where needed)

No global state management library needed - keep it simple.

## Build Process

### Development Build

```bash
npm run dev
# - Fast HMR (Hot Module Replacement)
# - Source maps for debugging
# - API proxy to backend (localhost:8000)
# - Port: 5173
```

### Production Build

```bash
npm run build
# - Optimized bundle
# - Code splitting
# - Minification
# - Tree shaking
# - Output: dist/
```

### Deployment

**Docker (Production):**

```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Nginx serving
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

**Server Integration:**

In production, the FastAPI server serves the built static files:

```python
# server/dakora_server/main.py
from fastapi.staticfiles import StaticFiles

# Serve Studio UI
app.mount("/", StaticFiles(directory="studio/dist", html=True), name="studio")
```

## TypeScript Guidelines

1. **Strict mode enabled** - No implicit any, strict null checks
2. **Type all props** - Use interface or type for component props
3. **Type API responses** - Define interfaces for all API data
4. **Avoid any** - Use unknown or specific types
5. **Generic components** - Use generics for reusable components

### Example Component Types

```typescript
interface PromptEditorProps {
  promptId: string
  initialContent: string
  onSave: (content: string) => Promise<void>
  onCancel: () => void
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  promptId,
  initialContent,
  onSave,
  onCancel,
}) => {
  // Component implementation
}
```

## Testing (Future)

Recommended testing setup (not yet implemented):

- **Vitest** - Fast unit testing framework
- **React Testing Library** - Component testing
- **Playwright** - E2E testing

## Common Patterns

### Error Handling

```typescript
try {
  await api.post('/api/prompts', data)
  toast.success('Prompt created successfully')
} catch (error) {
  toast.error('Failed to create prompt')
  console.error(error)
}
```

### Loading States

```typescript
const [loading, setLoading] = useState(false)

const handleSubmit = async () => {
  setLoading(true)
  try {
    await api.post('/api/prompts', data)
  } finally {
    setLoading(false)
  }
}
```

### Form Handling

```typescript
const [formData, setFormData] = useState({ name: '', description: '' })

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setFormData({ ...formData, [e.target.name]: e.target.value })
}
```

## Environment Variables

Create `.env.local` for local development:

```bash
VITE_API_URL=http://localhost:8000
```

Access in code:

```typescript
const apiUrl = import.meta.env.VITE_API_URL
```

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run dev -- --port 3001
```

### Build Fails

```bash
# Clear cache and reinstall
rm -rf node_modules dist
npm install
npm run build
```

### API Connection Issues

- Check backend is running on port 8000
- Verify proxy configuration in `vite.config.ts`
- Check CORS settings in backend
- Inspect Network tab in browser DevTools

## Best Practices

1. **Component organization** - Keep components small and focused
2. **File naming** - PascalCase for components, camelCase for utilities
3. **Import organization** - Group by type (React, libraries, local)
4. **Props destructuring** - Destructure props in function signature
5. **Event handlers** - Prefix with `handle` (handleClick, handleSubmit)
6. **Boolean props** - Prefix with `is`, `has`, `should` (isLoading, hasError)
7. **Accessibility** - Use semantic HTML, ARIA labels, keyboard navigation
8. **Performance** - Use React.memo for expensive components, useMemo/useCallback where needed

## Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [React Router Documentation](https://reactrouter.com)