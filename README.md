# Base

![Tests](https://github.com/basefoundry/base/actions/workflows/tests.yml/badge.svg)
![Lint](https://github.com/basefoundry/base/actions/workflows/pylint.yml/badge.svg)
![Platform: macOS + Ubuntu/Debian](https://img.shields.io/badge/platform-macOS%20%2B%20Ubuntu%2FDebian-lightgrey)
![Version](https://img.shields.io/badge/version-1.8.0-blue)

> Base is an AI-ready GitHub workspace control plane for repository setup, local
> development, and verified pull requests.

Base is the local operating contract that makes a project workspace explicit
and repeatable. It gives developers and platform engineers a shared way to
prepare repositories, inspect readiness, approve trusted project commands, and
hand off work across one or more independent Git repositories.

Use Base when you need to:

- create or configure a GitHub repository and its local workspace;
- make setup, readiness, tests, builds, and trusted execution inspectable before
  work starts;
- carry enough evidence from issue and implementation work to a verified,
  handoff-ready pull request.

Base owns workspace orchestration, policy, trust, readiness, and handoff. Your
repositories own their source code, tests, and project behavior; GitHub owns
hosting and pull requests; environment managers and AI tools remain adapters.
That boundary lets Base coordinate the workflow without turning your projects
into a monorepo or moving project-specific logic into Base.

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

## Quickstart

For the canonical source-checkout install commands, see the
[source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe).
Then run the trust-conscious project proof:

```bash
# After completing the canonical source-checkout install recipe.
~/work/base/bin/basectl setup --dry-run
~/work/base/bin/basectl projects list --workspace ~/work
~/work/base/bin/basectl trust status base
```

Review the manifest identity and digest printed by `trust status` before
running the exact `basectl trust allow base --manifest-sha256 ...` command it
provides. This path lets you inspect and verify Base before adding it to shell
startup files. See [Start Here](#start-here) for the full trust-conscious proof,
demo walkthrough, and install choices.

## Contents

- [Quickstart](#quickstart)
- [Start Here](#start-here)
- [How Base Fits](#how-base-fits)
- [Product Layers And Shipped Commands](#product-layers-and-shipped-commands)
- [Public Command Surface](#public-command-surface)
- [Documentation](#documentation)
- [Compatibility](#compatibility)

## Why Base Exists

Every engineering project accumulates setup steps, readiness rules, trusted
commands, and handoff context that can become scattered across READMEs, shell
state, and maintainer memory. That problem exists within a single repository
and becomes more visible when work spans several repositories. Base gives a
project or participating repository set one explicit local contract for answering:
what belongs here, what is ready, what is missing, what may run, and what the
next person or agent needs to know.

In this product promise, **deterministic** is deliberately narrow. Base makes
declared inputs, inspection order, findings, and next actions explicit and
repeatable. It does not promise hermetic builds, byte-for-byte environments, or
transactional mutation across every repository and external tool.

For a concise evaluator view of where Base fits, what it gives a project or
multi-repo workspace, and how it compares with adjacent tools, see
[Why Base](docs/why-base.md).
For a candid maintained assessment of Base's originality, usefulness, adoption
potential, and engineering evidence, see
[Product Assessment](docs/product-assessment.md).

Common first-run and product questions are answered in [FAQ.md](FAQ.md).
Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md). Report security
issues and handle detected credentials according to [SECURITY.md](SECURITY.md).
Release notes are tracked in [CHANGELOG.md](CHANGELOG.md).

## Source Control And Forge Support

Base assumes Git. Mercurial, Perforce, Subversion, and other non-Git SCMs are
out of scope.

Base is GitHub-primary rather than forge-independent. GitHub is the only
first-class forge automation target today for repository creation,
configuration, Issues, pull requests, Projects, Actions intake, and release
publishing. A GitLab, Bitbucket, internal Git, or local Git repository can
still use Base's local project loop once it is checked out locally and declares
`base_manifest.yaml`.

See [Source Control And Forge Support](docs/source-control-and-forge-support.md)
for the command-by-command compatibility contract and non-GitHub Git workflow.

## Start Here

### Trust-Conscious Proof, No Dotfile Changes

This trust-conscious evaluation path uses a source checkout. First follow the
[source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe),
then inspect the code and prove the local project loop before relying on the
shell handoff:

```bash
# After completing the canonical source-checkout install recipe.
~/work/base/bin/basectl setup --dry-run
~/work/base/bin/basectl projects list --workspace ~/work
~/work/base/bin/basectl trust status base
```

Review the manifest identity, digest, and read-only inspection commands, then
run the exact `basectl trust allow base --manifest-sha256 ...` command printed
by `trust status`. Until shell-profile setup puts `basectl` on `PATH`, replace
its leading `basectl` with `~/work/base/bin/basectl`; keep the project and
printed digest unchanged. The digest-bound approval is never inferred from
setup or an unattended flag. After approving the reviewed manifest, finish the
proof:

```bash
~/work/base/bin/basectl demo base -- --non-interactive
```

That sequence creates Base's local runtime state under `~/.base.d`, but it does
not edit `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`, or `~/.zshrc`. Use the
same explicit path, `~/work/base/bin/basectl`, until you decide to add Base to
future interactive shells.

To inspect a small, real Base-managed project, clone
[`basefoundry/base-demo`](https://github.com/basefoundry/base-demo) next to
Base and run its walkthrough:

```bash
git clone https://github.com/basefoundry/base-demo.git ~/work/base-demo
~/work/base/bin/basectl setup base-demo
~/work/base/bin/basectl trust status base-demo
```

Review the reported command surfaces, then run the exact command it prints:
`basectl trust allow base-demo --manifest-sha256 ...`. Only then launch the
demo:

```bash
~/work/base/bin/basectl demo base-demo
```

Success looks like a workspace where each participating project has a
`base_manifest.yaml`, appears in `basectl projects list`, can be checked with
`basectl check <project>`, and can run its declared test command through
`basectl test <project>` or named project commands through
`basectl run [project] <command>`.

### Shell Startup Is Explicit

Run `update-profile` only after you want `basectl` on `PATH`, shell
completions, and `basectl activate <project>` available in new interactive
shells:

```bash
~/work/base/bin/basectl update-profile --dry-run
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`update-profile` manages only marked Base sections in Bash and Zsh startup
files and preserves non-Base content. See [Shell Startup Files](#shell-startup-files)
for the full dotfile boundary.

### Choose An Install Path

If your Mac already has Homebrew, Git, and a supported Bash, choose one of the
normal Base install paths:

- Use Homebrew when you want Base managed like an ordinary installed tool.
- Use a source checkout when you want to inspect, contribute to, or dogfood Base
  from the repository.

See the canonical [Homebrew install recipe](docs/bootstrap.md#homebrew-install-recipe)
or [source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe).

For Homebrew installs, Base itself lives under Homebrew's prefix rather than in
your project workspace. For source checkout installs, Base lives at the clone
path you choose, usually `~/work/base`. In both modes, first setup creates
`~/.base.d/config.yaml` with the default workspace root:

```yaml
workspace:
  root: ~/work
```

Edit `workspace.root` if your repositories live under a different shared
directory. You may also add an optional workspace manifest:

```yaml
workspace:
  root: ~/work
  manifest: ~/work/base-workspace/workspace.yaml
  manifest_source: https://raw.githubusercontent.com/<org>/<repo>/main/workspace.yaml
```

When `workspace.manifest` is set, workspace status, check, doctor, onboarding,
agent-brief, clone, configure, setup, and update commands use it unless `--manifest <path>` is
supplied for a single command. `basectl workspace pull` treats it as the local
destination for an explicitly requested refresh. When
`workspace.manifest_source` is set, pull can refresh that local manifest from
the canonical source.

### New Or Uncertain Machine?

On a new macOS machine, or any machine where Homebrew, Git, or a supported Bash
may be missing, start with the first-mile bootstrap script:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

For a verified first run, pin reviewed Homebrew installer content before
executing the bootstrapper. Use the bootstrap-specific variables for this
script, or the `BASE_HOMEBREW_INSTALLER_URL` and
`BASE_HOMEBREW_INSTALLER_SHA256` pair when the same pin should apply to all
Base Homebrew entry points:

```bash
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL=file:///path/to/homebrew-install.sh \
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=<sha256> \
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

The bootstrapper installs Homebrew, Git, and a supported Bash when needed,
chooses an existing Base install when one is present, otherwise defaults to a
source checkout at `~/work/base`, and prints the exact `basectl setup` and
`basectl update-profile` commands to finish the installation. It does not edit
shell startup files automatically.

If Base is already installed but `basectl` cannot start because Bash is too
old, repair only that prerequisite:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --dry-run
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --yes
```

Choose an install mode explicitly when needed:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --brew
```

For mode selection, dry-run behavior, and contributor setup details, see
[First-Mile Bootstrap](docs/bootstrap.md).

On Ubuntu/Debian Linux, the same bootstrap script prints the manual
source-checkout path instead of running apt itself:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source --dry-run
```

Review the printed apt, clone, `basectl setup --yes`, and `update-profile`
commands, then run them in the Ubuntu shell. The printed `--yes` handoff is for
unattended pasted commands; interactive `basectl setup` still applies setup
after prompting for Ubuntu/Debian system changes.

### Team Or Security-Conscious Rollout

Use `--dry-run` before first-mile setup when you need to review planned
installer actions. Managed workstations can pin or mirror Homebrew installer
content by setting `BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL` and
`BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256`; Base fails closed if either half of
that pair is missing or the digest does not match.

Project-owned installers should pin `BASE_INSTALL_URL` to a tag, commit, or
owned copy and set `BASE_INSTALL_SHA256` before executing Base's installer. See
[Remote Installer Policy](docs/remote-installer-policy.md) and
[Project Installers](docs/project-installers.md) for the maintained trust
contracts.

After Base is installed, the common development loop is:

```bash
basectl projects list
basectl setup <project>
basectl check <project>
basectl doctor <project>
basectl test <project>
basectl demo [project]
basectl run [project] <command>
basectl export-context <project>
basectl docs
basectl activate <project>
```

For Base itself, run the self-demo or the dogfood test contract:

```bash
basectl demo base -- --non-interactive
basectl test base
```

## How Base Fits

Base's product responsibilities have four layers:

- **Core outcome:** deterministic local readiness and handoff across independent
  Git repositories.
- **Enabling execution contract:** `base_manifest.yaml`, `basectl`,
  `base-wrapper`, explicit activation, and declared project commands.
- **Supporting workflow packs:** repository baselines plus GitHub and release
  conventions. These support the outcome; they are not Base's primary product
  category.
- **Adapters:** environment managers, IDEs, containers, Nix/devenv, and AI
  tools remain external systems that Base detects, checks, invokes, or exports
  context for without taking over their domains.

These are responsibility layers, not separately installed packages. Base
orchestrates tools that already own their domains:

- Homebrew still owns ordinary macOS packages and Brewfiles.
- mise owns its configuration model, including language/runtime management and
  its broader machine and project bootstrap behavior. When a Base manifest
  points to a mise config, Base checks mise's config trust and missing tools,
  runs `mise install`, and delegates `mise run`. On Debian-family Linux, Base
  can install a missing mise CLI after `--dry-run` review and `--yes` consent
  under its [remote-installer policy](docs/remote-installer-policy.md). Base
  does not invoke or interpret `mise bootstrap`.
- Project repositories still own their source code, tests, installers, service
  definitions, and product-specific onboarding.
- Base owns the local contract that makes participation, readiness, trusted
  execution, and handoff explicit across projects.

Repository discovery, clone or synchronization, status, and command fan-out are
shared ecosystem primitives rather than Base's differentiation. See
[Tool Boundaries](docs/tool-boundaries.md) for the dated comparison, including
when to choose mise, `mani`, `gita`, `vcs2l`, Android Repo, or `west` instead.

### Reusable Bash Libraries

Base's reusable Bash libraries are also available as a standalone package for
scripts that want Base's Bash helper conventions without adopting the Base
local operating contract:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base-bash-libs
```

Base consumes reusable Bash libraries from an external `base-bash-libs` checkout
or Homebrew package. The resolution order, standalone usage path, and
post-migration boundary are documented in
[Base Bash Libraries](docs/base-bash-libs.md).

## Product Layers And Shipped Commands

The full command and runtime reference lives in the focused documentation:

- [Command Quick Reference](docs/command-reference.md) — current commands,
  flags, output formats, and detailed command behavior.
- [Technical Overview](docs/technical-overview.md) — product model, workspace
  shape, manifest contract, architecture, and implementation boundaries.

This README keeps the product overview and first-run path above; use the focused
references when you need command or runtime detail.

The top-level public command inventory remains visible here:

- `basectl setup [project]`
- `basectl check`
- `basectl doctor`
- `basectl clean --older-than <age>`
- `basectl config <path|show|doctor>`
- `basectl update-profile`
- `basectl update`
- `basectl projects list`
- `basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|update|init|configure|setup>`
- `basectl trust <status|allow|revoke>`
- `basectl repo <init|clone|check|configure|agent-guidance|installer-template>`
- `basectl gh <area> <command>`
- `basectl release <check|plan|notes|publish>`
- `basectl prompt <list|product-self-review>`
- `basectl activate <project>`
- `basectl test [project]`
- `basectl build [project] [target...]`
- `basectl demo [project]`
- `basectl run [project] <command>`
- `basectl export-context [project]`
- `basectl devcontainer [project]`
- `basectl devenv-report [project]`
- `basectl docs`
- `basectl onboard`
- `basectl history [--report]`
- `basectl version`

## Public Command Surface

Base exposes its own commands through `$BASE_HOME/bin`. That directory is added
to `PATH` by Base's managed shell startup snippets.

`bin/basectl` is the control-plane command. Additional Base-owned public
commands, when needed, are tiny real launcher files in `bin/` that delegate to
`basectl`; their implementation remains under
`cli/bash/commands/<command>/` or, in the future,
`cli/python/commands/<command>/`.

Example launcher for a hypothetical Base-owned Bash command:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" example "$@"
```

Projects expose their own commands through `$PROJECT_ROOT/bin`. When
`basectl activate <project>` starts a project runtime shell, Base adds that
directory to `PATH` if it exists, behind `$BASE_HOME/bin` and behind any
detected optional Base Platform Tools checkout. Project Python command packages
should be treated as implementation details unless a project-owned launcher
exposes them from `bin/`.

Optional utility commands live in
[`basefoundry/base-platform-tools`](https://github.com/basefoundry/base-platform-tools).
When that repository is checked out next to Base as `base-platform-tools`, Base
adds its `bin/` directory to `PATH` in new Bash/Zsh shells and Base runtime
shells. This is detected dynamically by the sourced shell snippets; users do not
need to rerun `basectl update-profile` after checking out the optional repo.

Project launchers that need to run Python packages should delegate through
`base-wrapper` so they use the selected project virtual environment and Base's
Python library roots:

```bash
#!/usr/bin/env bash
exec "$BASE_HOME/bin/base-wrapper" --project "${BASE_PROJECT:-example}" example_cli "$@"
```

`basectl setup` deliberately pins its default Homebrew Python formula so setup is
reproducible across machines. The current default is `python@3.13`. Override it
with `BASE_SETUP_PYTHON_FORMULA` when a workspace needs a different formula.
After this Bash bootstrap layer creates Base's own Python environment, setup
installs Base bootstrap Python packages into that environment. Shell-only
project reconciliation runs from that Base runtime and does not copy those
packages into a project venv. Projects that explicitly declare `python:` or a
`python-package` artifact keep the project-runtime path: Base first seeds the
target project venv with `bootstrap: true` default artifacts and then invokes
the Python project setup layer through `base-wrapper --project <project>`.
Prerequisite profiles are opt-in. Use `--profile dev` to install Base
contributor tools from `lib/base/dev_manifest.yaml`. On macOS that includes
Homebrew-managed BATS, GitHub CLI, and ShellCheck. On Ubuntu/Debian it installs
Base-owned apt-backed tools such as BATS and ShellCheck. It installs GitHub CLI
from GitHub CLI's official Debian/Ubuntu apt repository/keyring instead of the
default distro package; authentication remains user-owned. Use `--profile sre`
for the initial site-reliability profile in
`lib/base/sre_manifest.yaml`, which installs local diagnostic tools such as
`kubectl`, `helm`, `k9s`, `httpie`, `grpcurl`, `jq`, `yq`, `nmap`, and `mtr`.
Use `--profile ai` for optional AI coding tools: Codex CLI and Claude Code.
Use `--profile linux-lab` on a macOS host to install and check Multipass for
local Ubuntu lab VMs. Profiles compose with a comma-separated list.

```bash
basectl setup --profile dev
basectl setup --profile sre
basectl setup --profile ai
basectl setup --profile linux-lab --dry-run
basectl setup --profile linux-lab
basectl setup --profile dev,sre
basectl setup --profile dev,ai
basectl setup --profile dev,linux-lab
basectl check --profile sre
basectl check --profile ai
basectl check --profile linux-lab
basectl doctor --profile sre
basectl doctor --profile ai
basectl doctor --profile linux-lab
```

AI coding tools are intentionally not part of the plain `dev` or `sre` profile.
`basectl setup --profile ai` uses official remote installers only when that
profile is explicitly requested. Base checks tool presence and version output,
but it does not manage accounts, credentials, model access, or organization
policy.

The `linux-lab` profile is intentionally host-scoped. It installs or checks the
Multipass CLI on macOS through `brew install --cask multipass`, but Base does
not create, start, mount, or delete Multipass instances during setup. Review
the planned install with `--dry-run`, then create lab VMs with
`multipass launch` when you are ready.

For the complete Homebrew, Codex CLI, Claude Code, uv, and mise installer
inventory; the distinction between consent and integrity; dry-run behavior;
and managed-device checksum guidance, see
[Remote Installer Policy](docs/remote-installer-policy.md).

Setup intentionally stays serial for mutating installers and state writes until
Base has a setup-plan/preflight layer that can prove safe concurrency boundaries.
See [`basectl setup` parallelism](docs/setup-parallelism.md).

On macOS, `basectl setup` sends a best-effort notification when setup completes
or fails after running for at least 30 seconds. Notifications are skipped during
`--dry-run` and never change the setup exit status. Use `basectl setup --notify`
to force a notification for quick runs, `basectl setup --no-notify` or
`BASE_SETUP_NOTIFY=false` to disable notifications, and
`BASE_SETUP_NOTIFY_MIN_SECONDS` to tune the default threshold. When `--notify`
is requested on macOS, Base warns if `osascript` is not available.

## Installation Details

For a blank macOS machine, use `bootstrap.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

The bootstrapper is intentionally small. It verifies macOS, installs Homebrew
when missing, installs Git and Bash through Homebrew when needed, then installs
Base through either a source checkout or Homebrew. It does not edit shell startup
files automatically. Instead, it prints the exact follow-up commands, typically:

```bash
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

Pass `--source` or `--brew` with `bash -s --` to choose the route explicitly.
Without an explicit choice, the bootstrapper preserves an existing Homebrew Base
install, then an existing source checkout, and otherwise defaults to source mode.
See [First-Mile Bootstrap](docs/bootstrap.md) for the full bootstrap contract.

On Ubuntu/Debian Linux, `bootstrap.sh` does not run `sudo apt` automatically.
It prints the manual source-checkout path, including the supported apt
prerequisites, a sibling `base-bash-libs` checkout, `basectl setup --dry-run`,
`basectl setup --yes`, and `basectl update-profile`.

The focused `bootstrap.sh --ensure-bash --yes` path is intentionally narrower:
it installs only Bash after a dry-run review.

For the complete Homebrew command sequence, see the canonical
[Homebrew install recipe](docs/bootstrap.md#homebrew-install-recipe).

Use the full formula name `basefoundry/base/base` for Homebrew installs and
upgrades. `basefoundry/base` is the tap name, not the formula, and bare `base`
can resolve to unrelated Homebrew formulae or casks.

Base is not yet in Homebrew/core. Until that changes, use the tap commands
above. The planned core path keeps the reusable Bash libraries as a separate
`base-bash-libs` dependency so a future non-conflicting Base formula, expected
to be named `basefoundry`, can install with:

```bash
brew install basefoundry
```

The trust step is required on Homebrew versions that block formulae from
non-official taps until the tap is trusted. It is safe to run again on machines
that already trust `basefoundry/base`. Existing installs that predate this
trust step can fail during upgrade while Homebrew loads Base's tap-owned
`base-bash-libs` dependency. If that happens, run:

```bash
brew trust basefoundry/base
brew upgrade --no-ask basefoundry/base/base
```

Homebrew installs the Base files. `basectl setup` still prepares the local Base
runtime under `~/.base.d/base/.venv`, and `basectl update-profile` adds Base to
your shell startup path. When installed through Homebrew, `basectl update` for
Base hands off to Homebrew and runs setup only when the installed Base version
changes. The Homebrew handoff is equivalent to:

```bash
brew upgrade --no-ask basefoundry/base/base
```

For a Base development machine, prefer the source checkout as the active
`basectl`. Homebrew-installed Base and source-cloned Base can coexist, but the
active command is whichever executable wins on `PATH`, and both normally share
state under `~/.base.d`. Use Homebrew-managed Base for consumer install or
upgrade validation in a test account, separate machine, isolated `HOME`, or with
explicit paths such as `/opt/homebrew/bin/basectl` or `~/work/base/bin/basectl`.

When Base is installed through Homebrew, `BASE_HOME` points to the stable
Homebrew install location, such as `/usr/local/opt/base/libexec` or
`/opt/homebrew/opt/base/libexec`. It does not point to your project workspace.
Configure `workspace.root` in `~/.base.d/config.yaml` so commands such as
`basectl projects list`, `basectl activate <project>`, and
`basectl test <project>` can find your repositories:

```yaml
workspace:
  root: ~/work
```

The standalone installer is also available:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/v1.8.0/install.sh \
  | bash -s -- --branch v1.8.0
exec "$SHELL" -l
```

This stable consumer path pins both the installer script and the checkout to
the published `v1.8.0` ref. Review the script first if you do not already
trust this repository:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/v1.8.0/install.sh
```

For contributor or dogfood installs that intentionally follow development
`main`, use the mutable installer explicitly:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/install.sh \
  | bash -s -- --branch main
```

By default, the installer clones or updates Base at `~/work/base`, runs
`~/work/base/bin/basectl setup`, and then runs
`~/work/base/bin/basectl update-profile`. Set `BASE_INSTALL_DIR` or pass
`--dir <path>` to install somewhere else. When using the piped form, pass
installer options with `bash -s --`, for example:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/v1.8.0/install.sh \
  | bash -s -- --branch v1.8.0 --dir ~/work/base --no-profile
```

Use `--no-profile` to skip shell startup integration and `--dry-run` to print
planned actions.

For the explicit manual source-checkout command sequence, see the canonical
[source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe).

After the shell restarts, Base's managed startup section adds `~/work/base/bin`
to `PATH`, so `basectl` can be run without spelling out the full path. Use
`basectl version` or `basectl --version` to report the installed Base version.

## Version Identity

`VERSION` is the latest published release identity. `DEVELOPMENT_VERSION` is
the numeric next development line. A clean tagged release or packaged install
reports the clean `VERSION`, while a mutable Git checkout—including a dirty
checkout based on a release tag—reports
`DEVELOPMENT_VERSION-dev+g<short-sha>` and appends `.dirty` when local changes
are present. For example, Base `1.8.0` and mutable development code targeting
`1.9.0` cannot report the same identity.

Project-specific onboarding should live in project installers that call Base
internally. `basectl onboard [project]` can run Base's setup/check/doctor flow
for a selected project, but product-specific setup still belongs in scripts such
as `banyanlabs/install.sh`. See [Project Installers](docs/project-installers.md)
for the recommended boundary.

## Documentation

The top-level README is the product overview and first-run guide. The
[docs README](docs/README.md) is the map for architecture, runtime behavior,
feature designs, and ecosystem boundary decisions.

Key starting points:

- [FAQ](FAQ.md)
- [Command Quick Reference](docs/command-reference.md)
- [Technical Overview](docs/technical-overview.md)
- [Base Newcomer Orientation](docs/presentations/base-newcomer-orientation.md)
- [Architecture](docs/architecture.md)
- [Clean macOS Install Validation](docs/macos-install-validation.md)
- [Execution Model](docs/execution-model.md)
- [Runtime Environment](docs/runtime-environment.md)
- [Tool Boundaries](docs/tool-boundaries.md)
- [Doctor Finding IDs](docs/doctor-findings.md)
- [IDE Bootstrapping](docs/ide-bootstrapping.md)
- [Local Config](docs/local-config.md)
- [Project Demo Workflow](docs/project-demo-workflow.md)

## Compatibility

Base is macOS-first, with Ubuntu/Debian runtime support now included in the
tested support contract.

Intended supported platforms are:

- macOS 14 Sonoma or newer on Apple Silicon
- macOS 14 Sonoma or newer on Intel Macs
- Ubuntu/Debian runtime environments with apt-backed Base setup

The supported macOS version floor is macOS 14 Sonoma. Support means Base is
tested and expected to work on macOS 14 or newer with Homebrew's supported
install contract, Xcode Command Line Tools, a Homebrew-managed Bash, Git, and
Python installed through Base setup. Older macOS releases may work from source,
but they are outside Base's tested support contract.

Ubuntu/Debian support currently covers runtime checks, project diagnostics,
source-checkout validation, and apt-backed setup for the simple prerequisites
Base owns. Linux setup remains narrower than macOS setup and should stay behind
the platform-policy boundary described in [docs/linux-support.md](docs/linux-support.md).
Windows is out of scope.

The macOS CI floor runs on GitHub's `macos-14` runner. Newer macOS runners may
be added for coverage, but the floor job should stay until Base intentionally
raises the support floor.

OS-specific behavior should stay isolated behind small helpers instead of being
scattered through command code. For example, the Base runtime prompt can prefer
macOS `scutil` names while still falling back to generic `hostname`.

## Shell Startup Files

Base integrates with Bash and Zsh through marked sections in your real dotfiles;
it never takes over whole files. `basectl update-profile` creates or refreshes
the managed sections, preserving unrelated content and writing a timestamped
sibling backup before changing an existing file.

By default, it updates `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`, and
`~/.zshrc`. Use `basectl update-profile --remove` to remove only Base-managed
sections, or `--dry-run` to preview changes. The detailed file-by-file contract,
debugging guidance, and optional defaults are in
[Shell Startup Files](docs/shell-startup.md).

## Optional Utility Tools

Base no longer owns general-purpose utility CLIs such as `caff` and
`sort-in-place`. Those tools live in
[`basefoundry/base-platform-tools`](https://github.com/basefoundry/base-platform-tools),
which is the optional platform/SRE utility layer for Base-managed workspaces.
Check it out next to Base to make its launchers available automatically in new
shells:

```bash
git clone https://github.com/basefoundry/base-platform-tools.git ~/work/base-platform-tools
exec "$SHELL" -l
```

The Base control-plane surface remains `basectl`.

## What Base Is Responsible For

Base owns the local operating contract for participating repositories.

That means Base should be responsible for:

- inventorying participating repositories and their declared contracts
- preparing and verifying local readiness through explicit commands
- enforcing Base's local trust boundary for manifest-declared execution
- making onboarding state and handoff evidence inspectable
- providing the execution conventions and diagnostics that support that outcome

Repository/GitHub/release workflow packs and environment/IDE/container/AI
adapters support this contract, but they do not redefine the core product.

## What Base Is Not Responsible For

Base should not absorb project-specific logic that belongs inside individual
repositories.

Each project repo should still own:

- its own source code
- its own business logic
- its own build details
- its own runtime details
- its own tests
- its own project-specific setup steps

Base should orchestrate those things, not replace them.

## Mental Model

Think of Base as the local operating contract for a project, whether that
project is one repository or a set of independent Git repositories.

A single repository can use Base to make setup, readiness, trusted execution,
and handoff explicit. When a project spans several repositories, Base extends
the same contract across the repository set. Each project repo remains independent;
Base sits beside those repos and offers:

- one declared way to inventory, prepare, and verify local readiness
- one explicit trust boundary for project-owned commands
- one onboarding story and a growing set of local handoff evidence

That gives a multi-repo setup some of the ergonomic benefits people often reach
for in a monorepo, without forcing unrelated codebases into a single repository.

## Likely Workspace Shape

The target shape looks roughly like this:

```text
work/                          ← shared workspace root (`workspace.root`)
  base/                        ← Base repository (`BASE_HOME` for source installs)
  project-a/                   ← peer project with `base_manifest.yaml`
  project-b/                   ← peer project with `base_manifest.yaml`
  infra/                       ← another peer repo that can opt into Base
```

Projects opt into Base with minimal coupling:

- Base discovers projects in the shared workspace
- projects expose a small contract through `base_manifest.yaml`
- Base provides common orchestration on top

## Design Principles

Base follows a few simple principles.

1. Keep project repos independent.
2. Prefer explicit conventions over hidden shell magic.
3. Keep wrappers thin but reliable.
4. Make setup and test flows idempotent where possible.
5. Make findings and next actions stable enough for human and automated handoff.
6. Let Base provide the common layer without turning into a dumping ground for
   project-specific behavior.

## Current Status

Base `1.8.0` is the current release. The implemented command surface covers
setup, checks, diagnostics, project discovery, project activation, project test
execution, manifest-declared mise trust/missing-tool checks plus `mise install`
and `mise run` delegation, cleanup, updates, onboarding, repository baseline
creation, CI-safe setup/check/doctor entry points, release readiness inspection,
guarded GitHub release publishing, GitHub workflow helpers, workspace
status/check/doctor/onboarding/init/clone/pull/configure flows, privacy-conscious
history reports, local AI context exports, repo-owned prompt rendering, the
`basectl docs` documentation shortcut, external reusable Bash library
consumption, and explicit prerequisite profiles for developer, SRE, AI tooling,
and local Linux lab setup. The `basectl setup`, `basectl check`, and `basectl
doctor` flows are platform-aware for macOS and Ubuntu/Debian, including
apt-backed prerequisite handling on Ubuntu/Debian; macOS diagnostics also warn
when Homebrew reports outdated or incomplete Xcode Command Line Tools.

For the documentation map and naming convention, see
[docs/README.md](docs/README.md). For accepted product requirements, see
[docs/product-requirements.md](docs/product-requirements.md). For the
architecture and product direction, see
[docs/architecture.md](docs/architecture.md). For the current `basectl` runtime
and dispatch contract, see [docs/execution-model.md](docs/execution-model.md).
For ecosystem boundary and integration decisions, see
[docs/tool-boundaries.md](docs/tool-boundaries.md).

Release notes are tracked in [CHANGELOG.md](CHANGELOG.md), and upcoming work is
tracked in GitHub Issues using the workflow in
[docs/github-workflow.md](docs/github-workflow.md).

## Short Version

Base is the local operating contract you add to a repository set so its readiness,
trusted execution, onboarding, and handoff stop depending on private maintainer
memory.

## License

Base is licensed under Apache-2.0 starting with v1.9.0.

Versions v1.0.1 through v1.8.0 remain available under AGPL-3.0-or-later, and
versions through v1.0.0 remain available under the MIT License as originally
published. See [LICENSE](LICENSE) for the current license terms.
