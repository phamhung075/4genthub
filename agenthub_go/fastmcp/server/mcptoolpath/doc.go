// Package mcptoolpath holds black-box tests that drive the MCP tool path - POST /mcp,
// tools/call - over a real database, in their OWN test binary.
//
// WHY A SEPARATE PACKAGE: services.RepositoryProviderService.GetInstance caches a provider built
// from the FIRST composition's repository backend (repository_provider_service.go:63-73), and
// httpapp.NewApp sets that backend to the SessionManager it was handed (app.go:40). In one test
// binary that means the provider keeps whichever test composed an App FIRST, so a tool call in a
// LATER test is served from a database that test's cleanup already dropped - `sql: database is
// closed`. A test that composes an App therefore cannot share a binary with the httpapp suite and
// stay order-independent. It is also true of a package that merely imports httpapp: the caching is
// process-wide, so the binary is what has to be separate.
package mcptoolpath
