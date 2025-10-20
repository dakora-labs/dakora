# Release Process

This document describes how to release new versions of Dakora components.

## Version Strategy

- **Platform** (CLI + Server): Synchronized versions (e.g., v2.0.0)
- **Python SDK**: Independent versioning (e.g., v1.5.0)

## Prerequisites

1. All tests passing on main branch
2. No uncommitted changes
3. PyPI API token set in GitHub secrets: `PYPI_API_TOKEN`

## Release Workflow

### Option 1: Platform Release (CLI + Server)

#### 1. Bump versions locally

```bash
# Using helper script
uv run python scripts/bump_version.py platform 2.0.0

# Or manually edit:
# - cli/pyproject.toml
# - server/pyproject.toml
```

#### 2. Test everything

```bash
# Run tests
cd server && uv run pytest tests/ -v
cd ../cli && uv run pytest tests/ -v || echo "No CLI tests yet"

# Test builds
cd cli && uv build && cd ..
cd server && uv build && cd ..

# Test Docker builds
docker build -t dakora-server-test server/
docker build -t dakora-studio-test studio/
```

#### 3. Commit and push

```bash
git add cli/pyproject.toml server/pyproject.toml
git commit -m "chore: bump platform version to 2.0.0"
git push origin main
```

#### 4. Wait for CI to pass

Check GitHub Actions → CI workflow runs and passes

#### 5. Trigger releases

**Option A: Release CLI + Docker together (recommended)**

1. Go to GitHub Actions
2. Run `Release CLI (dakora)` workflow → Enter version: `2.0.0`
3. Run `Release Docker Images` workflow → Enter version: `2.0.0`

**Option B: Release CLI only**

1. Run `Release CLI (dakora)` workflow → Enter version: `2.0.0`

#### 6. Verify releases

- PyPI: https://pypi.org/project/dakora/2.0.0/
- Docker: `docker pull ghcr.io/OWNER/dakora/server:2.0.0`
- GitHub Releases: Check tags `cli-v2.0.0` and `docker-v2.0.0`

---

### Option 2: Python SDK Release

#### 1. Bump version

```bash
# Using helper script
uv run python scripts/bump_version.py sdk 1.5.0

# Or manually edit:
# - packages/client-python/pyproject.toml
```

#### 2. Test

```bash
cd packages/client-python
uv run pytest tests/ -v
uv build
```

#### 3. Commit and push

```bash
git add packages/client-python/pyproject.toml
git commit -m "chore: bump Python SDK version to 1.5.0"
git push origin main
```

#### 4. Wait for CI, then release

1. Go to GitHub Actions
2. Run `Release Python SDK (dakora-client)` → Enter version: `1.5.0`

#### 5. Verify

- PyPI: https://pypi.org/project/dakora-client/1.5.0/

---

## Release Checklist

### Before Release

- [ ] All tests pass locally
- [ ] All tests pass in CI
- [ ] Version numbers updated in pyproject.toml files
- [ ] Platform versions are in sync (CLI == Server)
- [ ] Changelog updated (if applicable)
- [ ] Breaking changes documented

### During Release

- [ ] GitHub Actions workflow completes successfully
- [ ] Package appears on PyPI
- [ ] Docker images appear in ghcr.io
- [ ] Git tags created

### After Release

- [ ] Test installation: `pip install dakora==VERSION`
- [ ] Test SDK installation: `pip install dakora-client==VERSION`
- [ ] Test Docker: `docker pull ghcr.io/OWNER/dakora/server:VERSION`
- [ ] Update documentation if needed
- [ ] Announce release (if major version)

---

## Hotfix Process

For urgent fixes to production:

1. Create hotfix branch from release tag
2. Fix issue
3. Bump patch version (e.g., 2.0.0 → 2.0.1)
4. Follow normal release process
5. Merge back to main

---

## Rollback

If a release has critical issues:

1. **PyPI**: Cannot delete, but can yank: `twine upload --skip-existing`
2. **Docker**: Delete tag from ghcr.io or retag as `broken`
3. **GitHub**: Delete release and tag
4. Release fixed version immediately

---

## Troubleshooting

### "Version already exists on PyPI"

PyPI versions are immutable. Bump to next version.

### "Docker build fails in CI"

- Check Dockerfile syntax
- Verify all files exist in build context
- Check Docker cache issues

### "Tests fail in CI but pass locally"

- Check Python version (CI uses 3.11)
- Check environment variables
- Check file paths (absolute vs relative)

### "Version mismatch error in CI"

Ensure CLI and Server have the same version in their pyproject.toml files.