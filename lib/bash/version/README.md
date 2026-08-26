# `lib_version.sh`

Base version helpers that are safe to source before the full Base runtime is
loaded.

## Public API

- `base_read_version`
  Read the effective version identity for a caller-provided Base home. Tagged
  releases and packaged installs use `VERSION`; untagged Git checkouts use
  `DEVELOPMENT_VERSION-dev+g<short-sha>` and append `.dirty` when the checkout
  has local changes. It returns `unknown` when `VERSION` is missing or empty.

## Usage

```bash
source "/absolute/path/to/lib/bash/version/lib_version.sh"

printf 'basectl %s\n' "$(base_read_version "$BASE_HOME")"
```

## Behavior Notes

- This library intentionally does not depend on `lib_std.sh`.
- `bin/basectl` uses it before `base_init.sh` is sourced so `basectl --version`
  stays available early in startup.
- The runtime `basectl version` command uses the same helper after Base home has
  been validated.
- A matching `vX.Y.Z` tag keeps the published `VERSION` identity. A mutable
  source checkout must carry the numeric next-development line in
  `DEVELOPMENT_VERSION`.

## Tests

BATS coverage lives in `tests/lib_version.bats`.
