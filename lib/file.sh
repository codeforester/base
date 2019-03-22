##
## file related functions
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
