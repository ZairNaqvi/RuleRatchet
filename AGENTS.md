# RuleRatchet

Rules for any agent working in this repository. They override the host's defaults. Each rule names the check that enforces it.

- Run `scripts/setup.sh` once after cloning. It installs `scripts/hooks/commit-msg` and `scripts/hooks/pre-push` into this clone only.
- Commit messages and pull request bodies carry no attribution line of any kind: no `Co-Authored-By`, no "Generated with", no agent trailer. Enforced by `scripts/hooks/commit-msg` and the "Commit and PR body rules" job in `.github/workflows/ci.yml`.
- The author and committer are always Zair Naqvi. Enforced by `scripts/hooks/commit-msg`.
- Commit subjects are imperative, capitalized, at most 72 characters. Enforced by `scripts/hooks/commit-msg`.
- Push branches and open pull requests; never push to `main`. Enforced by `scripts/hooks/pre-push`.
- No emojis anywhere. Enforced by `scripts/hooks/commit-msg` and the CI job.
- No employer or client names anywhere, in any commit. Enforced by the CI job against the banned-word list.
- The tool makes no network call and never calls a model; a change that adds either is a design change for the maintainer, not a fix.
- Run `python3 -m unittest discover tests` before committing. Enforced by the "Tests" job in `.github/workflows/ci.yml`.
