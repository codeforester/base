#!/usr/bin/env bash

# Shared Homebrew installer policy and execution helpers.
#
# First-mile callers may source this file when the Base checkout is available.
# bootstrap.sh and install.sh retain a standalone fallback for the case where
# the script was downloaded before the repository exists locally.

[[ -n "${_base_homebrew_install_sourced:-}" ]] && return 0
_base_homebrew_install_sourced=1
readonly _base_homebrew_install_sourced

base_homebrew_run_verified_installer() {
    local installer_url="$1"
    local expected_sha256="$2"
    local fetch_fn="$3"
    local fatal_fn="$4"
    local installer_file
    local checksum
    local actual_sha256
    local exit_code

    installer_file="$(mktemp "${TMPDIR:-/tmp}/base-homebrew-installer.XXXXXX")" || {
        "$fatal_fn" "Failed to create a temporary Homebrew installer file."
        return 1
    }
    "$fetch_fn" "$installer_url" "$installer_file" || {
        rm -f "$installer_file"
        "$fatal_fn" "Failed to read pinned Homebrew installer content from '$installer_url'."
        return 1
    }

    command -v shasum >/dev/null 2>&1 || {
        rm -f "$installer_file"
        "$fatal_fn" "shasum is required to verify pinned Homebrew installer content."
        return 1
    }
    checksum="$(shasum -a 256 "$installer_file")" || {
        rm -f "$installer_file"
        "$fatal_fn" "Failed to compute Homebrew installer checksum."
        return 1
    }
    actual_sha256="${checksum%% *}"
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        rm -f "$installer_file"
        "$fatal_fn" "Homebrew installer checksum mismatch (expected $expected_sha256, got $actual_sha256)."
        return 1
    fi

    /bin/bash "$installer_file"
    exit_code=$?
    rm -f "$installer_file"
    if ((exit_code)); then
        "$fatal_fn" "Homebrew installer failed."
        return 1
    fi
}

base_homebrew_run_mutable_installer() {
    local installer_url="$1"
    local fatal_fn="$2"
    local installer

    command -v curl >/dev/null 2>&1 || {
        "$fatal_fn" "curl is required to install Homebrew."
        return 1
    }
    installer="$(curl -fsSL "$installer_url")" || {
        "$fatal_fn" "Failed to download the Homebrew installer."
        return 1
    }
    /bin/bash -c "$installer" || {
        "$fatal_fn" "Homebrew installer failed."
        return 1
    }
}

base_homebrew_set_dry_run_result() {
    local result_var="$1"

    [[ -n "$result_var" ]] || return 0
    printf -v "$result_var" '%s' brew
}

base_homebrew_install() {
    local installer_url="$1"
    local installer_sha256="$2"
    local dry_run="$3"
    local pinned_selected="$4"
    local pinned_url_selected="$5"
    local pinned_sha256_selected="$6"
    local log_fn="$7"
    local fatal_fn="$8"
    local mutable_policy_fn="$9"
    local fetch_fn="${10}"
    local mutable_runner_fn="${11}"
    local result_var="${12:-}"

    "$log_fn" "Installing Homebrew."
    if [[ "$pinned_selected" == true ]]; then
        [[ "$pinned_url_selected" == true && "$pinned_sha256_selected" == true &&
            -n "$installer_url" && -n "$installer_sha256" ]] || {
            "$fatal_fn" "Pinned Homebrew installer URL and SHA-256 are both required."
            return 1
        }
        "$log_fn" "Using pinned Homebrew installer from $installer_url."
        if [[ "$dry_run" == true ]]; then
            "$log_fn" "[DRY-RUN] Would verify Homebrew installer SHA-256 $installer_sha256"
            "$log_fn" "[DRY-RUN] Would run: /bin/bash <verified Homebrew installer from $installer_url>"
            base_homebrew_set_dry_run_result "$result_var"
            return 0
        fi
        base_homebrew_run_verified_installer "$installer_url" "$installer_sha256" "$fetch_fn" "$fatal_fn"
        return $?
    fi

    "$mutable_policy_fn"
    if [[ "$dry_run" == true ]]; then
        "$log_fn" "[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from $installer_url>"
        base_homebrew_set_dry_run_result "$result_var"
        return 0
    fi

    "$mutable_runner_fn" "$installer_url" "$fatal_fn"
}
