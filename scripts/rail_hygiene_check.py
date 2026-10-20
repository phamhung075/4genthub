#!/usr/bin/env python3
"""Check room rail queue hygiene and chain_of_record successor states."""

import json
import os
import sqlite3
import sys


def find_db():
    room = os.environ.get("AGENTHUB_ROOM", "4genthub-min")
    state_root = os.environ.get("AGENTHUB_STATE_DIR", os.path.expanduser("~/.config/4genthub"))
    candidate = os.path.join(state_root, "rooms", room, "queue.sqlite")
    if os.path.exists(candidate):
        return candidate
    sys.stderr.write(f"Cannot find queue database at {candidate}\n")
    sys.exit(1)


def main():
    db_path = find_db()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT qitem_id, state, chain_of_record, summary, ts_created FROM queue_rows")
    rows = cur.fetchall()

    successors = {}
    for r in rows:
        qid = r[0]
        chain_str = r[2]
        try:
            chain = json.loads(chain_str) if chain_str.startswith("[") else ([chain_str] if chain_str and chain_str != "-" else [])
        except Exception:
            chain = []
        for parent in chain:
            successors.setdefault(parent, []).append(qid)

    handed_off_rows = [r for r in rows if r[1] == "handed-off"]
    missing = [r for r in handed_off_rows if r[0] not in successors]

    # Check if any handed-off row has successors that are all handed-off
    all_ho_succ = []
    row_map = {r[0]: r for r in rows}
    for r in handed_off_rows:
        succs = successors.get(r[0], [])
        if succs and all(row_map[s][1] == "handed-off" for s in succs if s in row_map):
            all_ho_succ.append(r)

    print(f"total_queue_rows={len(rows)}")
    print(f"handed_off_rows={len(handed_off_rows)}")
    print(f"orphaned_handed_off_rows={len(missing)}")
    print(f"all_handed_off_successor_rows={len(all_ho_succ)}")

    print("\n--- ORPHANED HANDED-OFF ROWS ---")
    for r in missing:
        print(f"{r[0]} ({r[4][:10]}): {r[3][:65]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
