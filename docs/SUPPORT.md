# Support

How to get help with Helios.

## I have a question about installation or setup

Read `docs/INSTALLATION.md` first — most common issues are covered there. Pay particular attention to §9 Common issues.

If still stuck:

1. Search [GitHub Issues](https://github.com/Golden007-prog/Helios/issues) for similar reports.
2. If none, open a new issue with the **Question** template. Include:
   - Your OS and version
   - Output of `python --version`, `node --version`, `git --version`
   - The exact command you ran and the exact error (full traceback, not a summary)
   - Your `request_id` from the failed response if applicable

We aim to respond within two business days during the hackathon period.

## I think I found a bug

Open a GitHub Issue with the **Bug** template. Reproducer first, theory second.

## I want to suggest a feature

Open a GitHub Issue with the **Phase 2 ask** or **Phase 3 ask** template. We use the phase tagging to triage against `docs/ROADMAP.md`.

## I found a security vulnerability

**Do not file a public issue.** Read `docs/SECURITY.md` for the responsible-disclosure email address.

## I want to contribute code

Read `CONTRIBUTING.md` for the workflow and `docs/WORKFLOW.md` for the branch naming, PR template, and review process. Look for issues tagged `good-first-issue`.

## I want to use Helios in my company

Phase 1 is Apache 2.0 — use it as you wish. We'd love to hear how it goes; open a GitHub Discussion under "Show and tell."

## I want to commercially deploy Helios at scale

Reach out via the email in `docs/SECURITY.md`. Phase 2 features (SSO, encryption keys, notification fan-out) make a meaningful pilot possible; we can talk through what your shop needs.

## What we will NOT do

- Provide phone or pager support during the hackathon — we are building.
- Provide custom development on request without a commercial conversation.
- Triage issues that are configuration problems with your IBM Cloud account — please contact IBM Cloud support for those.
- Reproduce issues against your private mainframe data without an arrangement.

## Self-help references

| If you want to... | Read... |
|---|---|
| Understand what Helios is | `README.md`, `docs/PROBLEM_STATEMENT.md` |
| Learn the mainframe terms used in the docs | `docs/GLOSSARY.md` |
| Know how the API works | `docs/API.md` |
| Know how the data is stored | `docs/DATA_MODEL.md` |
| Set up Bob IDE with the right MCP servers | `docs/MCP_SETUP.md` |
| Run the demo locally | `docs/INSTALLATION.md` + `docs/DEMO_SCRIPT.md` |
| Validate your install | `docs/TESTING.md` §2 |
| Decide if Helios fits your shop | `docs/PERSONA_MAYA.md` + `docs/FAQ.md` |
| See what's coming next | `docs/ROADMAP.md` |

## Office hours (post-hackathon)

If Phase 2 conversations begin, we'll post weekly office hours in GitHub Discussions. Until then, async via Issues.
