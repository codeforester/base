#
# base_defaults.sh
#

###
### Aliases
###
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

###
### Command editing
###
set -o vi
export EDITOR=vi

###
### vi/vim
###
export EXINIT="set ts=4 sw=4 ai nows nosm expandtab"

###
### Prompt
###
export PS1='\[\033[0;35m\]\T \h\[\033[0;33m\] \w\[\033[00m\]: '

###
### Bash history
###
export HISTCONTROL=ignoredups:erasedups
export HISTTIMEFORMAT="[%F %T] "
shopt -s histappend
