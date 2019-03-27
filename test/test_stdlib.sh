import lib/stdlib.sh

test_log_func() {
    local level=$1 func=$2 expected=$3 log rc=0
    set_log_level "$level"
    log=$(log_$func "test $level" 2>&1)
    if ((expected)) && ! [[ $log ]]; then
        printf 'Log level %-7s function %-11s: %s\n' "$level" "log_$func" FAIL
        ((fail++))
    else
        ((verbose)) && printf 'Log level %-7s function %-11s: %s\n' "$level" "log_$func" SUCCESS
    fi
}

test_logging() {
    local rc

    fail=0 verbose=0 rc=0
    test_log_func ERROR error   1
    test_log_func ERROR warn    0
    test_log_func ERROR info    0
    test_log_func ERROR debug   0
    test_log_func ERROR verbose 0

    test_log_func WARN  error   1
    test_log_func WARN  warn    1
    test_log_func WARN  info    0
    test_log_func WARN  debug   0
    test_log_func WARN  verbose 0

    test_log_func INFO  error   1
    test_log_func INFO  warn    1
    test_log_func INFO  info    1
    test_log_func INFO  debug   0
    test_log_func INFO  verbose 0

    test_log_func DEBUG error   1
    test_log_func DEBUG warn    1
    test_log_func DEBUG info    1
    test_log_func DEBUG debug   1
    test_log_func DEBUG verbose 0

    test_log_func VERBOSE error   1
    test_log_func VERBOSE warn    1
    test_log_func VERBOSE info    1
    test_log_func VERBOSE debug   1
    test_log_func VERBOSE verbose 1

    ((fail)) && rc=1
    exit $rc
}

test_logging
