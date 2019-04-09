#!/usr/bin/env bash

trap 'rm -f -- "$tempfile"' EXIT

# run this from demo directory
source ../lib/stdlib.sh
source ./error_handling_demo_lib.sh

test_func1() {
    log_debug_enter
    log_info "Calling test_func2"
    test_func2
    exit_if_error $? "test_func2 failed"
    log_debug_leave
}

test_func2() {
    log_debug_enter
    log_info "Calling test_func3"
    test_func3; ret=$?
    log_debug_leave
    return $ret
}

test_func3() {
    log_debug_enter
    return 1
    log_debug_leave
}

main() {
    set_log_level DEBUG
    # run tests in subshell so that the parent can continue even after error handler calls exit
    (test_func1)
    (demo_lib_func)  # this is defined in error_handling_demo_lib.sh
}

main
