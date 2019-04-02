# Sharing within a team

- Place team-specific commands inside <team name>/bin directory
- Place team-specific shell libraries inside <team name>/lib directory
- Two libraries under <team name>/lib have special meaning:
    1. <team name>.sh - always sourced by base_init.sh
    2. bashrc - sourced by base_init.sh if the invoking shell is interactive

- A user chooses his/her team by setting BASE_TEAM variable inside user/<user name>.sh script.
- base_init.sh adds $BASE_HOME/team/$BASE_TEAM/bin to PATH.
- To share libraries and commands of other teams, set BASE_SHARED_TEAMS variable inside user/<user name>.sh script. 
    1. base_init.sh adds shared teams bin directory to PATH
    2. Shared team's libraries or bashrc are not automatically sourced in

- To source in a team's library, use the 'import' function (defined in lib/stdlib.sh):
  ```bash
  import lib/<library>.sh
  import team/<team name>/<library>.sh
  ```
