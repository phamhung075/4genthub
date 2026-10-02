package utilities

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestImageFromData(t *testing.T) {
	img, err := NewImage(nil, []byte("abc"), strPtr("PNG"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if img.mimeType != "image/png" {
		t.Fatalf("mimeType = %q", img.mimeType)
	}
	content, err := img.ToImageContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if content.Type != "image" || content.MimeType != "image/png" || content.Data != base64.StdEncoding.EncodeToString([]byte("abc")) {
		t.Fatalf("content = %+v", content)
	}
}

func TestImageFromPathExtension(t *testing.T) {
	path := filepath.Join(t.TempDir(), "pic.GIF")
	if err := os.WriteFile(path, []byte{0x47, 0x49, 0x46}, 0o600); err != nil {
		t.Fatal(err)
	}
	img, err := NewImage(&path, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if img.mimeType != "image/gif" {
		t.Fatalf("mimeType = %q", img.mimeType)
	}
	content, err := img.ToImageContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if content.Data != base64.StdEncoding.EncodeToString([]byte{0x47, 0x49, 0x46}) {
		t.Fatalf("data = %q", content.Data)
	}
}

func TestImageValidation(t *testing.T) {
	if _, err := NewImage(nil, nil, nil, nil); err == nil {
		t.Fatal("expected ValueError for no path and no data")
	}
	if _, err := NewImage(strPtr("x.png"), []byte("z"), nil, nil); err == nil {
		t.Fatal("expected ValueError for both path and data")
	}
	// path="" is falsy in Python, so it becomes None and then fails to produce content.
	empty := ""
	img, err := NewImage(&empty, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if img.Path != nil {
		t.Fatal("empty path should become nil")
	}
	if _, err := img.ToImageContent(nil, nil); err == nil {
		t.Fatal("expected 'No image data available'")
	}
}

func TestAudioDefaultAndToContent(t *testing.T) {
	audio, err := NewAudio(nil, []byte("x"), nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if audio.mimeType != "audio/wav" {
		t.Fatalf("default mimeType = %q", audio.mimeType)
	}
	content, err := audio.ToAudioContent(strPtr("mp3"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if content.Type != "audio" || content.MimeType != "mp3" {
		t.Fatalf("content = %+v", content)
	}
	mpeg, err := NewAudio(nil, []byte("x"), strPtr("MP3"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if mpeg.mimeType != "audio/mp3" {
		t.Fatalf("mimeType = %q", mpeg.mimeType)
	}
}

func TestFileTextResourceFromData(t *testing.T) {
	f, err := NewFile(nil, []byte("hello"), strPtr("txt"), strPtr("notes"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if f.mimeType != "text/plain" {
		t.Fatalf("mimeType = %q", f.mimeType)
	}
	res, err := f.ToResourceContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if res.Type != "resource" {
		t.Fatalf("type = %q", res.Type)
	}
	text, ok := res.Resource.(*TextResourceContents)
	if !ok {
		t.Fatalf("resource = %T", res.Resource)
	}
	if text.Text != "hello" || text.MimeType != "text/plain" || text.URI != "file:///notes.plain" {
		t.Fatalf("text resource = %+v", text)
	}
}

func TestFileBlobResourceFromData(t *testing.T) {
	f, err := NewFile(nil, []byte{0xff, 0x00}, strPtr("bin"), nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	res, err := f.ToResourceContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	blob, ok := res.Resource.(*BlobResourceContents)
	if !ok {
		t.Fatalf("resource = %T", res.Resource)
	}
	if blob.Blob != base64.StdEncoding.EncodeToString([]byte{0xff, 0x00}) || blob.URI != "file:///resource.bin" {
		t.Fatalf("blob resource = %+v", blob)
	}
}

func TestFileLatin1Fallback(t *testing.T) {
	f, err := NewFile(nil, []byte{0xe9}, strPtr("txt"), nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	res, err := f.ToResourceContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if res.Resource.(*TextResourceContents).Text != "é" {
		t.Fatalf("text = %q", res.Resource.(*TextResourceContents).Text)
	}
}

func TestFileResourceFromPath(t *testing.T) {
	path := filepath.Join(t.TempDir(), "sample.txt")
	if err := os.WriteFile(path, []byte("hi"), 0o600); err != nil {
		t.Fatal(err)
	}
	f, err := NewFile(&path, nil, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if f.mimeType != "text/plain" {
		t.Fatalf("mimeType = %q", f.mimeType)
	}
	res, err := f.ToResourceContent(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	text := res.Resource.(*TextResourceContents)
	if text.Text != "hi" || !strings.HasPrefix(text.URI, "file://") || !strings.HasSuffix(text.URI, "/sample.txt") {
		t.Fatalf("resource = %+v", text)
	}
}
