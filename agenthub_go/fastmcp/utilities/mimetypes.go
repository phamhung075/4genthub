package utilities

// Port of mimetypes.MimeTypes().guess_type (CPython 3.14) over its built-in tables. The Go
// side never reads host mime files, so results do not depend on /etc/mime.types.

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// posixSplitext is posixpath.splitext.
func posixSplitext(p string) (string, string) {
	sepIndex := strings.LastIndex(p, "/")
	dotIndex := strings.LastIndex(p, ".")
	if dotIndex > sepIndex {
		for i := sepIndex + 1; i < dotIndex; i++ {
			if p[i] != '.' {
				return p[:dotIndex], p[dotIndex:]
			}
		}
	}
	return p, ""
}

// GuessType returns (mime type, encoding); nil means None.
func GuessType(url string) (*string, *string, error) {
	scheme, path, err := pyURLSchemePath(url)
	if err != nil {
		return nil, nil, err
	}
	if scheme == "" || len(scheme) <= 1 {
		return guessFileType(url)
	}
	if scheme == "data" {
		comma := strings.Index(path, ",")
		if comma < 0 {
			return nil, nil, nil
		}
		typ := path[:comma]
		if semi := strings.Index(path[:comma], ";"); semi >= 0 {
			typ = path[:semi]
		}
		if strings.Contains(typ, "=") || !strings.Contains(typ, "/") {
			typ = "text/plain"
		}
		return &typ, nil, nil
	}
	return guessFileType(path)
}

func guessFileType(path string) (*string, *string, error) {
	base, ext := posixSplitext(path)
	for {
		repl, ok := mimeSuffixMap[value_objects.PyLower(ext)]
		if !ok {
			break
		}
		base, ext = posixSplitext(base + repl)
	}
	var encoding *string
	if enc, ok := mimeEncodingsMap[ext]; ok {
		encoding = &enc
		base, ext = posixSplitext(base)
	}
	_ = base
	if t, ok := mimeTypesMap[value_objects.PyLower(ext)]; ok {
		return &t, encoding, nil
	}
	return nil, encoding, nil
}
