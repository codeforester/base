#!/usr/bin/env bats

load ./test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_RUNTIME_HOME="$TEST_TMPDIR/base"
    mkdir -p "$TEST_RUNTIME_HOME/lib/base"
    cp "$BASE_REPO_ROOT/lib/base/base_cli_runtime.sh" "$TEST_RUNTIME_HOME/lib/base/"
}

@test "base_cli runtime prefers a sibling base-cli checkout" {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli"
    touch "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py"

    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            printf "%s %s\n" "$(base_cli_runtime_source_kind)" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "sibling $TEST_RUNTIME_HOME/../base-cli/lib/python" ]
}

@test "base_cli runtime uses an explicit source directory before sibling checkout" {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli" "$TEST_TMPDIR/explicit/base_cli"
    touch "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py" "$TEST_TMPDIR/explicit/base_cli/__init__.py"

    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/explicit" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            printf "%s %s\n" "$(base_cli_runtime_source_kind)" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "explicit $TEST_TMPDIR/explicit" ]
}

@test "base_cli runtime reports pip when no source checkout exists" {
    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            base_cli_runtime_prepare
            printf "%s %s\n" "${BASE_CLI_SOURCE}" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "pip " ]
}

@test "base_cli runtime rejects malformed explicit source directories" {
    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/missing" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            base_cli_runtime_source_root
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"does not contain base_cli/__init__.py"* ]]
}
