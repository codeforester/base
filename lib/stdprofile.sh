#
# stdprofile.sh
#
# standard profile for Bash environments
# to be sourced in from .bashrc or .bash_profile
#

###
### Set env variables
###
export BASE_OS=$(uname -s)
export BASE_HOST=$(hostname -s)

###
### PATH related
###

add_to_path() {
    local dir re

    for dir; do
        re="(^$dir:|:$dir:|:$dir$)"
        if ! [[ $PATH =~ $re ]]; then
            PATH="$PATH:$dir"
        fi
    done
}

dedupe_path() {
    base_debug "PATH before dedupe: [$PATH]"
    PATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PATH}))')"
    base_debug "PATH after dedupe: [$PATH]"
}

###
### Other functions
###

base_update() (
    [[ -d $BASE_HOME ]] && {
        cd "$BASE_HOME"
        git pull --rebase
    }
)
