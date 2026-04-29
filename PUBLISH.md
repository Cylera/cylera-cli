# Publishing to PyPI

This document describes how to build and publish `cylera` to PyPI.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed
- PyPI account with access to the `cylera` package
- A PyPI API token (create one at https://pypi.org/manage/account/token/)

## Steps

### 1. Update the version

Edit the version in `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

Follow [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

### 2. Run the full test suite

Ensure all checks pass before publishing:

```bash
./test.sh --use-op
```

### 3. Build the package

```bash
uv build
```

This produces two artifacts in `dist/`:

- `cylera-<version>-py3-none-any.whl` — wheel
- `cylera-<version>.tar.gz` — source distribution

### 4. Publish to PyPI

The PyPI API token is required to publish. This secret, with a key `UV_PUBLISH_TOKEN`, is managed in 1Password.

```bash
op run --environment "$OP_ENVIRONMENT_ID" -- uv publish
```

### 5. Verify the release

Verification can be performed as follows - set the version number to be what you set earlier in the pyproject.toml file.

```bash
uvx --from cylera-cli@1.1.0 cylera
```

## Checklist

- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG` / commit history reflects the changes
- [ ] All tests and quality checks pass (`./test.sh`)
- [ ] `dist/` artifacts built with `uv build`
- [ ] Published with `uv publish`
- [ ] Release verified by installing from PyPI
