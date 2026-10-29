# Working rules for this repo

- **Start of every session:** read `HANDOFF.md`, then check `git status`/`git log` and the repo itself
  before trusting it; fix any drift you find.
- **After every task, before the final reply:** update `HANDOFF.md` with what actually happened
  (section M at the top, plus status, feature tracker, tests, bugs, backlog as relevant). Record
  failures and partial work too. Never write secrets into it.
- **Final reply format:** Completed / Files changed / Verification / Remaining / Handoff (which
  sections changed).
- Don't commit, push, deploy or publish unless the task authorises it.
- Tests: `npm run test:db`; `cd analytics && .venv/Scripts/python -m pytest -q`;
  `cd apps/mobile && npx tsc --noEmit`.
