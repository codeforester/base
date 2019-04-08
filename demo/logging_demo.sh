#!/usr/bin/env bash

trap 'rm -f -- "$tempfile"' EXIT

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

test_file_logging() {
    tempfile=/tmp/__log_demo__.txt
    printf '%s\n' "first line" "second line" "third line" > $tempfile
    set_log_level VERBOSE
    log_info_file    "$tempfile"
    log_debug_file   "$tempfile"
    log_verbose_file "$tempfile"
    rm -f -- "$tempfile"
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
test_file_logging

print_error "This is a plain error"
print_warn  "This is a plain warning"
print_info  "This is a plain info"
