#!/usr/bin/env bash

source ../lib/stdlib.sh

demo_lib_func() {
    log_debug_enter
    exit_if_error 1 "Deliberately exiting!"
    log_debug_leave
}
