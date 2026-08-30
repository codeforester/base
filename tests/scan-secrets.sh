#!/usr/bin/env bash

# Keep the fallback scanner deterministic across local and hosted validation.
GITLEAKS_REQUIRED_VERSION="8.30.1"
readonly GITLEAKS_REQUIRED_VERSION

usage() {
    cat <<'EOF'
Usage:
  tests/scan-secrets.sh
  tests/scan-secrets.sh --dir <path>

Scan committed repository history by default. Use --dir only for a controlled
working-tree or fixture scan. Findings are always fully redacted.
EOF
}

gitleaks_bin="${GITLEAKS_BIN:-}"
if [[ -z "$gitleaks_bin" ]]; then
    gitleaks_bin="$(command -v gitleaks 2>/dev/null || true)"
fi
if [[ -z "$gitleaks_bin" || ! -x "$gitleaks_bin" ]]; then
    printf 'ERROR: gitleaks %s is required for secret scanning.\n' \
        "$GITLEAKS_REQUIRED_VERSION" >&2
    printf 'Install that release or set GITLEAKS_BIN to its executable path.\n' >&2
    exit 1
fi

version_output=""
if version_output="$($gitleaks_bin version 2>/dev/null)"; then
    :
else
    printf 'ERROR: Could not determine the gitleaks version.\n' >&2
    exit 1
fi
if [[ "$version_output" != "$GITLEAKS_REQUIRED_VERSION" ]]; then
    printf 'ERROR: gitleaks %s is required; found %s.\n' \
        "$GITLEAKS_REQUIRED_VERSION" "$version_output" >&2
    exit 1
fi

scan_status=0
case "${1:-}" in
    "")
        "$gitleaks_bin" git --redact=100 --no-banner --no-color --verbose . ||
            scan_status=$?
        ;;
    --dir)
        if [[ -z "${2:-}" || -n "${3:-}" ]]; then
            usage >&2
            exit 2
        fi
        if [[ ! -e "$2" ]]; then
            printf "ERROR: Secret scan path does not exist: %s\n" "$2" >&2
            exit 1
        fi
        "$gitleaks_bin" dir --redact=100 --no-banner --no-color --verbose "$2" ||
            scan_status=$?
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

exit "$scan_status"
