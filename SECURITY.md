# Security Policy

## Reporting a Vulnerability

Report vulnerabilities through GitHub's private vulnerability reporting for
`basefoundry/base`. Do not open a public issue with exploit details, credentials,
or secret values. If private reporting is unavailable, contact the maintainers
without including a live credential and ask for a private channel.

## Secret Detection

Base uses two enforced layers:

- GitHub secret scanning and push protection detect supported provider secrets
  and block supported secrets before they reach the repository.
- The required `Security scanners` check runs Gitleaks 8.30.1 over committed
  history to cover provider and generic secret patterns on pull requests and
  protected `main` updates.

GitHub non-provider patterns, custom patterns, and validity checks are not
available for this public repository under its current GitHub feature set.
Repository administrators can verify the native setting readback without
displaying alerts or secret values:

```bash
gh api repos/basefoundry/base \
  --jq '.security_and_analysis | {
    secret_scanning,
    secret_scanning_push_protection,
    secret_scanning_non_provider_patterns,
    secret_scanning_validity_checks
  }'
```

Run the same fallback scanner locally with the exact supported Gitleaks release:

```bash
GITLEAKS_BIN=/path/to/gitleaks-8.30.1 ./tests/scan-secrets.sh
```

The scanner fully redacts findings. For a controlled working-tree or fixture
check, use `./tests/scan-secrets.sh --dir <path>`. Do not place controlled
secret-shaped fixtures in the repository history.

Test fixtures should use unmistakably fake, narrowly scoped values. If a false
positive cannot be rewritten safely, add only its reviewed fingerprint to
`.gitleaksignore`; do not disable a rule or exclude a broad test directory.

## Responding to a Secret

Treat detection as exposure until proven otherwise:

1. Do not print, quote, copy into an issue, or otherwise redistribute the value.
2. Revoke or rotate the credential first. Removing Git history does not make a
   live credential safe.
3. Determine the affected repositories, commits, logs, artifacts, and access
   window using provider and GitHub audit evidence.
4. Remove the value from the current change. Rewrite published history only
   when the exposure warrants it, and coordinate the force push and downstream
   clone cleanup with maintainers.
5. Resolve the GitHub alert with the accurate reason only after rotation and
   remediation are complete.

Never bypass push protection merely to make a build or release proceed. A fake
fixture that must exercise detection belongs in an isolated local validation,
not in the tracked tree.
