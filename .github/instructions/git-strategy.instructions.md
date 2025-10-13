---
applyTo: '**'
---
When suggesting code changes, commits, or branches:
- Always use branch names prefixed with 'feature/', 'bugfix/', or 'chore/' (e.g., 'feature/add-user-auth', 'bugfix/fix-login-error', 'chore/update-deps').
- Ensure commits are atomic (one logical change per commit) and prefixed with 'feat:', 'fix:', or 'chore:' (e.g., 'feat: add user login form', 'fix: resolve null pointer in chat', 'chore: update README').
- Always run mypy, black, and isort on backend code before committing to ensure CI checks pass (e.g., 'python -m mypy backend --ignore-missing-imports', 'python -m black backend', 'python -m isort backend --profile black').
- NEVER bypass CI/CD checks or pre-commit hooks under any circumstances. All code must pass quality checks before merging.
- Fix all mypy type errors, formatting issues, and import sorting before pushing to ensure CI/CD pipeline success.
- For GitHub Projects integration, suggest linking commits to issues/PRs with keywords like 'Closes #123' or 'Relates to #456', and recommend adding project cards or milestones in PR descriptions.
- Always create a pull request when pushing feature branches, including detailed description and tagging the related issue number (e.g., "Closes #123").
- Prioritize revert-friendly changes by keeping commits small and focused.
- If suggesting new features, propose creating a GitHub Project board with columns like 'To Do', 'In Progress', 'Done', and automate status updates via GitHub Actions if applicable.
- Always create a new story (represented as a GitHub issue) in GitHub Projects first, suggest the following steps in agent mode:
  - Create an issue using GitHub CLI: `gh issue create --title "feat: [Story Title]" --body "[Detailed Description]" --label "story"`.
  - Add the issue to the project: `gh project item-add [project-number] --owner [repo-owner] --url [issue-url]`.
  - Suggest a corresponding branch name (e.g., 'feature/implement-story') and atomic commits (e.g., 'feat: add story implementation').
  - Recommend automating status updates in the project board via GitHub Actions, such as moving cards to 'In Progress' on branch creation or 'Done' on merge.
