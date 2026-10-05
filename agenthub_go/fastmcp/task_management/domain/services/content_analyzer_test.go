package services

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type caFeature struct {
	Type  string         `json:"type"`
	Value string         `json:"value"`
	Conf  float64        `json:"conf"`
	Pos   int            `json:"pos"`
	Ctx   string         `json:"ctx"`
	Meta  map[string]any `json:"meta"`
}

type caFixture struct {
	Features []struct {
		Text     string      `json:"text"`
		Features []caFeature `json:"features"`
		Summary  struct {
			Total int            `json:"total_features"`
			Types map[string]int `json:"feature_types"`
			High  int            `json:"high_confidence_features"`
			Avg   float64        `json:"avg_confidence"`
			Ents  []string       `json:"extracted_entities"`
			Files []string       `json:"file_references"`
		} `json:"summary"`
	} `json:"features"`
	Rel struct {
		Contents map[string]string `json:"contents"`
		Result   map[string][]struct {
			Entity string   `json:"entity"`
			Src    string   `json:"src"`
			Tgt    string   `json:"tgt"`
			Type   string   `json:"type"`
			Conf   float64  `json:"conf"`
			Ev     []string `json:"ev"`
		} `json:"result"`
	} `json:"rel"`
	Sim [][]any `json:"sim"`
}

func caLoad(t *testing.T) caFixture {
	raw, err := os.ReadFile("testdata/content_analyzer_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fx caFixture
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	return fx
}

func TestContentAnalyzerFeaturesMatchPython(t *testing.T) {
	a := NewContentAnalyzer()
	for _, c := range caLoad(t).Features {
		got := a.ExtractFeatures(c.Text)
		if len(got) != len(c.Features) {
			t.Errorf("%.40q: %d features want %d", c.Text, len(got), len(c.Features))
			continue
		}
		for i, g := range got {
			w := c.Features[i]
			gm, _ := json.Marshal(g.Metadata)
			wm, _ := json.Marshal(w.Meta)
			if string(g.FeatureType) != w.Type || g.Value != w.Value || g.Confidence != w.Conf || g.Position != w.Pos ||
				g.Context != w.Ctx || !jsonEqual(gm, wm) {
				t.Errorf("%.40q [%d]: got %+v want %+v", c.Text, i, g, w)
			}
		}
		s := a.GetAnalysisSummary(got)
		types := map[string]int{}
		for _, k := range s.FeatureTypes.Keys() {
			types[k], _ = s.FeatureTypes.Get(k)
		}
		if len(got) > 0 && (s.TotalFeatures != c.Summary.Total || !reflect.DeepEqual(types, c.Summary.Types) ||
			s.HighConfidenceFeatures != c.Summary.High || s.AvgConfidence != c.Summary.Avg ||
			!reflect.DeepEqual(s.ExtractedEntities, c.Summary.Ents) || !reflect.DeepEqual(s.FileReferences, c.Summary.Files)) {
			t.Errorf("%.40q summary: got %+v want %+v", c.Text, s, c.Summary)
		}
	}
}

func jsonEqual(a, b []byte) bool {
	var x, y any
	_ = json.Unmarshal(a, &x)
	_ = json.Unmarshal(b, &y)
	return reflect.DeepEqual(x, y)
}

func TestContentAnalyzerRelationshipsMatchPython(t *testing.T) {
	fx := caLoad(t)
	contents := entities.NewOrderedMap[string]()
	for i := 0; i < len(fx.Rel.Contents); i++ {
		k := "t" + string(rune('0'+i))
		contents.Set(k, fx.Rel.Contents[k])
	}
	got := NewContentAnalyzer().AnalyzeTaskRelationships(contents)
	for _, k := range contents.Keys() {
		g, _ := got.Get(k)
		w := fx.Rel.Result[k]
		if len(g) != len(w) {
			t.Errorf("%s: %d matches want %d", k, len(g), len(w))
			continue
		}
		for i := range g {
			if g[i].Entity != w[i].Entity || g[i].SourceTaskID != w[i].Src || g[i].TargetTaskID != w[i].Tgt ||
				g[i].MatchType != w[i].Type || g[i].Confidence != w[i].Conf || !reflect.DeepEqual(g[i].Evidence, w[i].Ev) {
				t.Errorf("%s[%d]: got %+v want %+v", k, i, g[i], w[i])
			}
		}
	}
}

func TestContentAnalyzerStringSimilarityMatchesPython(t *testing.T) {
	for _, c := range caLoad(t).Sim {
		if got := calculateStringSimilarity(c[0].(string), c[1].(string)); got != c[2].(float64) {
			t.Errorf("sim(%q,%q) = %v want %v", c[0], c[1], got, c[2])
		}
	}
}
