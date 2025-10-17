# Contributing to QuietStories

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

QuietStories uses a **two-branch workflow**:
- **`main` branch**: Stable, production-ready code
- **`dev` branch**: Active development and integration branch

**Contribution Workflow:**

1. Fork the repo and create your branch from **`dev`** (not `main`)
2. Name your branch with a prefix: `feature/name`, `bugfix/name`, or `chore/name`
3. If you've added code that should be tested, add tests
4. If you've changed APIs, update the documentation
5. Ensure the test suite passes
6. Make sure your code lints (pre-commit hooks will help)
7. Create a pull request to merge into **`dev`**

For more details on our branching strategy and release process, see [RELEASE.md](./RELEASE.md).

## Pull Request Process

1. Create your feature branch from `dev` (not `main`)
2. Update the README with details of changes to the interface, if applicable
3. Follow the existing coding style (see below)
4. Ensure all tests pass and code quality checks pass
5. Create a pull request targeting the **`dev`** branch
6. The PR will be merged once you have the sign-off of at least one maintainer

**Note:** Only maintainers merge from `dev` to `main` during releases.

## Code Style

This project uses:
- **Python**: Black for formatting, isort for import sorting, mypy for type checking
- **TypeScript/JavaScript**: ESLint and Prettier for formatting
- **Commits**: [Conventional Commits](https://conventionalcommits.org/) format

### Setting up pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

This will run Black, isort, mypy, and other checks automatically before each commit.

## License

By contributing, you agree that your contributions will be licensed under the same license as the original project.

## Report bugs using GitHub's [issue tracker](https://github.com/AB-Law/QuietStories/issues)

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports.

## Use a Consistent Coding Style

This project uses automated code quality checks to ensure consistent code standards:

- **Black**: Code formatting (88 character line length)
- **isort**: Import sorting (compatible with Black)
- **mypy**: Static type checking
- **Frontend Build**: TypeScript compilation and Vite build check

## License

By contributing your code, you agree to license your contribution under the [MIT License](LICENSE).

## References

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md).
