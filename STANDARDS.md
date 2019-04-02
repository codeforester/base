# Standards followed in this framework

* Shell/local variables and function names follow "snake_case" - only lowercase letters, underscores, and digits.
* Environment variables use all uppercase names. For example, BASE_HOME, BASE_HOME, BASE_OS, BASE_SOURCES.
* In rare cases of global variables being shared between library functions and their callers use all uppercase names.
* Place most code inside functions.
* In libraries, have top level code that prevents the file from being sourced more than once.  For example:
    ```bash
    [[ $__stdlib_sourced__ ]] && return
    __stdlib_sourced__=1
    ```
* Make sure all local variables inside functions are declared local.
* Use __func__ naming convention for special purpose variables and functions.
* Double quote all variable expansions, except:
  - inside [[ ]] or (( ))
  - places where we need word splitting to take place

* Use [[ $var ]] to check if var has non-zero length, instead of [[ -n $var ]].
* Make sure the code passes https://shellcheck.net checks.
