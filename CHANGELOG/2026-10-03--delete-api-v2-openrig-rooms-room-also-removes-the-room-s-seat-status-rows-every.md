### Fixed

**Deleting a room deletes its seat status** (2026-10-03)

- `DELETE /api/v2/openrig/rooms/{room}` also removes the room's `seat_status` rows (every machine, this user only) in the same transaction (`MachineStatusRepository.DeleteSeatStatusForRoom`, `RoomDeletionService`). Before, they stayed until the bridge replaced the machine snapshot.
