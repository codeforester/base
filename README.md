# **What is Base?**

Base is a way for Bash users to organize the following across multiple hosts:

* .bash_profile
* .bashrc
* generic Bash libraries and commands
* company specific Bash libraries and commands
* team specific Bash libraries and commands
* user specific settings (aliases, functions, Bash settings)
* share Bash libraries and commands across teams

# **How can I get set up?**

You can get set up in a very short time.  Essentially, this is what you have to do:

* Check out Base. The standard convention is $HOME/git/base.  In case your git directory is elsewhere, symlink it to `$HOME/git`.
* Consolidate your profile specifics from your current `.bash_profile` and `.bashrc` into `<yourname>.sh` file.  Place this file under `base/user` directory.
* Make a backup of your `.bash_profile`.  Replace this file with a symlink to `base/lib/bash_profile`.
* Make a backup of your `.bashrc`.  Replace this file with a symlink to `base/lib/bashrc`.

Here is the code:

    cd $HOME
    mkdir git && cd git
    git clone git@github.com:codeforester/base.git
    cd $HOME
    mv .bash_profile .bash_profile.safe && ln -sf $HOME/git/base/lib/bash_profile .bash_profile
    mv .bashrc       .bashrc.safe       && ln -sf $HOME/git/base/lib/bashrc       .bashrc

# **How does Base work?**

In a typical setting `.bashrc` sources in `$BASE_HOME/base_init.sh` which does the following:

* sources in `lib/stdprofile.sh`, `lib/stdlib.sh`, and `user/<user>.sh` if it exists, in that order
* updates `$PATH` to include the relevant `bin` directories
    * `$BASE_HOME/company/bin` is always added
    * `$BASE_HOME/team/$BASE_TEAM/bin` is added if `$BASE_TEAM` is set in `user/<user>.sh`
    * `$BASE_HOME/team/$BASE_TEAM/bin` is added for each team defined in `$BASE_SHARED_TEAMS` (space-separated string), set in `user/<user>.sh`

# **Directory structure**

[![Screenshot of directory structure](./docs/img/directory_structure.png)](./docs/img/directory_structure.png)

# **Environment variables**

* BASE_HOME
* BASE_DEBUG
* BASE_TEAM
* BASE_SHARED_TEAMS
* BASE_OS
* BASE_HOST

# **FAQ**

## My git location is not `$HOME/git/base`.  What should I do?

You can either
    * specify your base location in `$HOME/.baserc`, like
      
          BASE_HOME=/path/to/base

    * symlink `$HOME/git/base` to the right place

You need to do this on every host where you want base.

## I don't want to keep my personal settings private, and not in git.  What should I do?

    Do one of the following:

    * write a one-liner in `user/<user>.sh` like this:

        source /path/to/your.settings

    * add the following code to your .bashrc:

        export BASE_HOME=/path/to/base
        source "$BASE_HOME/base_init.sh"

    In both these cases, you need to manage your files manually, outside git.

## I do want to use the default settings.  What should I do?

Add this to your `user/<user>.sh` file:

    import lib/base_defaults.sh

## I want to make sure I keep my base repository updated always.  How can I do it?

Add this to your `user/<user>.sh` file:

    base_update

# **Debugging**

You can turn on debug mode by touching `$HOME/.base_debug` file.  You can also do the same by setting environment variable `BASE_DEBUG` to 1. You can add `set -x` to `$HOME/.baserc` file to trace the execution.
