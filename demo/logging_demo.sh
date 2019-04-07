#!/usr/bin/env bash

# run this from demo directory
source ../lib/stdlib.sh

test_func() {
    set_log_level VERBOSE
    log_info_enter
    log_debug_enter
    log_verbose_enter

    log_info_leave
    log_debug_leave
    log_verbose_leave
}

set_log_level DEBUG
log_verbose "This verbose log won't print"
log_debug   "This is a debug log"
log_info    "This is an info log"
log_warn    "This is a warning"
log_error   "This is an error"
log_fatal   "This is a fatal error"

set_log_level VERBOSE
log_verbose "This is a verbose log"

set_log_level WARN
log_verbose "This verbose log won't print"
log_debug   "This debug log won't print"
log_info    "This info log that won't print"
log_warn    "This is a warning"

test_func
