#
# base_defaults.sh
#

###
### Aliases
###
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
alias h='history'

###
### Command editing
###
set -o vi

###
### Prompt
###
export PS1='\[\033[0;35m\]\T \h\[\033[0;33m\] \w\[\033[00m\]: '

###
### Bash history
###
export HISTCONTROL=ignoredups:erasedups
export HISTTIMEFORMAT="[%F %T] "
