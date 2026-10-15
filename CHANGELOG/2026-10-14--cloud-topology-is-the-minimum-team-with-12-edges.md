## The cloud topology is the minimum team with 12 edges

### Changed
- Cloud (api.4genthub.com): rooms `4genthub-dev` (9 seats, 21 links), `4genthub-client` (5), `4genthub-ab` (4) and `smoke` (1) were deleted, seats first. `4genthub-min` now has the 12 edges of `NEXT-GEN2.md` section 2, created by `PUT /api/v2/rooms/4genthub-min/seats/{seat}/links` with `allow: true` (the cloud accepted it on the omp seats). The topology page now reads 1 room, 5 seats, 12 edges (measured through the API).

### Tested
Counted through `GET /api/v2/rooms`, `/seats` and `/links` before and after. Before the deletion the four rooms were dumped to a local snapshot (seats and links); it is not in the repository.
