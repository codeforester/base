#
# networking related functions
#

#
# check if $1 is a valid IPV4 address; return 0 if true, 1 otherwise
#
validate_ip4() {
  local arr element
  IFS=. read -r -a arr <<< "$1"
  [[ ${#arr[@]} != 4 ]] && return 1
  for element in "${arr[@]}"; do
    [[ (! $element =~ ^[0-9]+$) ||
          $element =~ ^0[1-9]+$
    ]] && return 1
    ((element < 0 || element > 255)) && return 1
  done
  return 0
}
