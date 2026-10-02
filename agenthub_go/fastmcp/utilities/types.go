package utilities

import (
	"encoding/base64"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The MCP content objects returned by Image/Audio/File. The mcp.types models are not
// part of this slice, so these carry the same fields (and JSON names) as the Python
// pydantic objects; annotations stay an opaque pass-through value.

// ImageContent mirrors mcp.types.ImageContent (field order matches its model_fields).
type ImageContent struct {
	Type        string `json:"type"`
	Data        string `json:"data"`
	MimeType    string `json:"mimeType"`
	Annotations any    `json:"annotations"`
	Meta        any    `json:"meta"`
}

// AudioContent mirrors mcp.types.AudioContent.
type AudioContent struct {
	Type        string `json:"type"`
	Data        string `json:"data"`
	MimeType    string `json:"mimeType"`
	Annotations any    `json:"annotations"`
	Meta        any    `json:"meta"`
}

// TextResourceContents mirrors mcp.types.TextResourceContents.
type TextResourceContents struct {
	URI      string `json:"uri"`
	MimeType string `json:"mimeType"`
	Meta     any    `json:"meta"`
	Text     string `json:"text"`
}

// BlobResourceContents mirrors mcp.types.BlobResourceContents.
type BlobResourceContents struct {
	URI      string `json:"uri"`
	MimeType string `json:"mimeType"`
	Meta     any    `json:"meta"`
	Blob     string `json:"blob"`
}

// EmbeddedResource mirrors mcp.types.EmbeddedResource.
type EmbeddedResource struct {
	Type        string `json:"type"`
	Resource    any    `json:"resource"`
	Annotations any    `json:"annotations"`
	Meta        any    `json:"meta"`
}

// pySuffix mirrors pathlib.PurePath.suffix (leading dots are stripped first).
func pySuffix(name string) string {
	name = strings.TrimLeft(name, ".")
	if i := strings.LastIndex(name, "."); i != -1 {
		return name[i:]
	}
	return ""
}

// Image mirrors utilities.types.Image.
type Image struct {
	Path        *string
	Data        []byte
	Annotations any
	format      *string
	mimeType    string
}

// NewImage mirrors Image.__init__.
func NewImage(path *string, data []byte, format *string, annotations any) (*Image, error) {
	if path == nil && data == nil {
		return nil, value_objects.ValueErrorf("Either path or data must be provided")
	}
	if path != nil && data != nil {
		return nil, value_objects.ValueErrorf("Only one of path or data can be provided")
	}
	img := &Image{Data: data, format: format, Annotations: annotations}
	if path != nil && *path != "" {
		img.Path = path
	}
	img.mimeType = img.getMimeType()
	return img, nil
}

func (i *Image) getMimeType() string {
	if i.format != nil && *i.format != "" {
		return "image/" + value_objects.PyLower(*i.format)
	}
	if i.Path != nil {
		suffix := value_objects.PyLower(pySuffix(PyName(*i.Path)))
		switch suffix {
		case ".png":
			return "image/png"
		case ".jpg", ".jpeg":
			return "image/jpeg"
		case ".gif":
			return "image/gif"
		case ".webp":
			return "image/webp"
		}
		return "application/octet-stream"
	}
	return "image/png"
}

// ToImageContent mirrors to_image_content.
func (i *Image) ToImageContent(mimeType *string, annotations any) (*ImageContent, error) {
	var data string
	switch {
	case i.Path != nil:
		raw, err := os.ReadFile(*i.Path)
		if err != nil {
			return nil, err
		}
		data = base64.StdEncoding.EncodeToString(raw)
	case i.Data != nil:
		data = base64.StdEncoding.EncodeToString(i.Data)
	default:
		return nil, value_objects.ValueErrorf("No image data available")
	}
	mime := orString(mimeType, i.mimeType)
	return &ImageContent{Type: "image", Data: data, MimeType: mime, Annotations: orAnnotations(annotations, i.Annotations)}, nil
}

// Audio mirrors utilities.types.Audio.
type Audio struct {
	Path        *string
	Data        []byte
	Annotations any
	format      *string
	mimeType    string
}

// NewAudio mirrors Audio.__init__.
func NewAudio(path *string, data []byte, format *string, annotations any) (*Audio, error) {
	if path == nil && data == nil {
		return nil, value_objects.ValueErrorf("Either path or data must be provided")
	}
	if path != nil && data != nil {
		return nil, value_objects.ValueErrorf("Only one of path or data can be provided")
	}
	a := &Audio{Data: data, format: format, Annotations: annotations}
	if path != nil && *path != "" {
		a.Path = path
	}
	a.mimeType = a.getMimeType()
	return a, nil
}

func (a *Audio) getMimeType() string {
	if a.format != nil && *a.format != "" {
		return "audio/" + value_objects.PyLower(*a.format)
	}
	if a.Path != nil {
		suffix := value_objects.PyLower(pySuffix(PyName(*a.Path)))
		switch suffix {
		case ".wav":
			return "audio/wav"
		case ".mp3":
			return "audio/mpeg"
		case ".ogg":
			return "audio/ogg"
		case ".m4a":
			return "audio/mp4"
		case ".flac":
			return "audio/flac"
		}
		return "application/octet-stream"
	}
	return "audio/wav"
}

// ToAudioContent mirrors to_audio_content.
func (a *Audio) ToAudioContent(mimeType *string, annotations any) (*AudioContent, error) {
	var data string
	switch {
	case a.Path != nil:
		raw, err := os.ReadFile(*a.Path)
		if err != nil {
			return nil, err
		}
		data = base64.StdEncoding.EncodeToString(raw)
	case a.Data != nil:
		data = base64.StdEncoding.EncodeToString(a.Data)
	default:
		return nil, value_objects.ValueErrorf("No audio data available")
	}
	mime := orString(mimeType, a.mimeType)
	return &AudioContent{Type: "audio", Data: data, MimeType: mime, Annotations: orAnnotations(annotations, a.Annotations)}, nil
}

// File mirrors utilities.types.File.
type File struct {
	Path        *string
	Data        []byte
	Annotations any
	format      *string
	mimeType    string
	name        *string
}

// NewFile mirrors File.__init__.
func NewFile(path *string, data []byte, format *string, name *string, annotations any) (*File, error) {
	if path == nil && data == nil {
		return nil, value_objects.ValueErrorf("Either path or data must be provided")
	}
	if path != nil && data != nil {
		return nil, value_objects.ValueErrorf("Only one of path or data can be provided")
	}
	f := &File{Data: data, format: format, name: name, Annotations: annotations}
	if path != nil && *path != "" {
		f.Path = path
	}
	mt, err := f.getMimeType()
	if err != nil {
		return nil, err
	}
	f.mimeType = mt
	return f, nil
}

func (f *File) getMimeType() (string, error) {
	if f.format != nil && *f.format != "" {
		fmtName := value_objects.PyLower(*f.format)
		switch fmtName {
		case "plain", "txt", "text":
			return "text/plain", nil
		}
		return "application/" + fmtName, nil
	}
	if f.Path != nil {
		mt, _, err := GuessType(*f.Path)
		if err != nil {
			return "", err
		}
		if mt != nil && *mt != "" {
			return *mt, nil
		}
	}
	return "application/octet-stream", nil
}

// ToResourceContent mirrors to_resource_content.
func (f *File) ToResourceContent(mimeType *string, annotations any) (*EmbeddedResource, error) {
	var raw []byte
	var uriStr string
	switch {
	case f.Path != nil:
		b, err := os.ReadFile(*f.Path)
		if err != nil {
			return nil, err
		}
		raw = b
		uriStr = normalizeFileURL(fileURI(*f.Path))
	case f.Data != nil:
		raw = f.Data
		slash := strings.IndexByte(f.mimeType, '/')
		if slash < 0 {
			return nil, fmt.Errorf("index out of range")
		}
		ext := f.mimeType[slash+1:]
		if f.name != nil && *f.name != "" {
			uriStr = "file:///" + *f.name + "." + ext
		} else {
			uriStr = "file:///resource." + ext
		}
		uriStr = normalizeFileURL(uriStr)
	default:
		return nil, value_objects.ValueErrorf("No resource data available")
	}
	mime := orString(mimeType, f.mimeType)

	var resource any
	if strings.HasPrefix(mime, "text/") {
		resource = &TextResourceContents{Text: decodeText(raw), MimeType: mime, URI: uriStr}
	} else {
		resource = &BlobResourceContents{Blob: base64.StdEncoding.EncodeToString(raw), MimeType: mime, URI: uriStr}
	}
	return &EmbeddedResource{Type: "resource", Resource: resource, Annotations: orAnnotations(annotations, f.Annotations)}, nil
}

// fileURI mirrors Path.resolve().as_uri().
func fileURI(path string) string {
	abs := path
	if resolved, err := filepath.EvalSymlinks(path); err == nil {
		abs = resolved
	} else if a, err := filepath.Abs(path); err == nil {
		abs = a
	}
	return "file://" + PyQuote(abs)
}

// decodeText is raw.decode("utf-8") with a latin-1 fallback.
func decodeText(raw []byte) string {
	if utf8.Valid(raw) {
		return string(raw)
	}
	var b strings.Builder
	for _, c := range raw {
		b.WriteRune(rune(c))
	}
	return b.String()
}

// orString is Python's `a or b` for optional strings.
func orString(a *string, b string) string {
	if a != nil && *a != "" {
		return *a
	}
	return b
}

// orAnnotations is Python's `a or b` using truthiness.
func orAnnotations(a, b any) any {
	if value_objects.PyTruthy(a) {
		return a
	}
	return b
}
