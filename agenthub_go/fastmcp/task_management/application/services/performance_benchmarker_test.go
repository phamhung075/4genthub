package services

import (
	"errors"
	"fmt"
	"math"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpPerfTestF64(v float64) *float64 { return &v }
func zpPerfTestInt(v int) *int         { return &v }
func zpPerfTestBool(v bool) *bool      { return &v }
func zpPerfTestStr(v string) *string   { return &v }

func zpPerfTestClose(a, b float64) bool { return math.Abs(a-b) < 1e-9 }

// zpPerfTestResult builds a result with the context-manager fields populated so the
// summary and recommendation code can run.
func zpPerfTestResult(name string, execMs float64, inputBytes, outputBytes int) *BenchmarkResult {
	r := zpPerfNewBenchmarkResult(name, execMs/1000, execMs/1000, execMs/1000, 0)
	r.ExecutionTimeMs = zpPerfTestF64(execMs)
	r.InputSizeBytes = zpPerfTestInt(inputBytes)
	r.OutputSizeBytes = zpPerfTestInt(outputBytes)
	r.MemoryUsageMb = zpPerfTestF64(0)
	return r
}

func TestPerformanceBenchmarker_CategoryValues(t *testing.T) {
	want := map[BenchmarkCategory]string{
		BenchmarkCategoryResponseOptimization: "response_optimization",
		BenchmarkCategoryContextSelection:     "context_selection",
		BenchmarkCategoryTemplateProcessing:   "template_processing",
		BenchmarkCategoryCachePerformance:     "cache_performance",
		BenchmarkCategoryEndToEnd:             "end_to_end",
	}
	if len(zpPerfBenchmarkCategoryValues) != len(want) {
		t.Fatalf("category count = %d, want %d", len(zpPerfBenchmarkCategoryValues), len(want))
	}
	for _, c := range zpPerfBenchmarkCategoryValues {
		if string(c) != want[c] {
			t.Fatalf("category %v value = %q, want %q", c, string(c), want[c])
		}
		if c.String() != want[c] {
			t.Fatalf("String() = %q, want %q", c.String(), want[c])
		}
	}
}

func TestPerformanceBenchmarker_ResultDefaultsAndProperties(t *testing.T) {
	r := zpPerfNewBenchmarkResult("x", 1, 2, 3, 4)
	if r.Success == nil || !*r.Success {
		t.Fatalf("default Success = %v, want True", r.Success)
	}
	if r.AllTimes == nil || len(r.AllTimes) != 0 {
		t.Fatalf("default AllTimes = %#v, want []", r.AllTimes)
	}
	if r.Metadata == nil || len(r.Metadata) != 0 {
		t.Fatalf("default Metadata = %#v, want {}", r.Metadata)
	}
	if r.Category != nil || r.ExecutionTimeMs != nil || r.MemoryUsageMb != nil ||
		r.InputSizeBytes != nil || r.OutputSizeBytes != nil || r.ErrorMessage != nil ||
		r.PeakMemory != nil || r.MemoryDelta != nil || r.ConfidenceInterval != nil {
		t.Fatalf("optional fields must default to nil")
	}
	if r.IsAsync || r.Cached {
		t.Fatalf("IsAsync/Cached must default false")
	}

	r.InputSizeBytes = zpPerfTestInt(1000)
	r.OutputSizeBytes = zpPerfTestInt(400)
	if got := r.CompressionRatio(); got != 60 {
		t.Fatalf("CompressionRatio() = %v, want 60", got)
	}
	r.InputSizeBytes = zpPerfTestInt(0)
	if got := r.CompressionRatio(); got != 0 {
		t.Fatalf("CompressionRatio() with input 0 = %v, want 0", got)
	}

	r.InputSizeBytes = zpPerfTestInt(1000)
	r.ExecutionTimeMs = zpPerfTestF64(1000)
	if got := r.ThroughputMbPerSec(); got != (1000.0/(1024*1024))/1.0 {
		t.Fatalf("ThroughputMbPerSec() = %v", got)
	}
	r.ExecutionTimeMs = zpPerfTestF64(0)
	if got := r.ThroughputMbPerSec(); got != 0 {
		t.Fatalf("ThroughputMbPerSec() with time 0 = %v, want 0", got)
	}
}

func TestPerformanceBenchmarker_SuitePostInitAndSummary(t *testing.T) {
	name := "suite"
	fromSuiteName := zpPerfNewBenchmarkSuite(nil, &name)
	if fromSuiteName.Name != "suite" || fromSuiteName.SuiteName == nil || *fromSuiteName.SuiteName != "suite" {
		t.Fatalf("__post_init__ from suite_name failed: %#v", fromSuiteName)
	}
	fromName := zpPerfNewBenchmarkSuite(&name, nil)
	if fromName.Name != "suite" || fromName.SuiteName == nil || *fromName.SuiteName != "suite" {
		t.Fatalf("__post_init__ from name failed: %#v", fromName)
	}

	suite := zpPerfNewBenchmarkSuite(nil, nil)
	if s := suite.GetSummary(); s.Keys()[0] != "error" {
		t.Fatalf("empty suite summary = %v", s.Keys())
	}

	suite.AddResult(zpPerfTestResult("a", 10, 1000, 400))
	suite.AddResult(zpPerfTestResult("b", 30, 2000, 500))
	summary := suite.GetSummary()
	wantKeys := "total_benchmarks,successful_benchmarks,success_rate_percent,performance,compression,throughput"
	if got := strings.Join(summary.Keys(), ","); got != wantKeys {
		t.Fatalf("summary keys = %q, want %q", got, wantKeys)
	}
	if v, _ := summary.Get("total_benchmarks"); v.(int) != 2 {
		t.Fatalf("total_benchmarks = %v", v)
	}
	if v, _ := summary.Get("successful_benchmarks"); v.(int) != 2 {
		t.Fatalf("successful_benchmarks = %v", v)
	}
	if v, _ := summary.Get("success_rate_percent"); v.(float64) != 100 {
		t.Fatalf("success_rate_percent = %v", v)
	}

	perfAny, _ := summary.Get("performance")
	perf := perfAny.(*entities.OrderedMap[any])
	if got := strings.Join(perf.Keys(), ","); got != "avg_execution_time_ms,median_execution_time_ms,p95_execution_time_ms,min_execution_time_ms,max_execution_time_ms" {
		t.Fatalf("performance keys = %q", got)
	}
	if v, _ := perf.Get("avg_execution_time_ms"); v.(float64) != 20 {
		t.Fatalf("avg_execution_time_ms = %v", v)
	}
	if v, _ := perf.Get("median_execution_time_ms"); v.(float64) != 20 {
		t.Fatalf("median_execution_time_ms = %v", v)
	}
	if v, _ := perf.Get("p95_execution_time_ms"); v.(float64) != 30 {
		t.Fatalf("p95_execution_time_ms = %v", v)
	}

	compAny, _ := summary.Get("compression")
	comp := compAny.(*entities.OrderedMap[any])
	if v, _ := comp.Get("avg_compression_ratio_percent"); v.(float64) != 67.5 {
		t.Fatalf("avg_compression_ratio_percent = %v, want 67.5", v)
	}
	if v, _ := comp.Get("min_compression_ratio_percent"); v.(float64) != 60 {
		t.Fatalf("min_compression_ratio_percent = %v", v)
	}
	if v, _ := comp.Get("max_compression_ratio_percent"); v.(float64) != 75 {
		t.Fatalf("max_compression_ratio_percent = %v", v)
	}

	throughputAny, _ := summary.Get("throughput")
	throughput := throughputAny.(*entities.OrderedMap[any])
	if got := strings.Join(throughput.Keys(), ","); got != "avg_throughput_mb_per_sec,median_throughput_mb_per_sec,max_throughput_mb_per_sec" {
		t.Fatalf("throughput keys = %q", got)
	}

	failed := zpPerfTestResult("c", 5, 100, 50)
	failed.Success = zpPerfTestBool(false)
	suite2 := zpPerfNewBenchmarkSuite(nil, nil)
	suite2.AddResult(failed)
	if s := suite2.GetSummary(); s.Keys()[0] != "error" {
		t.Fatalf("no-successful summary = %v", s.Keys())
	}
}

func TestPerformanceBenchmarker_BenchmarkContextSession(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	b.StartSuite("s")

	session := b.BenchmarkContext("ctx", BenchmarkCategoryEndToEnd, map[string]any{"a": 1})
	if session.Result.InputSizeBytes == nil || *session.Result.InputSizeBytes == 0 {
		t.Fatalf("input size not computed: %v", session.Result.InputSizeBytes)
	}
	if session.Result.Success == nil || *session.Result.Success {
		t.Fatalf("result must start with success=False")
	}
	outputBytes := 50
	session.Result.OutputSizeBytes = &outputBytes
	session.Stop(nil)
	if session.Result.Success == nil || !*session.Result.Success {
		t.Fatalf("Stop(nil) must set success=True")
	}
	if session.Result.ExecutionTimeMs == nil || *session.Result.ExecutionTimeMs < 0 {
		t.Fatalf("execution time = %v", session.Result.ExecutionTimeMs)
	}
	if session.Result.MemoryUsageMb == nil {
		t.Fatalf("memory usage not recorded")
	}
	if len(b.CurrentSuite.Results) != 1 {
		t.Fatalf("current suite results = %d, want 1", len(b.CurrentSuite.Results))
	}
	// nil input_data leaves input size 0
	empty := b.BenchmarkContext("ctx-empty", BenchmarkCategoryEndToEnd, nil)
	if empty.Result.InputSizeBytes == nil || *empty.Result.InputSizeBytes != 0 {
		t.Fatalf("nil input size = %v, want 0", empty.Result.InputSizeBytes)
	}

	failed := b.BenchmarkContext("ctx-fail", BenchmarkCategoryEndToEnd, nil)
	failed.Stop(errors.New("boom"))
	if failed.Result.Success == nil || *failed.Result.Success {
		t.Fatalf("failed Stop must keep success=False")
	}
	if failed.Result.ErrorMessage == nil || *failed.Result.ErrorMessage != "boom" {
		t.Fatalf("error message = %v, want boom", failed.Result.ErrorMessage)
	}
}

func TestPerformanceBenchmarker_BenchmarkRunsAndStats(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarker(2, 3)
	calls := 0
	fn := zpPerfFunc(func(args []any, kwargs map[string]any) any { calls++; return nil })
	result := b.Benchmark(fn, []any{}, map[string]any{}, zpPerfTestStr("bench"), nil, nil, nil, false, nil)
	if calls != 5 {
		t.Fatalf("callable calls = %d, want warmup+benchmark = 5", calls)
	}
	if len(result.AllTimes) != 3 {
		t.Fatalf("all_times len = %d, want 3", len(result.AllTimes))
	}
	if result.MeanTime != zpPerfMean(result.AllTimes) {
		t.Fatalf("MeanTime = %v, want %v", result.MeanTime, zpPerfMean(result.AllTimes))
	}
	if result.StdDev != zpPerfStdev(result.AllTimes) {
		t.Fatalf("StdDev = %v, want %v", result.StdDev, zpPerfStdev(result.AllTimes))
	}
	if result.Name != "bench" || !*result.Success {
		t.Fatalf("result = %#v", result)
	}
	if len(b.Results) != 1 {
		t.Fatalf("results = %d, want 1", len(b.Results))
	}
}

func TestPerformanceBenchmarker_BenchmarkCache(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarker(0, 2)
	fn := zpPerfFunc(func(args []any, kwargs map[string]any) any { return nil })
	key := "k"
	first := b.Benchmark(fn, []any{}, nil, zpPerfTestStr("c"), nil, nil, &key, true, nil)
	second := b.Benchmark(fn, []any{}, nil, zpPerfTestStr("c"), nil, nil, &key, true, nil)
	if first != second {
		t.Fatalf("cached call must return the same result pointer")
	}
	if !second.Cached {
		t.Fatalf("cached flag not set")
	}
	// cache_key falsy (empty) bypasses the cache
	empty := ""
	third := b.Benchmark(fn, []any{}, nil, zpPerfTestStr("c"), nil, nil, &empty, true, nil)
	if third == first {
		t.Fatalf("empty cache_key must not hit the cache")
	}
}

func TestPerformanceBenchmarker_BenchmarkSetupTeardown(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarker(1, 1)
	seen := []any{}
	fn := zpPerfFunc(func(args []any, kwargs map[string]any) any {
		seen = append(seen, args...)
		return nil
	})
	teardowns := 0
	setup := func() any { return map[string]any{"x": 1} }
	teardown := func(context any) { teardowns++ }
	b.Benchmark(fn, []any{"ignored"}, nil, zpPerfTestStr("s"), setup, teardown, nil, false, nil)
	if len(seen) != 2 {
		t.Fatalf("truthy setup context must call func(context) once per run: seen=%v", seen)
	}
	if teardowns != 2 {
		t.Fatalf("teardowns = %d, want 2", teardowns)
	}
}

func TestPerformanceBenchmarker_ExportJSONCSV(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	result := zpPerfTestResult("op,one", 1.5, 100, 50)
	result.IsAsync = true
	b.Results = append(b.Results, result)

	js := b.ExportResults("json")
	decoded, err := entities.DecodeJSON([]byte(js))
	if err != nil {
		t.Fatalf("json export is not valid JSON: %v", err)
	}
	arr, ok := decoded.([]any)
	if !ok || len(arr) != 1 {
		t.Fatalf("json export shape = %#v", decoded)
	}
	obj := arr[0].(*entities.OrderedMap[any])
	if got := strings.Join(obj.Keys(), ","); got != "name,mean_time,min_time,max_time,std_dev,is_async,cached" {
		t.Fatalf("json keys = %q", got)
	}
	if v, _ := obj.Get("name"); v.(string) != "op,one" {
		t.Fatalf("json name = %v", v)
	}
	if v, _ := obj.Get("is_async"); v.(bool) != true {
		t.Fatalf("json is_async = %v", v)
	}

	csv := b.ExportResults("csv")
	want := "name,mean_time,min_time,max_time,std_dev\r\n\"op,one\",0.0015,0.0015,0.0015,0.0\r\n"
	if csv != want {
		t.Fatalf("csv = %q, want %q", csv, want)
	}
	if b.ExportResults("xml") != "" {
		t.Fatalf("unknown format must return an empty string")
	}
}

func TestPerformanceBenchmarker_CheckTarget(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	result := zpPerfTestResult("x", 5, 100, 50)

	target := zpPerfNewPerformanceTarget("t", 0.01)
	if !b.CheckTarget(result, &target) {
		t.Fatalf("0.005 must pass a 0.01 max_time")
	}
	strict := zpPerfNewPerformanceTarget("t", 0.001)
	if b.CheckTarget(result, &strict) {
		t.Fatalf("0.005 must fail a 0.001 max_time")
	}

	result.PeakMemory = zpPerfTestF64(2.0)
	memTarget := zpPerfNewPerformanceTarget("t", 1.0)
	memTarget.MaxMemory = zpPerfTestF64(1 * 1024 * 1024)
	if b.CheckTarget(result, &memTarget) {
		t.Fatalf("2MB peak must fail a 1MB max_memory")
	}
	memTarget.MaxMemory = zpPerfTestF64(10 * 1024 * 1024)
	if !b.CheckTarget(result, &memTarget) {
		t.Fatalf("2MB peak must pass a 10MB max_memory")
	}

	// fewer than 100 samples uses max(all_times)
	result.AllTimes = []float64{0.001, 0.005}
	percentileTarget := zpPerfNewPerformanceTarget("t", 1.0)
	percentileTarget.PercentileTargets = map[int]float64{50: 0.004}
	if b.CheckTarget(result, &percentileTarget) {
		t.Fatalf("small-sample percentile uses max=0.005 and must fail 0.004")
	}
	percentileTarget.PercentileTargets = map[int]float64{50: 0.006}
	if !b.CheckTarget(result, &percentileTarget) {
		t.Fatalf("small-sample percentile must pass 0.006")
	}

	// 100+ samples uses statistics.quantiles(data, 100)[percentile-1]
	times := make([]float64, 100)
	for i := range times {
		times[i] = float64(i + 1)
	}
	result.AllTimes = times
	exact := zpPerfNewPerformanceTarget("t", 1.0)
	exact.PercentileTargets = map[int]float64{50: 50.5}
	if !b.CheckTarget(result, &exact) {
		t.Fatalf("p50 of 1..100 = 50.5 must pass 50.5")
	}
	exact.PercentileTargets = map[int]float64{50: 50.0}
	if b.CheckTarget(result, &exact) {
		t.Fatalf("p50 of 1..100 = 50.5 must fail 50.0")
	}
}

func TestPerformanceBenchmarker_CompareAndRegression(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	slow := zpPerfNewBenchmarkResult("slow", 2, 2, 2, 1)
	slow.AllTimes = []float64{2, 2}
	fast := zpPerfNewBenchmarkResult("fast", 1, 1, 1, 0.5)
	fast.AllTimes = []float64{1, 1}

	cmp := b.Compare(slow, fast)
	if cmp.Speedup != 2 {
		t.Fatalf("speedup = %v, want 2", cmp.Speedup)
	}
	if cmp.Winner != "fast" {
		t.Fatalf("winner = %q, want fast", cmp.Winner)
	}
	if cmp.StatisticalSignificance == nil || *cmp.StatisticalSignificance != 1.0/((1+0.5)/2) {
		t.Fatalf("significance = %v", cmp.StatisticalSignificance)
	}

	current := zpPerfNewBenchmarkResult("current", 1.2, 1.2, 1.2, 0)
	if !b.DetectRegression(current, []*BenchmarkResult{fast}, 0.1) {
		t.Fatalf("1.2 > 1.0*(1+0.1) must be a regression")
	}
	if b.DetectRegression(current, []*BenchmarkResult{fast}, 1.0) {
		t.Fatalf("1.2 > 2.0 is false")
	}
	if b.DetectRegression(current, nil, 0.1) {
		t.Fatalf("empty history is never a regression")
	}
	sevCurrent, sevHistorical := 1.2, 1.0
	wantSeverity := (sevCurrent - sevHistorical) / sevHistorical
	if got := b.CalculateRegressionSeverity(current, []*BenchmarkResult{fast}); got != wantSeverity {
		t.Fatalf("severity = %v, want %v", got, wantSeverity)
	}
	if got := b.CalculateRegressionSeverity(current, nil); got != 0.0 {
		t.Fatalf("empty history severity = %v, want 0", got)
	}
}

func TestPerformanceBenchmarker_AnalyzeStatistics(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	times := []float64{1, 2, 3, 4}
	result := zpPerfNewBenchmarkResult("x", 2.5, 1, 4, zpPerfStdev(times))
	result.AllTimes = times

	stats := b.AnalyzeStatistics(result)
	percentilesAny, _ := stats.Get("percentiles")
	percentiles := percentilesAny.(*entities.OrderedMap[any])
	if got := strings.Join(percentiles.Keys(), ","); got != "25,50,75,90,95,99" {
		t.Fatalf("percentile keys = %q", got)
	}
	wantPercentiles := map[string]float64{"25": 2, "50": 3, "75": 4, "90": 4, "95": 4, "99": 4}
	for k, want := range wantPercentiles {
		gotAny, _ := percentiles.Get(k)
		if gotAny.(float64) != want {
			t.Fatalf("percentile %s = %v, want %v", k, gotAny, want)
		}
	}
	outliersAny, _ := stats.Get("outliers")
	if len(outliersAny.([]any)) != 0 {
		t.Fatalf("outliers = %v, want []", outliersAny)
	}
	ciAny, _ := stats.Get("confidence_interval")
	ci := ciAny.([2]float64)
	margin := 1.96 * zpPerfStdev(times) / math.Pow(4, 0.5)
	if !zpPerfTestClose(ci[0], 2.5-margin) || !zpPerfTestClose(ci[1], 2.5+margin) {
		t.Fatalf("confidence interval = %v", ci)
	}
	if v, _ := stats.Get("variance"); !zpPerfTestClose(v.(float64), zpPerfStdev(times)*zpPerfStdev(times)) {
		t.Fatalf("variance = %v", v)
	}
	if v, _ := stats.Get("coefficient_of_variation"); !zpPerfTestClose(v.(float64), zpPerfStdev(times)/2.5) {
		t.Fatalf("coefficient_of_variation = %v", v)
	}

	empty := b.AnalyzeStatistics(zpPerfNewBenchmarkResult("y", 0, 0, 0, 0))
	if len(empty.Keys()) != 0 {
		t.Fatalf("empty all_times must give {}, got %v", empty.Keys())
	}
}

func TestPerformanceBenchmarker_GenerateReport(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	slow := zpPerfNewBenchmarkResult("slow", 0.2, 0.1, 0.3, 0.15)
	fast := zpPerfNewBenchmarkResult("fast", 0.01, 0.01, 0.01, 0.001)
	b.Results = append(b.Results, slow, fast)

	report := b.GenerateReport(nil, true, true)
	if got := strings.Join(report.Keys(), ","); got != "summary,detailed_results,charts,recommendations" {
		t.Fatalf("report keys = %q", got)
	}
	summaryAny, _ := report.Get("summary")
	summary := summaryAny.(*entities.OrderedMap[any])
	if got := strings.Join(summary.Keys(), ","); got != "total_benchmarks,mean_execution_time" {
		t.Fatalf("summary keys = %q", got)
	}
	if v, _ := summary.Get("total_benchmarks"); v.(int) != 2 {
		t.Fatalf("total_benchmarks = %v", v)
	}
	if v, _ := summary.Get("mean_execution_time"); v.(float64) != zpPerfMean([]float64{0.2, 0.01}) {
		t.Fatalf("mean_execution_time = %v", v)
	}
	detailedAny, _ := report.Get("detailed_results")
	detailed := detailedAny.([]any)
	if len(detailed) != 2 {
		t.Fatalf("detailed_results len = %d", len(detailed))
	}
	first := detailed[0].(*entities.OrderedMap[any])
	if got := strings.Join(first.Keys(), ","); got != "name,mean_time,min_time,max_time,std_dev" {
		t.Fatalf("detailed result keys = %q", got)
	}
	recsAny, _ := report.Get("recommendations")
	recs := recsAny.([]string)
	if len(recs) != 2 || !strings.Contains(recs[0], "Optimize 'slow'") || !strings.Contains(recs[1], "high variance") {
		t.Fatalf("recommendations = %v", recs)
	}

	plain := b.GenerateReport(nil, false, false)
	if got := strings.Join(plain.Keys(), ","); got != "summary,detailed_results" {
		t.Fatalf("plain report keys = %q", got)
	}

	empty := zpPerfNewPerformanceBenchmarkerDefault().GenerateReport(nil, false, false)
	emptySummaryAny, _ := empty.Get("summary")
	emptySummary := emptySummaryAny.(*entities.OrderedMap[any])
	if v, _ := emptySummary.Get("mean_execution_time"); v.(int) != 0 {
		t.Fatalf("empty mean_execution_time = %v, want int 0", v)
	}
	if recs, _ := empty.Get("recommendations"); recs != nil {
		t.Fatalf("empty report must not include recommendations")
	}
}

func TestPerformanceBenchmarker_Measure(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	session := b.Measure("m")
	time.Sleep(2 * time.Millisecond)
	session.Stop()
	if !session.ResultStored {
		t.Fatalf("result_stored = false")
	}
	if session.ElapsedTime <= 0 {
		t.Fatalf("elapsed_time = %v", session.ElapsedTime)
	}
	if len(b.Results) != 1 || b.Results[0].Name != "m" {
		t.Fatalf("results = %#v", b.Results)
	}
	if len(b.Results[0].AllTimes) != 1 || b.Results[0].AllTimes[0] != session.ElapsedTime {
		t.Fatalf("all_times = %v, elapsed = %v", b.Results[0].AllTimes, session.ElapsedTime)
	}
}

func TestPerformanceBenchmarker_ContextMethodsPreserveBenchmarkMisCall(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	b.StartSuite("s")

	cases := []struct {
		name string
		call func()
	}{
		{"response_optimization", func() { b.BenchmarkResponseOptimization(nil, []map[string]any{{"a": 1}}) }},
		{"context_selection", func() { b.BenchmarkContextSelection(nil, nil, []map[string]any{{"a": 1}}) }},
		{"cache_performance", func() { b.BenchmarkCachePerformance(nil, [][2]any{{"k", 1}}) }},
		{"end_to_end", func() { b.BenchmarkEndToEnd(nil, nil, []map[string]any{{"a": 1}}) }},
	}
	for _, tc := range cases {
		tc := tc
		func() {
			defer func() {
				recovered := recover()
				if recovered == nil {
					t.Fatalf("%s: expected the Python TypeError panic", tc.name)
				}
				if !strings.Contains(fmt.Sprint(recovered), "argument after * must be an iterable") {
					t.Fatalf("%s: panic = %v", tc.name, recovered)
				}
			}()
			tc.call()
		}()
	}

	// empty input never enters the loop, so the category summary is returned
	empty := b.BenchmarkResponseOptimization(nil, nil)
	if empty == nil {
		t.Fatalf("empty response optimization returned nil")
	}
	if v, _ := empty.Get("error"); v != "No results for category response_optimization" {
		t.Fatalf("empty summary = %v", empty.Keys())
	}
}

func TestPerformanceBenchmarker_GetResults(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	b.Results = append(b.Results,
		zpPerfNewBenchmarkResult("a", 1, 1, 1, 0),
		zpPerfNewBenchmarkResult("b", 1, 1, 1, 0),
		zpPerfNewBenchmarkResult("a", 2, 2, 2, 0),
	)
	if got := b.GetResults("a"); len(got) != 2 {
		t.Fatalf("GetResults(a) = %d", len(got))
	}
	if got := b.GetResults("z"); len(got) != 0 {
		t.Fatalf("GetResults(z) = %d", len(got))
	}
}

func TestPerformanceBenchmarker_BenchmarkMemory(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	fn := zpPerfFunc(func(args []any, kwargs map[string]any) any {
		_ = make([]byte, 1<<16)
		return nil
	})
	result := b.BenchmarkMemory(fn, nil, nil, zpPerfTestStr("mem"))
	if result.PeakMemory == nil || result.MemoryDelta == nil {
		t.Fatalf("peak_memory/memory_delta not set")
	}
	profileAny, ok := result.Metadata["memory_profile"]
	if !ok {
		t.Fatalf("metadata = %#v", result.Metadata)
	}
	profile := profileAny.(*entities.OrderedMap[any])
	if got := strings.Join(profile.Keys(), ","); got != "before_bytes,after_bytes,peak_bytes,delta_bytes" {
		t.Fatalf("memory_profile keys = %q", got)
	}
	if len(b.Results) != 1 || result.Name != "mem" {
		t.Fatalf("results = %#v", b.Results)
	}
}

func TestPerformanceBenchmarker_RunSuite(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarker(0, 2)
	suite := zpPerfNewBenchmarkSuite(zpPerfTestStr("s"), nil)
	suite.AddBenchmark("one", zpPerfFunc(func(args []any, kwargs map[string]any) any { return nil }), nil, nil)
	suite.AddBenchmark("two", zpPerfFunc(func(args []any, kwargs map[string]any) any { return nil }), nil, nil)
	results := b.RunSuite(suite)
	if len(results) != 2 {
		t.Fatalf("RunSuite results = %d, want 2", len(results))
	}
	if results[0].Name != "one" || results[1].Name != "two" {
		t.Fatalf("RunSuite names = %q, %q", results[0].Name, results[1].Name)
	}
}

func TestPerformanceBenchmarker_BenchmarkAdaptive(t *testing.T) {
	b := zpPerfNewPerformanceBenchmarkerDefault()
	fn := zpPerfFunc(func(args []any, kwargs map[string]any) any { return nil })
	result := b.BenchmarkAdaptive(fn, "adapt", 2, 12, 0.95, nil, nil)
	if len(result.AllTimes) < 2 {
		t.Fatalf("adaptive all_times = %d", len(result.AllTimes))
	}
	if result.ConfidenceInterval == nil {
		t.Fatalf("confidence_interval not set")
	}
	if len(b.Results) != 1 {
		t.Fatalf("results = %d", len(b.Results))
	}
}
