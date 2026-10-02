package services

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// decodeOrdered decodes JSON keeping object key order (*OrderedMap[any]), ints as int64
// and floats as float64, like Python's json.loads.
func decodeOrdered(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch v := tok.(type) {
	case json.Delim:
		if v == '{' {
			m := entities.NewOrderedMap[any]()
			for dec.More() {
				k, _ := dec.Token()
				val, err := decodeOrdered(dec)
				if err != nil {
					return nil, err
				}
				m.Set(k.(string), val)
			}
			_, _ = dec.Token()
			return m, nil
		}
		arr := []any{}
		for dec.More() {
			val, err := decodeOrdered(dec)
			if err != nil {
				return nil, err
			}
			arr = append(arr, val)
		}
		_, _ = dec.Token()
		return arr, nil
	case json.Number:
		if strings.ContainsAny(string(v), ".eE") {
			f, _ := v.Float64()
			return f, nil
		}
		n, _ := v.Int64()
		return n, nil
	}
	return tok, nil
}

func loadOrdered(t *testing.T, path string) *entities.OrderedMap[any] {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	v, err := decodeOrdered(dec)
	if err != nil && err != io.EOF {
		t.Fatal(err)
	}
	return v.(*entities.OrderedMap[any])
}

func field(m any, k string) any { v, _ := m.(*entities.OrderedMap[any]).Get(k); return v }

func strList(v any) []string {
	out := []string{}
	for _, x := range v.([]any) {
		out = append(out, x.(string))
	}
	return out
}

func ordStrings(v any) *entities.OrderedMap[string] {
	out := entities.NewOrderedMap[string]()
	m := v.(*entities.OrderedMap[any])
	for _, k := range m.Keys() {
		s, _ := m.Get(k)
		out.Set(k, s.(string))
	}
	return out
}

func buildRule(t *testing.T, spec any) *entities.RuleContent {
	t.Helper()
	md := entities.NewRuleMetadata(field(spec, "path").(string), value_objects.RuleFormatMd,
		value_objects.RuleType(field(spec, "typ").(string)), 1, 1.0, "c", []string{})
	return &entities.RuleContent{Metadata: md, RawContent: field(spec, "raw").(string),
		ParsedContent: field(spec, "parsed").(*entities.OrderedMap[any]), Sections: ordStrings(field(spec, "sections")),
		References: []string{}, Variables: field(spec, "variables").(*entities.OrderedMap[any])}
}

func dumps(t *testing.T, v any) string {
	t.Helper()
	s, err := value_objects.PyJSONDumps(v, 2)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestRuleCompositionMatchesPython(t *testing.T) {
	fx := loadOrdered(t, "testdata/rule_composition_cases.json")
	specs := field(fx, "rules")
	build := func(names any) []*entities.RuleContent {
		var rs []*entities.RuleContent
		for _, n := range strList(names) {
			rs = append(rs, buildRule(t, field(specs, n)))
		}
		return rs
	}
	compared := 0
	for _, c := range field(fx, "cases").([]any) {
		compared++
		conf := value_objects.ConflictResolution(field(c, "conf").(string))
		svc := NewRuleCompositionService(conf)
		if want := field(c, "resolve"); want != nil {
			got := svc.ResolveConflicts(build(field(c, "names")))
			// Python builds dicts in insertion order; Go maps print sorted, so compare sorted renderings.
			if dumps(t, got) != dumps(t, sortedCopy(want)) {
				t.Errorf("resolve %v %s:\n got %s\nwant %s", field(c, "names"), conf, dumps(t, got), dumps(t, sortedCopy(want)))
			}
			continue
		}
		label := strings.Join(strList(field(c, "names")), ",") + "/" + string(conf) + "/" + field(c, "strat").(string) + "/" + field(c, "fmt").(string)
		got := svc.ComposeRules(build(field(c, "names")), value_objects.RuleFormat(field(c, "fmt").(string)), field(c, "strat").(string))
		w := field(c, "want")
		if got.ComposedContent != field(w, "composed") || got.Success != field(w, "success") {
			t.Errorf("%s: success=%v composed %q want success=%v %q", label, got.Success, got.ComposedContent, field(w, "success"), field(w, "composed"))
			continue
		}
		if !equalStrings(got.SourceRules, strList(field(w, "sources"))) || !equalStrings(got.ConflictsResolved, strList(field(w, "conflicts"))) ||
			!equalStrings(got.Warnings, strList(field(w, "warnings"))) {
			t.Errorf("%s: sources/conflicts/warnings differ: %v %v %v", label, got.SourceRules, got.ConflictsResolved, got.Warnings)
		}
		meta := map[string]any{}
		for k, v := range got.CompositionMetadata {
			if k != "timestamp" {
				meta[k] = v
			}
		}
		if _, hasTS := got.CompositionMetadata["timestamp"]; hasTS != field(w, "has_ts") {
			t.Errorf("%s: timestamp presence", label)
		}
		if dumps(t, meta) != dumps(t, sortedCopy(field(w, "meta"))) {
			t.Errorf("%s: meta %s want %s", label, dumps(t, meta), dumps(t, sortedCopy(field(w, "meta"))))
		}
		chain := field(w, "chain").([]any)
		if len(got.InheritanceChain) != len(chain) {
			t.Errorf("%s: chain len %d want %d", label, len(got.InheritanceChain), len(chain))
			continue
		}
		for i, inh := range got.InheritanceChain {
			wc := chain[i]
			merged := entities.NewOrderedMap[any]()
			for _, k := range sortedAnyKeys(inh.MergedVariables) {
				merged.Set(k, inh.MergedVariables[k])
			}
			if inh.ParentPath != field(wc, "parent") || inh.ChildPath != field(wc, "child") ||
				string(inh.InheritanceType) != field(wc, "type") || !equalStrings(inh.InheritedSections, strList(field(wc, "inherited"))) ||
				int64(inh.InheritanceDepth) != field(wc, "depth") || dumps(t, merged) != dumps(t, sortedCopy(field(wc, "merged"))) {
				t.Errorf("%s: chain[%d] %+v want %v", label, i, inh, wc)
			}
		}
	}
	if compared < 400 {
		t.Fatalf("only %d fixture cases compared", compared)
	}
}

func TestMergeSectionContentMatchesPython(t *testing.T) {
	fx := loadOrdered(t, "testdata/rule_composition_cases.json")
	svc := NewRuleCompositionService(value_objects.ConflictResolutionMerge)
	for _, m := range field(fx, "merges").([]any) {
		a := m.([]any)
		if got := svc.MergeSectionContent(a[0].(string), a[1].(string)); got != a[2].(string) {
			t.Errorf("merge(%q,%q) = %q want %q", a[0], a[1], got, a[2])
		}
	}
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func sortedAnyKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sortStringsAsc(keys)
	return keys
}

func sortStringsAsc(s []string) {
	for i := 1; i < len(s); i++ {
		for j := i; j > 0 && s[j] < s[j-1]; j-- {
			s[j], s[j-1] = s[j-1], s[j]
		}
	}
}

// sortedCopy re-keys every ordered map in v with sorted keys, so a Python dict (insertion
// order) can be compared with a Go map[string]any (printed sorted).
func sortedCopy(v any) any {
	switch x := v.(type) {
	case *entities.OrderedMap[any]:
		keys := x.Keys()
		sortStringsAsc(keys)
		out := entities.NewOrderedMap[any]()
		for _, k := range keys {
			e, _ := x.Get(k)
			out.Set(k, sortedCopy(e))
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i := range x {
			out[i] = sortedCopy(x[i])
		}
		return out
	}
	return v
}
