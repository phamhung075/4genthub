package utilities

import "strings"

// PyPath normalises a path string the way pathlib.PurePosixPath does: repeated slashes
// collapse (exactly two leading slashes are kept), "." components vanish and ".." is kept
// (unlike filepath.Clean); the empty path is ".".
func PyPath(p string) string {
	if p == "" {
		return "."
	}
	prefix := ""
	switch {
	case strings.HasPrefix(p, "//") && !strings.HasPrefix(p, "///"):
		prefix = "//"
	case strings.HasPrefix(p, "/"):
		prefix = "/"
	}
	var parts []string
	for _, c := range strings.Split(p, "/") {
		if c != "" && c != "." {
			parts = append(parts, c)
		}
	}
	if len(parts) == 0 {
		if prefix == "" {
			return "."
		}
		return prefix
	}
	return prefix + strings.Join(parts, "/")
}

// PyIsAbs is os.path.isabs.
func PyIsAbs(p string) bool { return strings.HasPrefix(p, "/") }

// PyJoin is `base / rel` on pathlib paths: an absolute rel replaces base.
func PyJoin(base string, rel ...string) string {
	cur := PyPath(base)
	for _, r := range rel {
		if PyIsAbs(r) {
			cur = PyPath(r)
		} else if r != "" {
			sep := "/"
			if strings.HasSuffix(cur, "/") {
				sep = ""
			}
			cur = PyPath(cur + sep + r)
		}
	}
	return cur
}

// PyParent is Path.parent (the root and "." are their own parent).
func PyParent(p string) string {
	p = PyPath(p)
	root := ""
	switch {
	case strings.HasPrefix(p, "//"):
		root = "//"
	case strings.HasPrefix(p, "/"):
		root = "/"
	}
	rest := p[len(root):]
	if rest == "" {
		return p
	}
	i := strings.LastIndex(rest, "/")
	switch {
	case i >= 0:
		return root + rest[:i]
	case root != "":
		return root
	}
	return "."
}

// PyName is Path.name.
func PyName(p string) string {
	p = PyPath(p)
	if p == "." || strings.Trim(p, "/") == "" {
		return ""
	}
	return p[strings.LastIndex(p, "/")+1:]
}
