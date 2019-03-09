BASE_TEAM=test-team1
BASE_SHARED_TEAMS=test-team2

import lib/base_defaults.sh

#
# generic aliases
#
alias mv='mv -i'
alias cp='cp -i'
alias rm='rm -i'
alias h='history'
alias l='ls -ltr'

#
# refresh base
#
base_update
