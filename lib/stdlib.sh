###
### stdlib.sh - foundation library for Bash scripts
###

#
# import a library from $BASE_HOME/lib
# Example:
#     import lib/assertions.sh company/lib/xyz.sh ...
#
import() {
    local lib rc=0
    for lib; do
        lib=$BASE_HOME/$lib
        [[ -f "$lib" ]] && {
            source "$lib"
        } || {
            printf 'ERROR: %s\n' "Library '$lib' does not exist" >&2
            rc=1
        }
    done
    return $rc
}

##
## PATH related functions
##

# add a new directory to $PATH
add_to_path() {
    local dir re prepend=0 opt strict=1

    OPTIND=1
    while getopts sp opt; do
        case "$opt" in
            n)  strict=0  ;;  # don't care if directory exists or not before adding it to PATH
            p)  prepend=1 ;;  # prepend the directory to PATH instead of appending
            *)  log_error "add_to_path - invalid option '$opt'"
                return
                ;;
        esac
    done

    shift $((OPTIND-1))
    for dir; do
        ((strict)) && [[ ! -d $dir ]] && continue
        re="(^$dir:|:$dir:|:$dir$)"
        if ! [[ $PATH =~ $re ]]; then
            ((prepend)) && PATH="$dir:$PATH" || PATH="$PATH:$dir"
        fi
    done
}

# remove duplicates in $PATH
dedupe_path() {
    PATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PATH}))')"
}

# print directories in $PATH, one per line
print_path() {
    local -a dirs
    local dir

    IFS=: read -ra dirs <<< "$PATH"
    for dir in "${dirs[@]}"; do
        printf '%s\n' "$dir"
    done
}

##
## Logging
##

dump_trace() {
    local frame=0
    while caller "$frame"; do
        ((frame++))
    done
    printf '%s\n' "$@"
}

exit_if_error() {
    (($#)) || return
    local num_re='^[0-9]+'
    local rc=$1; shift
    [[ $rc =~ $num_re ]] || return
    ((rc)) && {
        dump_trace "$@"
    }
}

#
# map log level strings (FATAL, ERROR, etc.) to numeric values
#
unset _log_levels _loggers_level_map
declare -gA _log_levels _loggers_level_map
_log_levels=([FATAL]=0 [ERROR]=1 [WARN]=2 [INFO]=3 [DEBUG]=4 [VERBOSE]=5)

#
# hash to map loggers to their log levels
# the default logger "default" has INFO as its default log level
#
_loggers_level_map["default"]=3  # the log level for the default logger is INFO

#
# set_log_level
#
set_log_level() {
    local logger=default in_level l
    [[ $1 = "-l" ]] && { logger=$2; shift 2 2>/dev/null; }
    in_level="${1:-INFO}"
    if [[ $logger ]]; then
        l="${_log_levels[$in_level]}"
        if [[ $l ]]; then
            _loggers_level_map[$logger]=$l
        else
            printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "WARN ${BASH_SOURCE[0]}:${BASH_LINENO[1]} Unknown log level '$in_level' for logger '$logger'; setting to INFO"
            _loggers_level_map[$logger]=3
        fi
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "WARN ${BASH_SOURCE[0]}:${BASH_LINENO[1]} Option '-l' needs an argument" >&2
    fi
}

log_execute() {
  local level=${1:-INFO}
  if (( $1 >= ${_log_levels[$level]} )); then
    "${@:2}" >/dev/null
  else
    "${@:2}"
  fi
}

#
# logging function
#
_print_log() {
    local in_level=$1; shift
    local logger=default log_level_set log_level
    [[ $1 = "-l" ]] && { logger=$2; shift 2; }
    log_level="${_log_levels[$in_level]}"
    log_level_set="${_loggers_level_map[$logger]}"
    if [[ $log_level_set ]]; then
        ((log_level_set >= log_level)) && printf '%(%Y-%m-%d:%H:%M:%S)T %s %s\n' -1 "$in_level ${BASH_SOURCE[2]}:${BASH_LINENO[1]}" "$@" >&2
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "WARN ${BASH_SOURCE[0]}:${BASH_LINENO[1]} Unknown logger '$logger'" >&2
    fi
}

#
# shortcut functions for each log level
#
log_fatal()   { _print_log FATAL   "$@"; }
log_error()   { _print_log ERROR   "$@"; }
log_warn()    { _print_log WARN    "$@"; }
log_info()    { _print_log INFO    "$@"; }
log_debug()   { _print_log DEBUG   "$@"; }
log_verbose() { _print_log VERBOSE "$@"; }

#
# functions for logging command output
#
_print_log_file()   {
    local in_level=$1; shift
    local logger=default log_level_set log_level file
    [[ $1 = "-l" ]] && { logger=$2; shift 2; }
    file=$1
    log_level="${_log_levels[$in_level]}"
    log_level_set="${_loggers_level_map[$logger]}"
    if [[ $log_level_set ]]; then
        if ((log_level_set >= log_level)) && [[ -f $file ]]; then
            log_debug "=== file output start ==="
            cat "$1"
            log_debug "=== file output end ==="
        fi
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "WARN ${BASH_SOURCE[0]}:${BASH_LINENO[1]} Unknown logger '$logger'" >&2
    fi
}

log_debug_file()   { _print_log_file DEBUG "$@";   }
log_verbose_file() { _print_log_file VERBOSE "$@"; }

##
## file related
##
dirname2() {
  local path=$1
  [[ $path =~ ^[^/]+$ ]] && dir=. || {              # if path has no slashes, set dir to .
    [[ $path =~ ^/+$ ]]  && dir=/ || {              # if path has only slashes, set dir to /
      local IFS=/ dir_a i
      read -ra dir_a <<< "$path"                    # read the components of path into an array
      dir="${dir_a[0]}"
      for ((i=1; i < ${#dir_a[@]}; i++)); do        # strip out any repeating slashes
        [[ ${dir_a[i]} ]] && dir="$dir/${dir_a[i]}" # append unless it is an empty element
      done
    }
  }

  [[ $dir ]] && printf '%s\n' "$dir"                # print only if not empty
}
