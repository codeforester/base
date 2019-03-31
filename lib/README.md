## Logging example

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

## Error handling example

``` bash

    path=/path/to/required/dir
    [[ -d $path ]] || fatal_error "Directory '$path' does not exist"


    call_some_function; exit_if_error $? "Some function failed"
```
