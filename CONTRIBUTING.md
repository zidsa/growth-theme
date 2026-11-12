# Contributing

Thanks for helping improve the Growth theme. This page covers how changes get
from an idea to `main`.

## Before you start

- **Security issues:** follow [SECURITY.md](SECURITY.md). Do not include
  secrets, credentials or customer data in issues, PRs or screenshots.
- **Bugs and features:** open an issue first for anything bigger than a small
  fix, so the approach can be agreed before you write it.
- **Store data:** use test stores. Never copy merchant or shopper data (names,
  emails, orders) into the repo, tests or PR descriptions.

## Making a change

1. Branch from `main` with a prefix that says what the change is:
   `feat/…`, `fix/…`, `hotfix/…` (production incident), `chore/…`, `perf/…`.
2. Keep each PR to one change. Unrelated fixes go in their own PR.
3. Follow the existing structure and patterns described in
   [README.md](README.md) (templates, sections, CSS variables, JS modules,
   platform callbacks). Run `npm run format` before committing.
4. Write commit messages as `Type: Summary` in the imperative mood, for example
   `Fix: Stop empty logo URL in footer`. Use `Feat`, `Fix`, `Perf`, `Test`,
   `Chore` or `Docs`, and explain *why* in the body when it isn't obvious.

## Verification

Every PR must pass the checks in [AGENTS.md](AGENTS.md#verify-before-opening-a-pr)
for each feature group it touches (account, blog, cart, content pages, home
sections, layout, product, search/category):

- `npm ci && npm run build` and `npx playwright test`
- the group's `verify-<group>` journeys on a local vitrin storefront
- the group's `formal-<group>/check.sh`

If your change alters a group's behaviour, update that group's skills in
`.agents/skills/` in the same PR, so the recorded outcomes stay true.

## Pull requests

- Target `main`. Describe the problem, the fix, and how you verified it, and
  list any check you did not run.
- For visual changes, include before/after screenshots at mobile and desktop
  widths, in both LTR and RTL when text direction matters.
- Link the issue the PR closes (`Fixes #123`).
- At least one maintainer approval is required to merge.

**Merging to `main` deploys.** Every push to `main` (and `develop`) triggers
the theme deploy pipeline, so only merge a PR that is ready to reach live
stores.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE) that covers this repository.
