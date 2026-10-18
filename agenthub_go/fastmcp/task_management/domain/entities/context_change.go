package entities

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
)

// ContextChange is ONE leaf a context write changed, as the ledger's `context_updated` payload names
// it: a dot-joined path (`status`, `implementation_notes.progress_updates`), the operation, and the
// leaf's old and new value. The WHO is not here: attribution is `actor_kind`/`actor_id` on the entry,
// which is the one home for it (the same rule RecordStatusChange follows).
type ContextChange struct {
	Path string `json:"path"`
	Op   string `json:"op"`
	Old  any    `json:"old,omitempty"`
	New  any    `json:"new,omitempty"`
}

// The two caps the payload keeps, in bytes of compact JSON. A task context holds implementation
// notes, insights and settings, so a full snapshot (or a whole array element-diffed) would put
// 100 KB+ per edit into an append-only table.
const (
	// MaxContextChangeValue bounds one leaf value. Over it, the value is replaced by a marker with
	// its byte count and sha256, which keeps it verifiable and diffable without the bytes.
	MaxContextChangeValue = 512
	// MaxContextChangesPayload bounds the whole `changes` array. A longer change set keeps the first
	// entries in canonical order and reports the count dropped.
	MaxContextChangesPayload = 8 << 10
)

// ContextChanges is the ONE change-set builder: both writers call it, so the two can never drift.
// It is pure - no I/O - and deterministic: keys are compared in sorted order, nested maps one level
// deep, and any deeper value (a map, an array, a scalar) as a whole.
//
// `dropped` counts the changes left out to respect MaxContextChangesPayload.
func ContextChanges(before, after *OrderedMap[any]) ([]ContextChange, int) {
	changes := []ContextChange{}
	for _, key := range unionKeys(before, after) {
		oldValue, oldOK := getOf(before, key)
		newValue, newOK := getOf(after, key)

		oldMap, oldIsMap := asOrderedMap(oldValue)
		newMap, newIsMap := asOrderedMap(newValue)
		if oldIsMap && newIsMap {
			for _, sub := range unionKeys(oldMap, newMap) {
				oldLeaf, hadOld := oldMap.Get(sub)
				newLeaf, hasNew := newMap.Get(sub)
				appendLeaf(&changes, key+"."+sub, oldLeaf, hadOld, newLeaf, hasNew)
			}
			continue
		}
		appendLeaf(&changes, key, oldValue, oldOK, newValue, newOK)
	}
	return boundChanges(changes)
}

// ContextUpdatePayload is the payload the ledger stores for a context write, assembled in ONE place so
// both writers agree on its keys: the level and version the row records, the writer surface (`origin`),
// the bounded change set, and how many changes were left out.
func ContextUpdatePayload(level, id string, version int, origin string, changes []ContextChange, dropped int) map[string]any {
	if changes == nil {
		changes = []ContextChange{}
	}
	return map[string]any{
		"level":             level,
		"id":                id,
		"version":           version,
		"origin":            origin,
		"changes":           changes,
		"changes_truncated": dropped,
	}
}

// appendLeaf writes one change at `path`, or nothing when the two sides are equal.
func appendLeaf(changes *[]ContextChange, path string, oldValue any, hadOld bool, newValue any, hasNew bool) {
	switch {
	case hadOld && !hasNew:
		*changes = append(*changes, ContextChange{Path: path, Op: "remove", Old: capValue(oldValue)})
	case !hadOld && hasNew:
		*changes = append(*changes, ContextChange{Path: path, Op: "add", New: capValue(newValue)})
	case hadOld && hasNew && !sameJSON(oldValue, newValue):
		*changes = append(*changes, ContextChange{Path: path, Op: "set", Old: capValue(oldValue), New: capValue(newValue)})
	}
}

// capValue replaces a value whose compact JSON exceeds MaxContextChangeValue with a marker carrying
// its byte count and sha256 - still verifiable and diffable, without the bytes.
func capValue(value any) any {
	encoded, err := json.Marshal(value)
	if err != nil || len(encoded) <= MaxContextChangeValue {
		return value
	}
	sum := sha256.Sum256(encoded)
	return map[string]any{"truncated": true, "bytes": len(encoded), "sha256": hex.EncodeToString(sum[:])}
}

// boundChanges keeps the change set inside MaxContextChangesPayload, counting what it leaves out.
func boundChanges(changes []ContextChange) ([]ContextChange, int) {
	kept := make([]ContextChange, 0, len(changes))
	size := 2 // the enclosing "[]"
	for _, change := range changes {
		encoded, err := json.Marshal(change)
		if err != nil {
			continue
		}
		cost := len(encoded)
		if len(kept) > 0 {
			cost++ // the comma between entries
		}
		if size+cost > MaxContextChangesPayload {
			return kept, len(changes) - len(kept)
		}
		size += cost
		kept = append(kept, change)
	}
	return kept, 0
}

func unionKeys(before, after *OrderedMap[any]) []string {
	seen := map[string]bool{}
	keys := make([]string, 0, before.Len()+after.Len())
	for _, side := range []*OrderedMap[any]{before, after} {
		if side == nil {
			continue
		}
		for _, key := range side.Keys() {
			if !seen[key] {
				seen[key] = true
				keys = append(keys, key)
			}
		}
	}
	sort.Strings(keys)
	return keys
}

func getOf(m *OrderedMap[any], key string) (any, bool) {
	if m == nil {
		return nil, false
	}
	return m.Get(key)
}

// asOrderedMap reads the nested shapes both writers hold: an OrderedMap, or the plain map a copy path
// may carry.
func asOrderedMap(value any) (*OrderedMap[any], bool) {
	switch typed := value.(type) {
	case *OrderedMap[any]:
		return typed, true
	case map[string]any:
		out := NewOrderedMap[any]()
		for _, key := range sortedMapKeys(typed) {
			out.Set(key, typed[key])
		}
		return out, true
	}
	return nil, false
}

// sameJSON compares two leaves by their compact JSON, so a number, an array or an object is compared
// as a whole and never element-diffed.
func sameJSON(left, right any) bool {
	leftJSON, leftErr := json.Marshal(left)
	rightJSON, rightErr := json.Marshal(right)
	if leftErr != nil || rightErr != nil {
		return leftErr == nil && rightErr == nil
	}
	return string(leftJSON) == string(rightJSON)
}
