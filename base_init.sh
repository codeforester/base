#
# base_init.sh: top level script that should be sourced in, especially inside .bash_profile
#

[[ -f $HOME/.base_debug ]] && export BASE_DEBUG=1
base_debug() { [[ $BASE_DEBUG ]] && printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "DEBUG ${BASH_SOURCE[0]}:${BASH_LINENO[1]} $@" >&2; }
base_error() {                      printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "ERROR ${BASH_SOURCE[0]}:${BASH_LINENO[1]} $@" >&2; }

set_base_home() {
    script=$HOME/.baserc
    [[ -f $script ]] && [[ ! $_baserc_sourced ]] && {
        base_debug "Sourcing $script"
        source "$script"
        _baserc_sourced=1
    }

    # set BASE_HOME to default in case it is not set
    [[ -z $BASE_HOME ]] && {
        local dir=$HOME/git/base
        base_debug "BASE_HOME not set; defaulting it to '$dir'"
        BASE_HOME=$dir
    }

    export BASE_HOME
}

#
# source in stdprofile.sh and stdlib.sh
#
import_libs_and_profiles() {
    local lib bin team
    for lib in $BASE_HOME/lib/stdprofile.sh \
               $BASE_HOME/lib/stdlib.sh; do
        [[ -f $lib ]] && { base_debug "Sourcing $lib" >&2; source "$lib"; }
    done

    lib=$BASE_HOME/user/$USER.sh
    [[ -f $lib ]] && ((_interactive)) && { base_debug "[interactive] Sourcing $lib" >&2; source "$lib"; }

    #
    # team specific actions
    #
    # Users choose teams by setting the "BASE_TEAM" variable in their user specific startup script
    # For example: BASE_TEAM=teamX
    #
    # Users can also set "BASE_SHARED_TEAMS" to more teams so as to share from those teams.
    # For example: BASE_SHARED_TEAMS="teamY teamZ"
    #
    # We source the team specific startup script add the team bin directory to PATH, in the same order
    #
    for team in $BASE_TEAM $BASE_SHARED_TEAMS; do
        lib=$BASE_HOME/team/$team/lib/bashrc
        [[ -f $lib ]] && ((_interactive)) && { base_debug "[interactive] Sourcing $lib" >&2; source "$lib"; }

        lib=$BASE_HOME/team/$team/lib/$team.sh
        [[ -f $lib ]] && { base_debug "Sourcing $lib" >&2; source "$lib"; }

        bin=$BASE_HOME/team/$team/bin
        [[ -d $bin ]] && add_to_path "$bin"
    done
}

main() {
    [[ $- = *i* ]] && _interactive=1 || _interactive=0

    set_base_home
    if [[ -d $BASE_HOME ]]; then
        import_libs_and_profiles   
        add_to_path "$BASE_HOME/bin" "$BASE_HOME/company/bin"
        dedupe_path
    else
        base_error "BASE_HOME '$BASE_HOME' is not a directory or is not accessible"
    fi
}

main
