# Shortcut Release GitHub Action

A GitHub Action that automatically creates release notes and increments the [semver](https://semver.org/) based on [Shortcut](https://shortcut.com) stories referenced in commit messages.

This project was mostly generated by [Cursor](https://cursor.com), as a sample project while I've been exploring AI development tooling.

## Features

- Automatically detects Shortcut story IDs in commit messages (e.g., `SC-123`)
- Determines release type (major, minor, patch) based on story types
- Generates release notes from story titles
- Creates GitHub releases with appropriate versioning
- Supports custom release titles and body prefixes
- Configurable draft and prerelease flags
- Supports artifact uploads

## Usage

### Basic Usage

```yaml
name: Create Release
on:
  push:
    branches:
      - main

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Create Release
        uses: matthew/kilpatrick/shortcut-release-action@v1
        with:
          shortcut-token: ${{ secrets.SHORTCUT_TOKEN }}
```

### Advanced Usage

```yaml
name: Create Release
on:
  push:
    branches:
      - main

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Create Release
        uses: matthew-kilpatrick/shortcut-release-action@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          shortcut-token: ${{ secrets.SHORTCUT_TOKEN }}
          title: 'Major Feature Release'
          body-prefix: |
            # Release Highlights
            This release includes several important updates:
          artifacts: 'dist.zip,release-notes.pdf'
          draft: true
          prerelease: false
        id: release
      
      - name: Use Release Outputs
        run: |
          echo "New version: ${{ steps.release.outputs.version }}"
          echo "Release notes: ${{ steps.release.outputs.release-notes }}"
```

## Inputs

| Input | Type | Description | Required | Default |
|-------|------|-------------|----------|---------|
| `github-token` | `string` | GitHub token for authentication | No | `${{ github.token }}` |
| `shortcut-token` | `string` | Shortcut API token | Yes | - |
| `title` | `string` | Custom release title. If empty, uses the version | No | - |
| `body-prefix` | `string` | Text to prepend to the generated release notes | No | - |
| `artifacts` | `string` | Comma-separated list of artifacts to upload | No | - |
| `draft` | `boolean` | Whether to create the release as a draft | No | `false` |
| `prerelease` | `boolean` | Whether to mark the release as a prerelease | No | `false` |
| `create-release` | `boolean` | Whether to automatically create the GitHub release. If false, only generates version and release notes | No | `true` |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `version` | `string` | The version of the new release (e.g., "v1.2.3") |
| `release-notes` | `string` | The generated release notes from Shortcut stories |
