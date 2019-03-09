declare -A _shopt_restore
shopt_set() {
    local opt count
    for opt; do
        if ! shopt -q "$opt"; then
            echo "$opt not set, setting it"
            shopt -s "$opt"
            _shopt_restore[$opt]=1
            ((count++))
        else
            echo "$opt set already"
        fi
    done
}

shopt_restore() {
    local opt
    for opt; do
        [[ ${_shopt_restore[$opt]} ]] && {
            echo "unsetting $opt"
            shopt -u "$opt"
            unset _shopt_restore[$opt]
        } || {
            echo "$opt wasn't changed earlier"
        }
    done
}
