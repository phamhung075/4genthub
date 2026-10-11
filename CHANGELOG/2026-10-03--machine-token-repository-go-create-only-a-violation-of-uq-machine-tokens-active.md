### Fixed

**Machine token creation reported any integrity error as a conflict** (2026-10-03)

- `machine_token_repository.go` `Create`: only a violation of `uq_machine_tokens_active` (SQLSTATE 23505) is `ErrMachineTokenExists` (409 "already has an active token"); a foreign key, not-null or other unique violation is returned as the underlying error (500). Reviewer minor on the machine-token commit.
