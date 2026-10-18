# The test harness says which database variable not to export

`agenthub_go/tools/testpg/start.sh` prints `AGENTHUB_TEST_PG_URL`, so a runner following "set the
database env vars" exports that - and, naturally, `TEST_DATABASE_URL` too. That second variable is a
different case's switch: `models_prod_test.go:29` reads it, `:143` skips with "SKIPPED, NOT PASSED"
when it is unset, and when it IS set `TestProductionModelsCRUDRealPostgres` runs against a schema this
harness does not create and goes red 0.02s in on six legacy tables (`relation agent_import_history
does not exist`). The skip is correct behaviour that the export silently disables - two runs in an
earlier packet were spent on the resulting red.

The harness's own comment block now records the variable, the case, the two behaviours and the
symptom, beside the `|| true` false-red lesson it already carried. No gate, skip condition or
variable meaning changed.

Verified: `bash -n agenthub_go/tools/testpg/start.sh` parses.
