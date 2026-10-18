# The client pin names `bcd3110`: `deepseek-offload` is a submodule and the seat skill

`agenthub_client` moves `34d5eba` -> `bcd3110`:

### Added
- Submodule `third_party/deepseek-offload` (`git@github.com:phamhung075/deepseek-offload.git`); the symlink
  `skills/share/deepseek-offload` points at its `.agents/skills/deepseek-offload`, so every seat gets the skill
  through `sync` and `reseat`.

### Changed
- The skill loader, the installed-copy hash (`treeHash`) and the retired-verb scan accept a symlinked skill
  directory. The scan skips symlinks: a linked skill is the submodule's text.
- The seat skill `deepseek-delegation` is retired; `deepseek-offload` replaces it.

### Tested
- `go test ./...` and `cargo test --offline` (179) pass in `agenthub_client`; new case
  `TestASymlinkedSkillDirectoryIsASkill`.
