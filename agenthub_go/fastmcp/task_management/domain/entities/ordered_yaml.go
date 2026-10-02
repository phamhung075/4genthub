package entities

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"math"
	"math/big"
	"regexp"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

// PyYAML (YAML 1.1) implicit resolvers for plain scalars.
var (
	yamlBoolRe  = regexp.MustCompile(`^(?:yes|Yes|YES|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$`)
	yamlFloatRe = regexp.MustCompile(`^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$`)
	yamlIntRe   = regexp.MustCompile(`^(?:[-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$`)
	yamlNullRe  = regexp.MustCompile(`^(?:~|null|Null|NULL|)$`)
	yamlTimeRe  = regexp.MustCompile(`^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]|[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?(?:[Tt]|[ \t]+)[0-9][0-9]?:[0-9][0-9]:[0-9][0-9](?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$`)
)

// LoadYAML is yaml.safe_load for one document: mappings become *OrderedMap[any] (merge
// keys expanded first, like PyYAML), sequences []any, plain scalars are resolved with the
// YAML 1.1 rules PyYAML uses (yes/no/on/off booleans, 0755 octal, 1_000, sexagesimal),
// quoted scalars are strings. Timestamps stay strings (PyYAML returns date/datetime) and
// non-string mapping keys are converted to their JSON key text; anchors and aliases are
// resolved. Empty input is nil. More than one document is an error, like safe_load.
func LoadYAML(data []byte) (any, error) {
	dec := yaml.NewDecoder(bytes.NewReader(data))
	var doc yaml.Node
	if err := dec.Decode(&doc); err != nil {
		if err == io.EOF {
			return nil, nil
		}
		return nil, err
	}
	var extra yaml.Node
	if err := dec.Decode(&extra); err != io.EOF {
		if err != nil {
			return nil, err
		}
		return nil, errors.New("expected a single document in the stream")
	}
	c := &yamlConv{memo: map[*yaml.Node]any{}, inProgress: map[*yaml.Node]bool{}}
	return c.convert(doc.Content[0])
}

// yamlConv converts a node tree. Anchored nodes are converted once and shared by every
// alias (like PyYAML, which shares the object), so an alias-expansion bomb costs nothing;
// an alias to a node that is still being converted is a cycle and an error.
type yamlConv struct {
	memo       map[*yaml.Node]any
	inProgress map[*yaml.Node]bool
}

func (c *yamlConv) convert(n *yaml.Node) (any, error) {
	if n.Anchor != "" && n.Kind != yaml.AliasNode {
		if v, ok := c.memo[n]; ok {
			return v, nil
		}
		if c.inProgress[n] {
			return nil, errors.New("recursive aliases are not supported")
		}
		c.inProgress[n] = true
		v, err := c.convertNode(n)
		delete(c.inProgress, n)
		if err == nil {
			c.memo[n] = v
		}
		return v, err
	}
	return c.convertNode(n)
}

func (c *yamlConv) convertNode(n *yaml.Node) (any, error) {
	switch n.Kind {
	case yaml.AliasNode:
		return c.convert(n.Alias)
	case yaml.SequenceNode:
		list := make([]any, 0, len(n.Content))
		for _, child := range n.Content {
			v, err := c.convert(child)
			if err != nil {
				return nil, err
			}
			list = append(list, v)
		}
		return list, nil
	case yaml.MappingNode:
		return c.mapping(n)
	case yaml.ScalarNode:
		return yamlScalar(n)
	}
	return nil, fmt.Errorf("unsupported YAML node kind %d", n.Kind)
}

func yamlIsMerge(k *yaml.Node) bool {
	return k.Kind == yaml.ScalarNode && k.Style&yaml.TaggedStyle == 0 && k.Value == "<<" && k.Style&(yaml.SingleQuotedStyle|yaml.DoubleQuotedStyle) == 0
}

func (c *yamlConv) mapping(n *yaml.Node) (any, error) {
	type pair struct {
		key, ident string
		val        any
	}
	// PyYAML's flatten_mapping puts the merged entries before the explicit ones.
	var merged, explicit []pair
	for i := 0; i+1 < len(n.Content); i += 2 {
		k, v := n.Content[i], n.Content[i+1]
		if !yamlIsMerge(k) {
			key, ident, err := c.key(k)
			if err != nil {
				return nil, err
			}
			val, err := c.convert(v)
			if err != nil {
				return nil, err
			}
			explicit = append(explicit, pair{key, ident, val})
			continue
		}
		src := v
		if src.Kind == yaml.AliasNode {
			src = src.Alias
		}
		var maps []*yaml.Node
		switch src.Kind {
		case yaml.MappingNode:
			maps = []*yaml.Node{src}
		case yaml.SequenceNode:
			for _, m := range src.Content {
				if m.Kind == yaml.AliasNode {
					m = m.Alias
				}
				if m.Kind != yaml.MappingNode {
					return nil, fmt.Errorf("expected a mapping for merging, but found %d", m.Kind)
				}
				maps = append(maps, m)
			}
		default:
			return nil, fmt.Errorf("expected a mapping or list of mappings for merging, but found %d", src.Kind)
		}
		// With a sequence the earlier mapping wins, so the last one is applied first.
		for j := len(maps) - 1; j >= 0; j-- {
			sub, err := c.convert(maps[j])
			if err != nil {
				return nil, err
			}
			om := sub.(*OrderedMap[any])
			for _, key := range om.Keys() {
				val, _ := om.Get(key)
				merged = append(merged, pair{key, "s:" + key, val})
			}
		}
	}
	// Python dict keys that compare equal (1, 1.0, True; 0, 0.0, False) are one key: the
	// first spelling keeps its position and the last value wins.
	om := NewOrderedMap[any]()
	first := map[string]string{}
	for _, p := range append(merged, explicit...) {
		if k, ok := first[p.ident]; ok {
			om.Set(k, p.val)
			continue
		}
		first[p.ident] = p.key
		om.Set(p.key, p.val)
	}
	return om, nil
}

// key is a mapping key as text (strings as-is, other scalars as json.dumps writes them as
// dict keys) and its Python dict identity.
func (c *yamlConv) key(k *yaml.Node) (string, string, error) {
	// A plain '=' (the YAML value tag) has no constructor as a value but loads as the
	// string '=' as a mapping key.
	if k.Kind == yaml.ScalarNode && k.Value == "=" && k.Style&(yaml.TaggedStyle|yaml.SingleQuotedStyle|yaml.DoubleQuotedStyle|yaml.LiteralStyle|yaml.FoldedStyle) == 0 {
		return "=", "s:=", nil
	}
	v, err := c.convert(k)
	if err != nil {
		return "", "", err
	}
	switch x := v.(type) {
	case string:
		return x, "s:" + x, nil
	case bool:
		if x {
			return "true", "n:1", nil
		}
		return "false", "n:0", nil
	case nil:
		return "null", "None", nil
	case int64:
		return strconv.FormatInt(x, 10), "n:" + strconv.FormatInt(x, 10), nil
	case *big.Int:
		return x.String(), "n:" + x.String(), nil
	case float64:
		ident := "f:" + strconv.FormatFloat(x, 'g', -1, 64)
		if !math.IsNaN(x) && !math.IsInf(x, 0) && x == math.Trunc(x) {
			i, _ := new(big.Float).SetFloat64(x).Int(nil)
			ident = "n:" + i.String()
		}
		return yamlFloatKey(x), ident, nil
	}
	return "", "", fmt.Errorf("unhashable mapping key of type %T", v)
}

func yamlFloatKey(f float64) string {
	switch {
	case math.IsNaN(f):
		return "NaN"
	case math.IsInf(f, 1):
		return "Infinity"
	case math.IsInf(f, -1):
		return "-Infinity"
	}
	s := strconv.FormatFloat(f, 'g', -1, 64)
	if !strings.ContainsAny(s, ".eEn") {
		s += ".0"
	}
	return s
}

func yamlScalar(n *yaml.Node) (any, error) {
	if n.Style&yaml.TaggedStyle != 0 {
		switch n.Tag {
		case "!!str":
			return n.Value, nil
		case "!!int":
			return yamlInt(n.Value)
		case "!!float":
			return yamlFloat(n.Value), nil
		case "!!bool":
			return yamlBool(n.Value), nil
		case "!!null":
			return nil, nil
		}
		return nil, fmt.Errorf("could not determine a constructor for the tag %q", n.Tag)
	}
	if n.Style&(yaml.SingleQuotedStyle|yaml.DoubleQuotedStyle|yaml.LiteralStyle|yaml.FoldedStyle) != 0 {
		return n.Value, nil
	}
	s := n.Value
	switch {
	case yamlBoolRe.MatchString(s):
		return yamlBool(s), nil
	case yamlFloatRe.MatchString(s):
		return yamlFloat(s), nil
	case yamlIntRe.MatchString(s):
		return yamlInt(s)
	case s == "<<":
		return s, nil
	case yamlNullRe.MatchString(s):
		return nil, nil
	case yamlTimeRe.MatchString(s):
		return s, nil
	case s == "=":
		return nil, fmt.Errorf("could not determine a constructor for the tag %q", "tag:yaml.org,2002:value")
	}
	return s, nil
}

func yamlBool(s string) bool {
	switch strings.ToLower(s) {
	case "yes", "true", "on":
		return true
	}
	return false
}

func yamlSexagesimal(digits string, base int64) *big.Int {
	total := big.NewInt(0)
	mult := big.NewInt(1)
	parts := strings.Split(digits, ":")
	for i := len(parts) - 1; i >= 0; i-- {
		p, _ := strconv.ParseInt(parts[i], 10, 64)
		total.Add(total, new(big.Int).Mul(big.NewInt(p), mult))
		mult.Mul(mult, big.NewInt(base))
	}
	return total
}

// yamlInt is PyYAML's construct_yaml_int. Values beyond int64 are kept as *big.Int.
func yamlInt(s string) (any, error) {
	v := strings.ReplaceAll(s, "_", "")
	sign := int64(1)
	if v != "" && (v[0] == '-' || v[0] == '+') {
		if v[0] == '-' {
			sign = -1
		}
		v = v[1:]
	}
	var n *big.Int
	var ok bool
	switch {
	case v == "0":
		n = big.NewInt(0)
	case strings.HasPrefix(v, "0b"):
		n, ok = new(big.Int).SetString(v[2:], 2)
	case strings.HasPrefix(v, "0x"):
		n, ok = new(big.Int).SetString(v[2:], 16)
	case strings.HasPrefix(v, "0"):
		n, ok = new(big.Int).SetString(v[1:], 8)
	case strings.Contains(v, ":"):
		n, ok = yamlSexagesimal(v, 60), true
	default:
		n, ok = new(big.Int).SetString(v, 10)
	}
	if n == nil || (!ok && v != "0") {
		return nil, fmt.Errorf("invalid literal for int(): %q", s)
	}
	n.Mul(n, big.NewInt(sign))
	if n.IsInt64() {
		return n.Int64(), nil
	}
	return n, nil
}

// yamlFloat is PyYAML's construct_yaml_float.
func yamlFloat(s string) float64 {
	v := strings.ToLower(strings.ReplaceAll(s, "_", ""))
	sign := 1.0
	if v != "" && (v[0] == '-' || v[0] == '+') {
		if v[0] == '-' {
			sign = -1
		}
		v = v[1:]
	}
	switch v {
	case ".inf":
		return sign * math.Inf(1)
	case ".nan":
		return math.NaN()
	}
	if strings.Contains(v, ":") {
		parts := strings.Split(v, ":")
		total, mult := 0.0, 1.0
		for i := len(parts) - 1; i >= 0; i-- {
			p, _ := strconv.ParseFloat(parts[i], 64)
			total += p * mult
			mult *= 60
		}
		return sign * total
	}
	f, _ := strconv.ParseFloat(v, 64)
	return sign * f
}
