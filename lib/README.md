## Logging examples

### Basic logging

``` bash
    source stdlib.sh

    SECONDS=0
    log_info "Program started"

    # set the default logger to DEBUG
    set_log_level DEBUG

    log_debug "Running step 1"
    # code for step 1

    log_info  "Program finished, elapsed time = $SECONDS seconds"
```

### Multiline logs

```
    # Pass each log line as a separate argument
    log_info "This is a multi-line log" "This is the second line" "This is the last line"

    # store log lines in an array and pass the array to the logging function
    log_lines=("log line 1" "log line 2" "log line 3")
    log_debug "${log_lines[@]}"
```

## Error handling example

``` bash
    source stdlib.sh

    path=/path/to/required/dir
    [[ -d $path ]] || fatal_error "Directory '$path' does not exist"


    call_some_function; exit_if_error $? "Some function failed"
```
