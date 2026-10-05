package use_cases

import "testing"

func TestImportTemplateMatchesPythonErrors(t *testing.T) {
	svc := NewContextTemplateService(&draftTemplateContextService{})
	base := func(cat, lvl, vars string) string {
		return `{"id":"x","name":"n","description":"d","category":"` + cat + `","level":"` + lvl + `","data_template":{}` + vars + `}`
	}
	cases := []struct{ in, want string }{
		{base("nope", "project", ""), "'nope' is not a valid TemplateCategory"},
		{base("custom", "zzz", ""), "'zzz' is not a valid ContextLevel"},
		{base("custom", "project", `,"variables":[{"name":"a"}]`), "'description'"},
		{base("custom", "project", `,"variables":["s"]`), "string indices must be integers, not 'str'"},
		{"", "Expecting value: line 1 column 1 (char 0)"},
		{"[1]", "list indices must be integers or slices, not str"},
	}
	for _, c := range cases {
		_, err := svc.ImportTemplate(c.in)
		if err == nil || err.Error() != c.want {
			t.Errorf("%q: got %v want %q", c.in, err, c.want)
		}
	}
	if _, err := svc.ImportTemplate(base("custom", "project", "")); err != nil {
		t.Fatal(err)
	}
}
