package entities

// fnmatch mirrors Python's fnmatch.fnmatch on POSIX (case-sensitive, no path
// awareness): "*" matches any run including "/", "?" one rune, "[seq]" and
// "[!seq]" sets with ranges; an unterminated "[" is a literal.
func fnmatch(name, pattern string) bool {
	return fnmatchRunes([]rune(name), []rune(pattern))
}

func fnmatchRunes(n, p []rune) bool {
	for len(p) > 0 {
		switch p[0] {
		case '*':
			for len(p) > 0 && p[0] == '*' {
				p = p[1:]
			}
			if len(p) == 0 {
				return true
			}
			for i := 0; i <= len(n); i++ {
				if fnmatchRunes(n[i:], p) {
					return true
				}
			}
			return false
		case '?':
			if len(n) == 0 {
				return false
			}
			n, p = n[1:], p[1:]
		case '[':
			set, rest, ok := parseFnmatchSet(p)
			if !ok {
				if len(n) == 0 || n[0] != '[' {
					return false
				}
				n, p = n[1:], p[1:]
				continue
			}
			if len(n) == 0 || !set.matches(n[0]) {
				return false
			}
			n, p = n[1:], rest
		default:
			if len(n) == 0 || n[0] != p[0] {
				return false
			}
			n, p = n[1:], p[1:]
		}
	}
	return len(n) == 0
}

type fnmatchSet struct {
	negate bool
	ranges [][2]rune
}

func (s fnmatchSet) matches(c rune) bool {
	in := false
	for _, r := range s.ranges {
		if c >= r[0] && c <= r[1] {
			in = true
			break
		}
	}
	return in != s.negate
}

// parseFnmatchSet parses a set starting at p[0]=='['; ok is false when the set
// is unterminated (the "[" is then literal).
func parseFnmatchSet(p []rune) (fnmatchSet, []rune, bool) {
	j := 1
	if j < len(p) && p[j] == '!' {
		j++
	}
	if j < len(p) && p[j] == ']' {
		j++
	}
	for j < len(p) && p[j] != ']' {
		j++
	}
	if j >= len(p) {
		return fnmatchSet{}, nil, false
	}
	stuff := p[1:j]
	var s fnmatchSet
	if len(stuff) > 0 && stuff[0] == '!' {
		s.negate = true
		stuff = stuff[1:]
	}
	for k := 0; k < len(stuff); {
		if k+2 < len(stuff) && stuff[k+1] == '-' {
			s.ranges = append(s.ranges, [2]rune{stuff[k], stuff[k+2]})
			k += 3
		} else {
			s.ranges = append(s.ranges, [2]rune{stuff[k], stuff[k]})
			k++
		}
	}
	return s, p[j+1:], true
}
