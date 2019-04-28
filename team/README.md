# Sharing within a team

- Choose your team by setting `BASE_TEAM` variable inside your `user/<username>.sh` script.
- Place team-specific commands inside `<team name>/bin` directory
- Place team-specific shell libraries inside `<team_name>/lib` directory
- Two libraries under `<team_name>/lib` have special meaning:
    1. `<team_name>.sh` - always sourced by `base_init.sh`
    2. `bashrc` - sourced by `base_init.sh` if the invoking shell is interactive
- `base_init.sh` adds `$BASE_HOME/team/$BASE_TEAM/bin` to `PATH`.

# Sharing among teams

- To share libraries and commands of other teams, set `BASE_SHARED_TEAMS` variable inside `user/<username>.sh` script. 
    1. `base_init.sh` adds shared teams bin directory to `PATH`
    2. Shared team's `<shared_team_name>/lib/<shared_team_name>.sh` libraries or `bashrc` are not automatically sourced in

- To source in a team's library, use the `import` function (defined in `lib/stdlib.sh`):
  ```bash
  import lib/<library>.sh
  import team/<team name>/<library>.sh
  ```
