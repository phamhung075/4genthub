package contextpacks

import (
	"fmt"
	"regexp"
	"strings"
)

// Ref safety (OPR.0.5.0.3 §2, the one thing that must be right). Refs are PATH-LIKE
// MULTI-SEGMENT, so the single-component name check becomes a PER-SEGMENT check over the same
// charset: no traversal, no absolute, no empty segment, no whitespace/YAML/id injection — while
// enabling `packs/compaction-restore`-style refs. The version token stays a bounded,
// delimiter-free single token.

// One safe path segment: leading alnum, then alnum/._-; <=64 chars. The allowlist alone bans
// '/', whitespace, ':' and newlines — every traversal and YAML/id injection vector — and its
// leading-alnum rule rejects '.', '..' and dotfiles.
var safeSegment = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`)

// A bounded, delimiter-free version token: <=32 chars, no separator that could forge a store id.
var safeVersion = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$`)

// IsSafePackRef reports whether a path-like pack ref is one or more '/'-separated safe segments.
// An empty ref, an absolute path (empty leading segment), a double/trailing slash, a '.'/'..'
// segment, or any injection character in a segment is NOT safe.
func IsSafePackRef(ref string) bool {
	if len(ref) == 0 {
		return false
	}
	for _, segment := range strings.Split(ref, "/") {
		if segment == "" {
			return false // absolute leading, interior '//', or trailing '/'
		}
		if segment == "." || segment == ".." {
			return false // defensive (safeSegment already bans them)
		}
		if !safeSegment.MatchString(segment) {
			return false
		}
	}
	return true
}

// AssertSafePackRef is the throwing form for write/resolve sites: packs must stay inside the
// context store root.
func AssertSafePackRef(ref string) error {
	if IsSafePackRef(ref) {
		return nil
	}
	return fmt.Errorf("unsafe pack ref %q — a ref must be one or more '/'-separated segments, each "+
		"matching [A-Za-z0-9][A-Za-z0-9._-]{0,63} (no '.'/'..', no absolute path, no empty segment, "+
		"no whitespace or injection), so packs stay inside the context store root", ref)
}

// IsSafePackVersion reports whether a pack version is a single bounded token (no separators,
// whitespace, '@' or ':').
func IsSafePackVersion(version string) bool {
	return safeVersion.MatchString(version)
}
