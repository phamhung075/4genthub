package rigspec

import "sort"

// FindLaunchCycle returns the seat keys of a cycle in the launch order of edges, closed by
// repeating the first key (["a", "b", "a"]), or nil when the edges can launch. Only
// delegates_to (the source launches before the target) and spawned_by (the target is the
// parent and launches before the source) order a launch; the other kinds are descriptive. This
// is the rule `rig up` applies ("Cycle detected in rig topology").
func FindLaunchCycle(edges []Edge) []string {
	next := map[string][]string{}
	for _, e := range edges {
		switch e.Kind {
		case "delegates_to":
			next[e.From] = append(next[e.From], e.To)
		case "spawned_by":
			next[e.To] = append(next[e.To], e.From)
		}
	}
	keys := make([]string, 0, len(next))
	for key, targets := range next {
		sort.Strings(targets)
		keys = append(keys, key)
	}
	sort.Strings(keys)

	const (
		visiting = 1
		done     = 2
	)
	state := map[string]int{}
	var path []string
	var visit func(key string) []string
	visit = func(key string) []string {
		state[key] = visiting
		path = append(path, key)
		for _, to := range next[key] {
			switch state[to] {
			case visiting:
				start := 0
				for path[start] != to {
					start++
				}
				return append(append([]string{}, path[start:]...), to)
			case 0:
				if cycle := visit(to); cycle != nil {
					return cycle
				}
			}
		}
		path = path[:len(path)-1]
		state[key] = done
		return nil
	}
	for _, key := range keys {
		if state[key] == 0 {
			if cycle := visit(key); cycle != nil {
				return cycle
			}
		}
	}
	return nil
}
