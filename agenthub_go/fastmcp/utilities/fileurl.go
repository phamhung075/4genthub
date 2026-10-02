package utilities

import (
	"strings"
)

// PyQuote is urllib.parse.quote(s) with its default safe="/": every byte except ASCII
// letters, digits and "_.-~/" is percent-encoded (uppercase hex).
func PyQuote(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch {
		case c >= 'a' && c <= 'z', c >= 'A' && c <= 'Z', c >= '0' && c <= '9', c == '_', c == '.', c == '-', c == '~', c == '/':
			b.WriteByte(c)
		default:
			b.WriteString(pctByte(c))
		}
	}
	return b.String()
}

func pctByte(c byte) string {
	const hex = "0123456789ABCDEF"
	return string([]byte{'%', hex[c>>4], hex[c&15]})
}

// encodeSet percent-encodes the bytes of s that are C0 controls, non-ASCII, 0x7F, or listed in extra.
func encodeSet(s, extra string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c <= 0x20 || c >= 0x7F || strings.IndexByte(extra, c) >= 0 {
			b.WriteString(pctByte(c))
		} else {
			b.WriteByte(c)
		}
	}
	return b.String()
}

// normalizeFileURL applies the WHATWG URL parser normalisation that pydantic's AnyUrl
// (rust `url` crate) performs on a "file:///..." string: tab/CR/LF removal, backslash as
// separator, dot-segment removal, and percent-encoding of the path, query and fragment sets.
func normalizeFileURL(raw string) string {
	raw = strings.NewReplacer("\t", "", "\r", "", "\n", "").Replace(raw)
	rest := strings.TrimPrefix(raw, "file://")
	fragment, hasFragment := "", false
	if i := strings.IndexByte(rest, '#'); i >= 0 {
		rest, fragment, hasFragment = rest[:i], rest[i+1:], true
	}
	query, hasQuery := "", false
	if i := strings.IndexByte(rest, '?'); i >= 0 {
		rest, query, hasQuery = rest[:i], rest[i+1:], true
	}
	rest = strings.ReplaceAll(rest, "\\", "/")
	// Leading empty segments collapse (empirical, pydantic-core on file URLs).
	segments := strings.Split(strings.TrimLeft(rest, "/"), "/")
	var out []string
	for i, seg := range segments {
		last := i == len(segments)-1
		switch strings.ToLower(seg) {
		case ".", "%2e":
			if last {
				out = append(out, "")
			}
		case "..", ".%2e", "%2e.", "%2e%2e":
			if len(out) > 0 {
				out = out[:len(out)-1]
			}
			if last {
				out = append(out, "")
			}
		default:
			out = append(out, encodeSet(seg, "\"#<>?`{}"))
		}
	}
	result := "file:///" + strings.Join(out, "/")
	if hasQuery {
		result += "?" + encodeSet(query, "\"#<>'")
	}
	if hasFragment {
		result += "#" + encodeSet(fragment, "\"<>`")
	}
	return result
}
