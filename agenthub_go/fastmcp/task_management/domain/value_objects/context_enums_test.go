package value_objects

import "testing"

func TestContextLevelFromEnumValueIsExact(t *testing.T) {
	if l, err := ContextLevelFromEnumValue("task"); err != nil || l != ContextLevelTask {
		t.Fatalf("task = %v, %v", l, err)
	}
	for _, bad := range []string{"GLOBAL", "Task", " task", "xyz", ""} {
		_, err := ContextLevelFromEnumValue(bad)
		want := "'" + bad + "' is not a valid ContextLevel"
		if err == nil || err.Error() != want {
			t.Errorf("%q: err = %v, want %q", bad, err, want)
		}
	}
}
