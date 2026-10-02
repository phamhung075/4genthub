package pyyaml

import (
	"regexp"
	"strings"
)

// Resolver (resolver.py). Only the implicit resolvers matter for the dumper pipeline
// (there are no path resolvers), and they decide which plain scalars would be re-read
// as a non-string tag, which in turn decides quoting.

const (
	defaultScalarTag   = "tag:yaml.org,2002:str"
	defaultSequenceTag = "tag:yaml.org,2002:seq"
	defaultMappingTag  = "tag:yaml.org,2002:map"

	boolTag      = "tag:yaml.org,2002:bool"
	floatTag     = "tag:yaml.org,2002:float"
	intTag       = "tag:yaml.org,2002:int"
	mergeTag     = "tag:yaml.org,2002:merge"
	nullTag      = "tag:yaml.org,2002:null"
	timestampTag = "tag:yaml.org,2002:timestamp"
	valueTag     = "tag:yaml.org,2002:value"
	yamlTag      = "tag:yaml.org,2002:yaml"
)

type implicitResolver struct {
	tag string
	re  *regexp.Regexp
}

// first-map from a leading character (or "" for an empty scalar) to the resolvers
// registered for it, in add_implicit_resolver order.
var implicitResolvers = map[string][]implicitResolver{}

func addImplicitResolver(tag string, re *regexp.Regexp, first []string) {
	for _, ch := range first {
		implicitResolvers[ch] = append(implicitResolvers[ch], implicitResolver{tag: tag, re: re})
	}
}

func init() {
	addImplicitResolver(boolTag, regexp.MustCompile(`^(?:yes|Yes|YES|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$`), []string{"y", "Y", "n", "N", "t", "T", "f", "F", "o", "O"})
	addImplicitResolver(floatTag, regexp.MustCompile(`^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$`), []string{"-", "+", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."})
	addImplicitResolver(intTag, regexp.MustCompile(`^(?:[-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$`), []string{"-", "+", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"})
	addImplicitResolver(mergeTag, regexp.MustCompile(`^(?:<<)$`), []string{"<"})
	addImplicitResolver(nullTag, regexp.MustCompile(`^(?:~|null|Null|NULL|)$`), []string{"~", "n", "N", ""})
	addImplicitResolver(timestampTag, regexp.MustCompile(`^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]|[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?(?:[Tt]|[ \t]+)[0-9][0-9]?:[0-9][0-9]:[0-9][0-9](?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$`), []string{"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"})
	addImplicitResolver(valueTag, regexp.MustCompile(`^(?:=)$`), []string{"="})
	addImplicitResolver(yamlTag, regexp.MustCompile(`^(?:!|&|\*)$`), []string{"!", "&", "*"})
}

type resolver struct{}

var defaultResolver = &resolver{}

// pyReMatch is re.match: the patterns start with ^; Python's $ also matches just before a
// single trailing newline, while Go's $ is end-of-text, so retry without that newline.
func pyReMatch(re *regexp.Regexp, s string) bool {
	if re.MatchString(s) {
		return true
	}
	if strings.HasSuffix(s, "\n") {
		return re.MatchString(s[:len(s)-1])
	}
	return false
}

// resolveScalar is BaseResolver.resolve for a ScalarNode: with implicit false it returns
// the default scalar tag; with implicit true it tries the first-character resolvers.
func (r *resolver) resolveScalar(value string, implicit bool) string {
	if implicit {
		first := ""
		runes := []rune(value)
		if len(runes) > 0 {
			first = string(runes[0])
		}
		for _, res := range implicitResolvers[first] {
			if pyReMatch(res.re, value) {
				return res.tag
			}
		}
	}
	return defaultScalarTag
}
