# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.1]: https://github.com/bogdan-pistol/dakora/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/bogdan-pistol/dakora/releases/tag/v1.0.0