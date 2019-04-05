# Standards followed in this framework

 0. Use four spaces for indentation. No tabs.
 1. Shell/local variables and function names follow "snake_case" - only lowercase letters, underscores, and digits.
 2. Environment variables use all uppercase names. For example, BASE_HOME, BASE_HOST, BASE_OS, BASE_SOURCES.
 3. In rare cases of global variables being shared between library functions and their callers, use all uppercase names.
 4. Place most code inside functions.
 5. In libraries, have top level code that prevents the file from being sourced more than once.  For example:
    ```bash
    [[ $__stdlib_sourced__ ]] && return
    __stdlib_sourced__=1
    ```
 6. Make sure all local variables inside functions are declared local.
 7. Use __func__ naming convention for special purpose variables and functions.
 8. Double quote all variable expansions, except:
      - inside [[ ]] or (( ))
      - places where we need word splitting to take place

 9. Use [[ $var ]] to check if var has non-zero length, instead of [[ -n $var ]].
10. Use "compact" style for if statements and loops:
    ```bash
    if condition; then
        ...
    fi

    while condition; do
    ...
    done

    for ((i=0; i < limit; i++)); do
    ...
    done
    ```
11. Make sure the code passes https://shellcheck.net checks.
