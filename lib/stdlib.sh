#
# stdlib.sh - foundation library for Bash scripts
#
# we cover:
#   - assertions
#   - logging
#   - error handling
#

#
# import a library from $BASE_HOME/lib
# Example:
#     import lib/logging.sh company/lib/xyz.sh ...
#
import() {
    local lib
    for lib; do
        lib=$BASE_HOME/$lib
        [[ -f "$lib" ]] && {
            source "$lib"
        } || {
            printf 'ERROR: %s\n' "Library '$lib' does not exist" >&2
        }
    done
}

#
# Print components of $PATH, one on each line
#
print_path() {
    local -a dirs
    local dir

    IFS=: read -ra dirs <<< "$PATH"
    for dir in "${dirs[@]}"; do
        printf '%s\n' "$dir"
    done
}

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
# Given a version like x.y, where x and y are numbers, asserts that
# bash version is at least x.y
#
assert_minimum_bash_version() {
  local version=$1 message=$2
  local version_array curr_version version_re='^[0-9]+\.[0-9]+$'

  assert_arg_count $# 1 "Usage: assert_minimum_bash_version version"
  assert_regex_match "$version" "$version_re" "Version should be in the format x.y where x and y are integers"
  version_array=(${version//\./ })
  ((  BASH_VERSINFO[0] < version_array[0] ||
    ((BASH_VERSINFO[0] == version_array[0] && BASH_VERSINFO[1] < version_array[1])))) && {
    curr_version="${BASH_VERSINFO[@]:0:4}"
    [[ $message ]] || message="Running with Bash version ${curr_version// /.}; need $version or above"
    printf '%s\n' "$message" >&2
    exit 1
  }
  return 0
}

#
# test code - run this to test the functions in this library
# the tests run in a sub shell and hence won't exit the main shell in case of failures
#
test_stdlib() (
  assert_minimum_bash_version "$@"
)

#
# exit if number of arguments passed doesn't meet expectations
# example call:
#    assert_arg_count $# 2 "Need exactly two arguments"
#
assert_arg_count() {
  local actual=$1 expected=$2 message=$3

  ((actual != expected)) && {
    [[ $message ]] || message="Expected $expected arguments, got $actual arguments"
    printf '%s\n' "$message" >&2
    exit 1
  }
}

assert_regex_match() {
  local string=$1 regex=$2 message=$3

  [[ $string =~ $regex ]] || {
    [[ $message ]] || message="String '$string' does not match regex '$regex'"
    printf '%s\n' "$message" >&2
    exit 1
  }
}

#
# assert if variables are set
# if any variable is not set, exit 1 (when -f option is set) or return 1 otherwise
#
# Usage: assert_not_null [-f] variable ...
#
assert_not_null() {
  local fatal var num_null=0
  [[ "$1" = "-f" ]] && { shift; fatal=1; }
  for var in "$@"; do
    [[ -z "${!var}" ]] &&
      printf '%s\n' "Variable '$var' not set" >&2 &&
      ((num_null++))
  done

  if ((num_null > 0)); then
    [[ "$fatal" ]] && exit 1
    return 1
  fi
  return 0
}

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
