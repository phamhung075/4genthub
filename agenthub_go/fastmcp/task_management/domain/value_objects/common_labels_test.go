package value_objects

import (
	"reflect"
	"testing"
)

func TestLabelValidator(t *testing.T) {
	v := LabelValidator{}
	if !v.IsValidLabel("bug") || !v.IsValidLabel("My Custom/Label") || v.IsValidLabel("bad-label") || v.IsValidLabel("a!b") || v.IsValidLabel("") {
		t.Fatal("IsValidLabel")
	}
	got, err := v.ValidateLabels([]string{" Foo Bar ", "", "x_y"})
	if err != nil || !reflect.DeepEqual(got, []string{"foo-bar", "x_y"}) {
		t.Fatal(got, err)
	}
	if _, err := v.ValidateLabels([]string{"a$"}); err == nil || err.Error() != "Invalid label format: a$ (use alphanumeric, hyphens, underscores only)" {
		t.Fatal(err)
	}
}

func TestSuggestLabels(t *testing.T) {
	got := SuggestLabels("Fix the login bug in the API")
	want := map[string]bool{"bug": true, "api": true, "auth": true, "backend": true, "integration": true}
	for _, g := range got {
		delete(want, g)
	}
	if len(want) != 0 {
		t.Fatal("missing", want, "got", got)
	}
	if n := len(LabelValidator{}.GetLabelSuggestions([]string{"bug"}, "Fix the login bug in the API")); n > 5 {
		t.Fatal(n)
	}
	if CommonLabelAgenthub != "task-management" || len(GetAllLabels()) != len(CommonLabelValues) {
		t.Fatal("enum")
	}
}
