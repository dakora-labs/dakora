# Dakora Documentation

This directory contains the Mintlify documentation for Dakora.

## Structure

- `mint.json` - Mintlify configuration
- `introduction.mdx` - Landing page
- `quickstart.mdx` - Quick start guide
- `installation.mdx` - Installation instructions
- `concepts/` - Core concepts
- `features/` - Feature documentation
- `api-reference/` - API documentation
- `examples/` - Code examples
- `guides/` - How-to guides

## Local Development

Install Mintlify CLI:

```bash
npm i -g mintlify
```

Preview docs locally:

```bash
cd docs
mintlify dev
```

## Deployment

Mintlify automatically deploys when you push to GitHub. Connect your repository at https://mintlify.com/dashboard

## Adding Pages

1. Create a new `.mdx` file in the appropriate directory
2. Add frontmatter with `title` and `description`
3. Add the page to `navigation` in `mint.json`

## Components

Mintlify supports built-in components:

- `<Card>` - Clickable cards
- `<CardGroup>` - Card containers
- `<CodeGroup>` - Tabbed code blocks
- `<Tabs>` - Content tabs
- `<Accordion>` - Collapsible sections
- `<Steps>` - Numbered steps
- `<Warning>`, `<Info>`, `<Tip>` - Callouts

See https://mintlify.com/docs/components for full list.
