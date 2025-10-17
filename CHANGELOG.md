# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2025-10-17

### Added

- Azure Blob Storage support for template registry with comprehensive tests ([#44](https://github.com/bogdan-pistol/dakora/pull/44))
- Execute tab in playground UI with multi-model comparison support ([#43](https://github.com/bogdan-pistol/dakora/pull/43))
- CLI command for multi-model comparison (`dakora compare`) ([#40](https://github.com/bogdan-pistol/dakora/pull/40))
- `dakora run` CLI command to execute templates from terminal ([#32](https://github.com/bogdan-pistol/dakora/pull/32))
- `execute()` method to TemplateHandle for single-model execution ([#31](https://github.com/bogdan-pistol/dakora/pull/31))
- LiteLLM integration for multi-provider LLM support ([#30](https://github.com/bogdan-pistol/dakora/pull/30))
- Microsoft Agent Framework integration examples ([#16](https://github.com/bogdan-pistol/dakora/issues/16))
- OpenAI Agents framework integration examples ([#29](https://github.com/bogdan-pistol/dakora/pull/29))
- API key configuration guide and improved error handling ([#33](https://github.com/bogdan-pistol/dakora/pull/33))
- Discord community links for user engagement ([#12](https://github.com/bogdan-pistol/dakora/issues/12))
- Mintlify documentation integration
- Claude Code AI agent and MCP servers for UI/UX review ([#34](https://github.com/bogdan-pistol/dakora/pull/34))

### Changed

- Redesigned playground UI with extensible Cockpit architecture ([#41](https://github.com/bogdan-pistol/dakora/pull/41))
- Moved assets from `.github/assets/` to `assets/` for GitHub Pages compatibility ([#39](https://github.com/bogdan-pistol/dakora/pull/39))
- Enhanced README and index.html with better community links and accessibility

### Fixed

- Path to assets folder in index.html ([#37](https://github.com/bogdan-pistol/dakora/pull/37))
- Scaling issues on smaller screens in playground UI ([#11](https://github.com/bogdan-pistol/dakora/pull/11))
- CSS for GitHub Pages website to fix scaling issues ([#10](https://github.com/bogdan-pistol/dakora/pull/10))

### Documentation

- Added playground UI development guide to CLAUDE.md ([#42](https://github.com/bogdan-pistol/dakora/pull/42))
- Cleaned up repository documentation and updated development guide ([#8](https://github.com/bogdan-pistol/dakora/pull/8))
- Added interactive playground with demo mode and deployment support ([#6](https://github.com/bogdan-pistol/dakora/pull/6))

## [1.0.2] - 2025-09-30

### Fixed

- Misleading error messages when running playground from PyPI installs ([#3](https://github.com/bogdan-pistol/dakora/issues/3))
- CLI now correctly detects pre-built UI and shows success message instead of "UI build failed"

## [1.0.1] - 2025-09-30

### Fixed

- Playground UI now builds fresh from source during releases, preventing stale assets ([#1](https://github.com/bogdan-pistol/dakora/issues/1))
- Release workflow now includes smoke tests to verify playground functionality before PyPI publication

### Changed

- Playground built assets are no longer tracked in git, only the directory structure (via `.gitkeep`)
- PyPI releases now include pre-built playground UI for out-of-the-box functionality
- Updated documentation to clarify installation requirements for playground feature

### Added

- Automated UI build step in release workflow
- Smoke test validation for playground server and API endpoints before release
- Hatchling configuration to properly package playground assets

## [1.0.0] - 2025-09-29

### Added

- Initial stable release
- Interactive web playground for template development
- Type-safe prompt templates with Pydantic validation
- File-based template management with YAML definitions
- Hot-reload support for development workflows
- Jinja2 templating with custom filters (`default`, `yaml`)
- Semantic versioning for templates
- Optional execution logging to SQLite
- CLI interface with commands: `init`, `list`, `get`, `bump`, `watch`, `playground`
- Thread-safe caching for production use
- FastAPI-based playground server with REST API
- Modern React UI built with shadcn/ui components
- Support for input types: string, number, boolean, array<string>, object
- Template registry pattern with local filesystem implementation
- Comprehensive test suite (unit, integration, performance)

[1.0.3]: https://github.com/bogdan-pistol/dakora/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/bogdan-pistol/dakora/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/bogdan-pistol/dakora/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/bogdan-pistol/dakora/releases/tag/v1.0.0
