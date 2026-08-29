#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl setup prints setup-specific help" {
    run_basectl setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on supported setup platforms."* ]]
    [[ "$output" == *"Install or verify macOS prerequisites on macOS."* ]]
    [[ "$output" == *"Install or verify apt prerequisites on Ubuntu/Debian Linux with interactive consent or --yes."* ]]
    [[ "$output" == *"--allow-project-ide-mutations"* ]]
    [[ "$output" != *"Install Homebrew if needed."* ]]
}
