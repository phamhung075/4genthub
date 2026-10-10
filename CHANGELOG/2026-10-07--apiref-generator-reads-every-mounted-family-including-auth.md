## apiref generator reads every mounted family, including auth

- The route walk follows each `RegisterRoutes` call to its package through `go.mod`, so the
  auth registrations are counted: the generator now reports **144 routes** where it reported 124.
- The drift witness was widened to the same three families; a witness that reads less than the
  producer fails direction two, which is the property it exists to assert.
- Verified by the lead: `go run ./cmd/apirefgen -out <tmp>` reports 144 routes and 10 tools,
  `pathParams: null` count 0 (79 empty lists), 144 method+path pairs, no duplicates;
  `gofmt` clean; `go test ./internal/apiref/` ok.
