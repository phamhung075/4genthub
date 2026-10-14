## `~/.config/4genthub/.env` fills a variable that is exported empty

### Fixed
- `agenthub_go/fastmcp/utilities/config_loader.go` (`LoadEnv`): a name already present in the process environment with an empty value (for example `TYPESAFE_API_KEY=` exported by a shell or a unit file) blocked the value in the file, so the Jev client and every other `ResolveConfigVar` caller saw no key. `LoadEnv` now skips a name only when its current value is non-empty, matching `ResolveConfigVar`, which already treats empty as unset.

### Tested
- `go test -count=1 ./fastmcp/utilities/` and `go vet ./fastmcp/utilities/` pass, including the new `TestLoadEnvFillsEmptyAndKeepsNonEmpty`.
