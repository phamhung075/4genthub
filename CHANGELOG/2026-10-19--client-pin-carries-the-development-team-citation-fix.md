# The pin carries the development-team citation fix

The hub's gitlink moves `36a415f -> 8a97cf7` (client main). The `development-team` skill stops citing a
reference that no longer exists; two lines in, three out, plus its changelog entry. The skill file is
byte-identical from `4b24c15` through `36a415f`, so the hunk applies without a rebase.

Evidence: `git apply --check` rc 0 at `36a415f` (sha256 `1e7532ab`); the commit's numstat is
`skills/share/development-team/SKILL.md +2 -3` and its changelog `+18 -0`; settled by board `fd2f893b`
criterion 2.
