# Review PR Comments

Review the comments on the current branch's GitHub PR, assess each suggestion, and offer to apply
any that are worthwhile.

## Prerequisites

- **GitHub CLI (`gh`)** must be installed and authenticated (`gh auth status`)

## Instructions

### 1. Identify the PR

```bash
gh pr list --head "$(git branch --show-current)" --json number,title
```

If no PR is found, check `--state all` in case it's been merged/closed.

### 2. Fetch review comments

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate \
  --jq '.[] | "=== \(.user.login) on \(.path):\(.line // .original_line) ===\n\(.body)\n"'
```

Derive `{owner}/{repo}` from `git remote get-url origin`.

### 3. For each comment

1. **Read the relevant source file** at the referenced line range — include enough surrounding
   context to understand the code's intent
2. **Check related code** — look at callers, type definitions, tests, or schema if the suggestion
   involves types, contracts, or data flow
3. **Summarise the suggestion** — one or two sentences explaining what the reviewer is asking for
4. **Assess whether it's necessary** — consider:
   - Does the current code have an actual bug or latent failure mode?
   - Is the suggestion purely defensive against a scenario that can't happen in the current design?
   - Does it improve clarity or correctness at a reasonable cost, or add unnecessary complexity?
   - Does it conflict with project conventions in `copilot-instructions.md`?
5. **Give a verdict** — "Yes, worth taking" or "No, not necessary" with a brief rationale

### 4. Offer to apply

After reviewing all comments, offer to apply the worthwhile changes. When applying:

- Make the minimal change that addresses the concern
- Run the relevant tests to verify nothing breaks
- Do not apply suggestions you assessed as unnecessary unless the user asks
