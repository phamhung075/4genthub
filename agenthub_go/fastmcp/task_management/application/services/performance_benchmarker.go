package services

import (
	"fmt"
	"math"
	"math/big"
	"reflect"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// BenchmarkCategory: Benchmark categories (Python enum BenchmarkCategory).
type BenchmarkCategory string

const (
	BenchmarkCategoryResponseOptimization BenchmarkCategory = "response_optimization"
	BenchmarkCategoryContextSelection     BenchmarkCategory = "context_selection"
	BenchmarkCategoryTemplateProcessing   BenchmarkCategory = "template_processing"
	BenchmarkCategoryCachePerformance     BenchmarkCategory = "cache_performance"
	BenchmarkCategoryEndToEnd             BenchmarkCategory = "end_to_end"
)

// zpPerfBenchmarkCategoryValues lists all members in declaration order.
var zpPerfBenchmarkCategoryValues = []BenchmarkCategory{
	BenchmarkCategoryResponseOptimization,
	BenchmarkCategoryContextSelection,
	BenchmarkCategoryTemplateProcessing,
	BenchmarkCategoryCachePerformance,
	BenchmarkCategoryEndToEnd,
}

func (e BenchmarkCategory) String() string { return string(e) }

// zpPerfFunc is the Go shape of a Python callable invoked as func(*args, **kwargs).
type zpPerfFunc func(args []any, kwargs map[string]any) any

// BenchmarkResult is a single benchmark result (Python dataclass BenchmarkResult).
// Optional fields are pointers; a nil pointer is Python None. InputSizeBytes and
// OutputSizeBytes are pointers but the properties dereference them, so a nil value
// panics exactly where Python raises TypeError on None arithmetic.
type BenchmarkResult struct {
	Name               string
	MeanTime           float64
	MinTime            float64
	MaxTime            float64
	StdDev             float64
	AllTimes           []float64
	Category           *BenchmarkCategory
	ExecutionTimeMs    *float64
	MemoryUsageMb      *float64
	InputSizeBytes     *int
	OutputSizeBytes    *int
	Success            *bool
	ErrorMessage       *string
	Metadata           map[string]any
	IsAsync            bool
	Cached             bool
	PeakMemory         *float64
	MemoryDelta        *float64
	ConfidenceInterval *[2]float64
}

// CompressionRatio is the compression_ratio property.
func (r *BenchmarkResult) CompressionRatio() float64 {
	if *r.InputSizeBytes == 0 {
		return 0.0
	}
	return (1 - float64(*r.OutputSizeBytes)/float64(*r.InputSizeBytes)) * 100
}

// ThroughputMbPerSec is the throughput_mb_per_sec property.
func (r *BenchmarkResult) ThroughputMbPerSec() float64 {
	if *r.ExecutionTimeMs == 0 {
		return 0.0
	}
	return (float64(*r.InputSizeBytes) / (1024 * 1024)) / (*r.ExecutionTimeMs / 1000)
}

// zpPerfNewBenchmarkResult applies the dataclass field defaults (all_times [],
// success True, metadata {}).
func zpPerfNewBenchmarkResult(name string, meanTime, minTime, maxTime, stdDev float64) *BenchmarkResult {
	success := true
	return &BenchmarkResult{
		Name: name, MeanTime: meanTime, MinTime: minTime, MaxTime: maxTime, StdDev: stdDev,
		AllTimes: []float64{}, Success: &success, Metadata: map[string]any{},
	}
}

// BenchmarkSuite is the complete benchmark suite results (Python dataclass BenchmarkSuite).
type BenchmarkSuite struct {
	Name        string
	Description string
	SuiteName   *string
	StartedAt   *time.Time
	CompletedAt *time.Time
	Results     []*BenchmarkResult
	Benchmarks  []map[string]any
}

// zpPerfNewBenchmarkSuite builds a suite with the dataclass defaults and applies
// __post_init__ (name and suite_name mirror each other when only one is set).
func zpPerfNewBenchmarkSuite(name *string, suiteName *string) *BenchmarkSuite {
	s := &BenchmarkSuite{Results: []*BenchmarkResult{}, Benchmarks: []map[string]any{}}
	if name != nil {
		s.Name = *name
	}
	if suiteName != nil {
		s.SuiteName = suiteName
	}
	// __post_init__
	if s.SuiteName != nil && *s.SuiteName != "" && s.Name == "" {
		s.Name = *s.SuiteName
	}
	if s.Name != "" && (s.SuiteName == nil || *s.SuiteName == "") {
		n := s.Name
		s.SuiteName = &n
	}
	return s
}

// AddResult appends a result.
func (s *BenchmarkSuite) AddResult(result *BenchmarkResult) { s.Results = append(s.Results, result) }

// AddBenchmark appends a benchmark dict {"name", "func", "args", "kwargs"}.
func (s *BenchmarkSuite) AddBenchmark(name string, fn any, args []any, kwargs map[string]any) {
	if args == nil {
		args = []any{}
	}
	if kwargs == nil {
		kwargs = map[string]any{}
	}
	s.Benchmarks = append(s.Benchmarks, map[string]any{"name": name, "func": fn, "args": args, "kwargs": kwargs})
}

// GetSummary is get_summary: summary statistics in Python key order.
func (s *BenchmarkSuite) GetSummary() *entities.OrderedMap[any] {
	if len(s.Results) == 0 {
		return zpPerfObj("error", "No results available")
	}
	successful := []*BenchmarkResult{}
	for _, r := range s.Results {
		if r.Success != nil && *r.Success {
			successful = append(successful, r)
		}
	}
	if len(successful) == 0 {
		return zpPerfObj("error", "No successful results")
	}

	executionTimes := make([]float64, len(successful))
	compressionRatios := make([]float64, len(successful))
	throughputs := make([]float64, len(successful))
	for i, r := range successful {
		executionTimes[i] = *r.ExecutionTimeMs
		compressionRatios[i] = r.CompressionRatio()
		throughputs[i] = r.ThroughputMbPerSec()
	}

	var p95 float64
	if len(executionTimes) >= 20 {
		p95 = zpPerfQuantiles(executionTimes, 20)[18]
	} else {
		p95 = zpPerfMax(executionTimes)
	}

	performance := zpPerfObj(
		"avg_execution_time_ms", zpPerfMean(executionTimes),
		"median_execution_time_ms", zpPerfMedian(executionTimes),
		"p95_execution_time_ms", p95,
		"min_execution_time_ms", zpPerfMin(executionTimes),
		"max_execution_time_ms", zpPerfMax(executionTimes),
	)
	compression := zpPerfObj(
		"avg_compression_ratio_percent", zpPerfMean(compressionRatios),
		"median_compression_ratio_percent", zpPerfMedian(compressionRatios),
		"min_compression_ratio_percent", zpPerfMin(compressionRatios),
		"max_compression_ratio_percent", zpPerfMax(compressionRatios),
	)
	throughput := zpPerfObj(
		"avg_throughput_mb_per_sec", zpPerfMean(throughputs),
		"median_throughput_mb_per_sec", zpPerfMedian(throughputs),
		"max_throughput_mb_per_sec", zpPerfMax(throughputs),
	)

	return zpPerfObj(
		"total_benchmarks", len(s.Results),
		"successful_benchmarks", len(successful),
		"success_rate_percent", float64(len(successful))/float64(len(s.Results))*100,
		"performance", performance,
		"compression", compression,
		"throughput", throughput,
	)
}

// PerformanceTarget is a performance target configuration.
type PerformanceTarget struct {
	Name              string
	MaxTime           float64
	MaxMemory         *float64
	PercentileTargets map[int]float64
}

// zpPerfNewPerformanceTarget applies the dataclass default_factory for percentile_targets.
func zpPerfNewPerformanceTarget(name string, maxTime float64) PerformanceTarget {
	return PerformanceTarget{Name: name, MaxTime: maxTime, PercentileTargets: map[int]float64{}}
}

// BenchmarkComparison is a comparison between two benchmark results.
type BenchmarkComparison struct {
	Speedup                 float64
	Winner                  string
	StatisticalSignificance *float64
}

// Python PerformanceBenchmarker.__init__ defaults.
const (
	zpPerfDefaultWarmupRuns    = 3
	zpPerfDefaultBenchmarkRuns = 10
)

// PerformanceBenchmarker is the comprehensive performance benchmarker.
type PerformanceBenchmarker struct {
	WarmupRuns      int
	BenchmarkRuns   int
	Results         []*BenchmarkResult
	CurrentSuite    *BenchmarkSuite
	CompletedSuites []*BenchmarkSuite
	cache           map[string]*BenchmarkResult
}

// zpPerfNewPerformanceBenchmarker mirrors __init__(warmup_runs, benchmark_runs).
func zpPerfNewPerformanceBenchmarker(warmupRuns, benchmarkRuns int) *PerformanceBenchmarker {
	return &PerformanceBenchmarker{
		WarmupRuns: warmupRuns, BenchmarkRuns: benchmarkRuns,
		Results: []*BenchmarkResult{}, CompletedSuites: []*BenchmarkSuite{},
		cache: map[string]*BenchmarkResult{},
	}
}

// zpPerfNewPerformanceBenchmarkerDefault mirrors PerformanceBenchmarker().
func zpPerfNewPerformanceBenchmarkerDefault() *PerformanceBenchmarker {
	return zpPerfNewPerformanceBenchmarker(zpPerfDefaultWarmupRuns, zpPerfDefaultBenchmarkRuns)
}

// StartSuite starts a new benchmark suite.
func (b *PerformanceBenchmarker) StartSuite(name string) *BenchmarkSuite {
	s := zpPerfNewBenchmarkSuite(nil, &name)
	t := time.Now().Truncate(time.Microsecond)
	s.StartedAt = &t
	b.CurrentSuite = s
	return s
}

// CompleteSuite completes the current benchmark suite.
func (b *PerformanceBenchmarker) CompleteSuite() *BenchmarkSuite {
	if b.CurrentSuite == nil {
		return nil
	}
	t := time.Now().Truncate(time.Microsecond)
	b.CurrentSuite.CompletedAt = &t
	b.CompletedSuites = append(b.CompletedSuites, b.CurrentSuite)
	completed := b.CurrentSuite
	b.CurrentSuite = nil
	return completed
}

// zpPerfBenchmarkSession models the benchmark_context @contextmanager. Call
// Stop(err) after the measured body; err is recorded as error_message and the
// body error is swallowed like the Python generator. The measured result is
// available through the Result field.
type zpPerfBenchmarkSession struct {
	bench        *PerformanceBenchmarker
	Result       *BenchmarkResult
	start        time.Time
	memoryBefore uint64
	finished     bool
}

// BenchmarkContext is benchmark_context: it does not run a body itself, it
// returns a session whose Stop records timing, memory and the result.
func (b *PerformanceBenchmarker) BenchmarkContext(name string, category BenchmarkCategory, inputData any) *zpPerfBenchmarkSession {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	memoryBefore := ms.HeapAlloc

	inputSize := 0
	if value_objects.PyTruthy(inputData) {
		dumped := value_objects.PyJSONDumpsDefaultStr(inputData, -1)
		if dumped != "" {
			inputSize = len(dumped)
		} else {
			inputSize = zpPerfSizeof(inputData)
		}
	}

	// Python constructs BenchmarkResult() without mean_time/min_time/max_time/std_dev,
	// which raises TypeError; the Go result carries zeros instead (reported deviation).
	result := zpPerfNewBenchmarkResult(name, 0, 0, 0, 0)
	cat := category
	zeroMS := 0.0
	zeroMB := 0.0
	zeroBytes := 0
	failure := false
	result.Category = &cat
	result.ExecutionTimeMs = &zeroMS
	result.MemoryUsageMb = &zeroMB
	result.InputSizeBytes = &inputSize
	result.OutputSizeBytes = &zeroBytes
	result.Success = &failure

	return &zpPerfBenchmarkSession{bench: b, Result: result, start: time.Now(), memoryBefore: memoryBefore}
}

// Stop finalizes the session: it sets success on a nil error (or error_message
// otherwise), records execution time and memory, and adds the result to the
// current suite.
func (s *zpPerfBenchmarkSession) Stop(err error) {
	if s.finished {
		return
	}
	s.finished = true
	if err != nil {
		msg := err.Error()
		s.Result.ErrorMessage = &msg
	} else {
		success := true
		s.Result.Success = &success
	}
	elapsed := zpPerfSeconds(time.Since(s.start))
	s.Result.ExecutionTimeMs = &elapsed

	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	delta := int64(ms.HeapAlloc) - int64(s.memoryBefore)
	memoryMB := float64(delta) / (1024 * 1024)
	s.Result.MemoryUsageMb = &memoryMB

	if s.bench != nil && s.bench.CurrentSuite != nil {
		s.bench.CurrentSuite.AddResult(s.Result)
	}
}

// BenchmarkResponseOptimization ports benchmark_response_optimization. The Python
// body wraps each optimization in `with self.benchmark(...)`, a defect: self.benchmark
// is the benchmark runner, not the benchmark_context context manager. The call binds
// func to the name (str), args to the category enum and kwargs to the response, so
// the *args unpack raises TypeError for every non-empty test_responses. Preserved.
func (b *PerformanceBenchmarker) BenchmarkResponseOptimization(optimizer any, testResponses []map[string]any) *entities.OrderedMap[any] {
	for i, response := range testResponses {
		name := fmt.Sprintf("response_optimization_test_%d", i+1)
		_ = b.Benchmark(name, BenchmarkCategoryResponseOptimization, response, nil, nil, nil, nil, false, nil)
	}
	return b.getCategorySummary(BenchmarkCategoryResponseOptimization)
}

// BenchmarkContextSelection ports benchmark_context_selection. In Python the
// sibling imports (context_field_selector / context_template_manager) fail at
// import time, and the same self.benchmark defect is present; only the defect is
// reproduced here (the unported imports cannot be).
func (b *PerformanceBenchmarker) BenchmarkContextSelection(fieldSelector any, templateManager any, testContexts []map[string]any) *entities.OrderedMap[any] {
	fieldSets := []string{"minimal", "summary", "detail"}
	operations := []string{"task.get", "task.list", "task.update"}
	for _, context := range testContexts {
		for _, fieldSet := range fieldSets {
			for _, operation := range operations {
				name := "context_selection_" + fieldSet + "_" + operation
				_ = b.Benchmark(name, BenchmarkCategoryContextSelection, context, nil, nil, nil, nil, false, nil)
			}
		}
	}
	return b.getCategorySummary(BenchmarkCategoryContextSelection)
}

// BenchmarkCachePerformance ports benchmark_cache_performance (same self.benchmark
// defect: the first cache_warmup call raises TypeError for any input).
func (b *PerformanceBenchmarker) BenchmarkCachePerformance(cacheOptimizer any, testData [][2]any) *entities.OrderedMap[any] {
	_ = b.Benchmark("cache_warmup", BenchmarkCategoryCachePerformance, nil, nil, nil, nil, nil, false, nil)
	_ = b.Benchmark("cache_hit_performance", BenchmarkCategoryCachePerformance, nil, nil, nil, nil, nil, false, nil)
	_ = b.Benchmark("cache_miss_performance", BenchmarkCategoryCachePerformance, nil, nil, nil, nil, nil, false, nil)
	_ = b.Benchmark("cache_optimization", BenchmarkCategoryCachePerformance, nil, nil, nil, nil, nil, false, nil)
	return b.getCategorySummary(BenchmarkCategoryCachePerformance)
}

// BenchmarkEndToEnd ports benchmark_end_to_end (same self.benchmark defect).
func (b *PerformanceBenchmarker) BenchmarkEndToEnd(optimizer any, templateManager any, testScenarios []map[string]any) *entities.OrderedMap[any] {
	for i, scenario := range testScenarios {
		name := fmt.Sprintf("end_to_end_scenario_%d", i+1)
		_ = b.Benchmark(name, BenchmarkCategoryEndToEnd, scenario, nil, nil, nil, nil, false, nil)
	}
	return b.getCategorySummary(BenchmarkCategoryEndToEnd)
}

// getCategorySummary is _get_category_summary.
func (b *PerformanceBenchmarker) getCategorySummary(category BenchmarkCategory) *entities.OrderedMap[any] {
	if b.CurrentSuite == nil {
		return zpPerfObj("error", "No active benchmark suite")
	}
	categoryResults := []*BenchmarkResult{}
	for _, r := range b.CurrentSuite.Results {
		if r.Category != nil && *r.Category == category {
			categoryResults = append(categoryResults, r)
		}
	}
	if len(categoryResults) == 0 {
		return zpPerfObj("error", fmt.Sprintf("No results for category %s", string(category)))
	}
	successful := []*BenchmarkResult{}
	for _, r := range categoryResults {
		if r.Success != nil && *r.Success {
			successful = append(successful, r)
		}
	}
	if len(successful) == 0 {
		return zpPerfObj("error", fmt.Sprintf("No successful results for category %s", string(category)))
	}

	executionTimes := make([]float64, len(successful))
	compressionRatios := []float64{}
	for i, r := range successful {
		executionTimes[i] = *r.ExecutionTimeMs
		if *r.InputSizeBytes > 0 {
			compressionRatios = append(compressionRatios, r.CompressionRatio())
		}
	}

	summary := zpPerfObj(
		"category", string(category),
		"total_tests", len(categoryResults),
		"successful_tests", len(successful),
		"success_rate_percent", float64(len(successful))/float64(len(categoryResults))*100,
		"avg_execution_time_ms", zpPerfMean(executionTimes),
		"median_execution_time_ms", zpPerfMedian(executionTimes),
		"total_execution_time_ms", value_objects.PySum(executionTimes),
	)
	if len(compressionRatios) > 0 {
		summary.Set("avg_compression_ratio_percent", zpPerfMean(compressionRatios))
		summary.Set("median_compression_ratio_percent", zpPerfMedian(compressionRatios))
		summary.Set("max_compression_ratio_percent", zpPerfMax(compressionRatios))
	}
	return summary
}

// GenerateReportOld is generate_report_old.
func (b *PerformanceBenchmarker) GenerateReportOld(suite *BenchmarkSuite) *entities.OrderedMap[any] {
	target := suite
	if target == nil {
		target = b.CurrentSuite
	}
	if target == nil {
		return zpPerfObj("error", "No benchmark suite available")
	}

	categorySummaries := entities.NewOrderedMap[any]()
	seen := map[BenchmarkCategory]bool{}
	for _, r := range target.Results {
		if r.Category == nil {
			panic("'NoneType' object has no attribute 'value'")
		}
		c := *r.Category
		if !seen[c] {
			seen[c] = true
			categorySummaries.Set(string(c), b.getCategorySummary(c))
		}
	}

	return zpPerfObj(
		"suite_name", zpPerfOptStr(target.SuiteName),
		"started_at", value_objects.IsoFormatNaive(*target.StartedAt),
		"completed_at", zpPerfOptTimeISO(target.CompletedAt),
		"summary", target.GetSummary(),
		"category_summaries", categorySummaries,
		"performance_comparison", b.compareWithBaseline(),
		"recommendations", b.generateRecommendations(target),
	)
}

// compareWithBaseline is _compare_with_baseline.
func (b *PerformanceBenchmarker) compareWithBaseline() *entities.OrderedMap[any] {
	baseline := zpPerfObj(
		"response_processing_ms", 100,
		"response_size_bytes", 5000,
		"compression_ratio_percent", 0,
		"cache_hit_rate_percent", 0,
	)
	if b.CurrentSuite == nil || len(b.CurrentSuite.Results) == 0 {
		return zpPerfObj("error", "No current results to compare")
	}
	successful := []*BenchmarkResult{}
	for _, r := range b.CurrentSuite.Results {
		if r.Success != nil && *r.Success {
			successful = append(successful, r)
		}
	}
	if len(successful) == 0 {
		return zpPerfObj("error", "No successful results to compare")
	}

	executionTimes := make([]float64, len(successful))
	outputSizes := make([]float64, len(successful))
	compressionRatios := []float64{}
	for i, r := range successful {
		executionTimes[i] = *r.ExecutionTimeMs
		outputSizes[i] = float64(*r.OutputSizeBytes)
		if *r.InputSizeBytes > 0 {
			compressionRatios = append(compressionRatios, r.CompressionRatio())
		}
	}
	avgExecutionTime := zpPerfMean(executionTimes)
	avgOutputSize := zpPerfMean(outputSizes)
	var avgCompression any = 0
	if len(compressionRatios) > 0 {
		avgCompression = zpPerfMean(compressionRatios)
	}

	currentMetrics := zpPerfObj(
		"avg_execution_time_ms", avgExecutionTime,
		"avg_output_size_bytes", avgOutputSize,
		"avg_compression_ratio_percent", avgCompression,
	)
	improvements := zpPerfObj(
		"execution_time_improvement_percent", math.Max(0, (100-avgExecutionTime)/100*100),
		"size_reduction_percent", math.Max(0, (5000-avgOutputSize)/5000*100),
		"compression_achievement_percent", avgCompression,
	)
	return zpPerfObj("baseline_metrics", baseline, "current_metrics", currentMetrics, "improvements", improvements)
}

// generateRecommendations is _generate_recommendations.
func (b *PerformanceBenchmarker) generateRecommendations(suite *BenchmarkSuite) []string {
	recommendations := []string{}
	successful := []*BenchmarkResult{}
	for _, r := range suite.Results {
		if r.Success != nil && *r.Success {
			successful = append(successful, r)
		}
	}
	if len(successful) == 0 {
		return []string{"No successful benchmarks to analyze"}
	}

	executionTimes := make([]float64, len(successful))
	for i, r := range successful {
		executionTimes[i] = *r.ExecutionTimeMs
	}
	avgTime := zpPerfMean(executionTimes)
	maxTime := zpPerfMax(executionTimes)
	if avgTime > 50 {
		recommendations = append(recommendations, "Consider optimizing response processing - average time exceeds 50ms")
	}
	if maxTime > 200 {
		recommendations = append(recommendations, "Some operations are very slow (>200ms) - investigate bottlenecks")
	}

	compressionRatios := []float64{}
	memoryUsage := []float64{}
	for _, r := range successful {
		if *r.InputSizeBytes > 0 {
			compressionRatios = append(compressionRatios, r.CompressionRatio())
		}
		if *r.MemoryUsageMb > 0 {
			memoryUsage = append(memoryUsage, *r.MemoryUsageMb)
		}
	}
	if len(compressionRatios) > 0 {
		avgCompression := zpPerfMean(compressionRatios)
		if avgCompression < 50 {
			recommendations = append(recommendations, "Compression ratio below 50% - review optimization strategies")
		} else if avgCompression > 80 {
			recommendations = append(recommendations, "Excellent compression ratio achieved - current optimization is effective")
		}
	}
	if len(memoryUsage) > 0 {
		if zpPerfMean(memoryUsage) > 10 {
			recommendations = append(recommendations, "High memory usage detected - consider memory optimization")
		}
	}

	hasCache := false
	for _, r := range successful {
		if r.Category != nil && *r.Category == BenchmarkCategoryCachePerformance {
			hasCache = true
			break
		}
	}
	if hasCache {
		cacheTimes := []float64{}
		for _, r := range successful {
			if r.Category != nil && *r.Category == BenchmarkCategoryCachePerformance {
				cacheTimes = append(cacheTimes, *r.ExecutionTimeMs)
			}
		}
		if zpPerfMean(cacheTimes) > 10 {
			recommendations = append(recommendations, "Cache operations are slow - consider cache optimization")
		}
	}

	if len(recommendations) == 0 {
		return []string{"Performance looks good - no specific recommendations"}
	}
	return recommendations
}

// Benchmark is benchmark(func=None, args=(), kwargs=None, ...). func/args/kwargs are
// `any` because Python unpacks them dynamically (`func(*args, **kwargs)`); args must be
// a []any tuple and kwargs a map[string]any, otherwise the invocation raises like Python.
func (b *PerformanceBenchmarker) Benchmark(fn any, args any, kwargs any, name *string, setup func() any, teardown func(any), cacheKey *string, useCache bool, profileType *string) *BenchmarkResult {
	if kwargs == nil {
		kwargs = map[string]any{}
	}

	if useCache && cacheKey != nil && *cacheKey != "" {
		if cached, ok := b.cache[*cacheKey]; ok {
			cached.Cached = true
			return cached
		}
	}

	allTimes := []float64{}

	for i := 0; i < b.WarmupRuns; i++ {
		var context any = map[string]any{}
		if setup != nil {
			context = setup()
		}
		start := time.Now()
		if value_objects.PyTruthy(context) {
			zpPerfInvoke(fn, []any{context}, nil)
		} else {
			zpPerfInvoke(fn, args, kwargs)
		}
		_ = time.Since(start)
		if teardown != nil {
			teardown(context)
		}
	}

	for i := 0; i < b.BenchmarkRuns; i++ {
		var context any = map[string]any{}
		if setup != nil {
			context = setup()
		}
		start := time.Now()
		if value_objects.PyTruthy(context) {
			zpPerfInvoke(fn, []any{context}, nil)
		} else {
			zpPerfInvoke(fn, args, kwargs)
		}
		end := time.Now()
		allTimes = append(allTimes, zpPerfSeconds(end.Sub(start)))
		if teardown != nil {
			teardown(context)
		}
	}

	result := zpPerfNewBenchmarkResult(zpPerfResultName(name, fn), zpPerfMean(allTimes), zpPerfMin(allTimes), zpPerfMax(allTimes), zpPerfStdev(allTimes))
	result.AllTimes = allTimes
	b.Results = append(b.Results, result)
	if cacheKey != nil && *cacheKey != "" {
		b.cache[*cacheKey] = result
	}
	return result
}

// BenchmarkAsync is benchmark_async: Python awaits each call; Go runs the same callable
// sequentially (no asyncio).
func (b *PerformanceBenchmarker) BenchmarkAsync(fn any, args []any, kwargs map[string]any, name *string) *BenchmarkResult {
	if kwargs == nil {
		kwargs = map[string]any{}
	}
	allTimes := []float64{}

	for i := 0; i < b.WarmupRuns; i++ {
		start := time.Now()
		zpPerfInvoke(fn, args, kwargs)
		_ = time.Since(start)
	}
	for i := 0; i < b.BenchmarkRuns; i++ {
		start := time.Now()
		zpPerfInvoke(fn, args, kwargs)
		allTimes = append(allTimes, zpPerfSeconds(time.Since(start)))
	}

	result := zpPerfNewBenchmarkResult(zpPerfResultName(name, fn), zpPerfMean(allTimes), zpPerfMin(allTimes), zpPerfMax(allTimes), zpPerfStdev(allTimes))
	result.AllTimes = allTimes
	result.IsAsync = true
	b.Results = append(b.Results, result)
	return result
}

// RunSuite runs a benchmark suite.
func (b *PerformanceBenchmarker) RunSuite(suite *BenchmarkSuite) []*BenchmarkResult {
	results := []*BenchmarkResult{}
	for _, benchmarkInfo := range suite.Benchmarks {
		fn := benchmarkInfo["func"]
		name, _ := benchmarkInfo["name"].(string)
		args := benchmarkInfo["args"]
		kwargs := benchmarkInfo["kwargs"]
		results = append(results, b.Benchmark(fn, args, kwargs, &name, nil, nil, nil, false, nil))
	}
	return results
}

// BenchmarkMemory is benchmark_memory. tracemalloc is approximated with
// runtime.ReadMemStats (HeapAlloc); peak is not tracked and equals the after value.
func (b *PerformanceBenchmarker) BenchmarkMemory(fn any, args []any, kwargs map[string]any, name *string) *BenchmarkResult {
	if kwargs == nil {
		kwargs = map[string]any{}
	}

	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	memoryBefore := ms.HeapAlloc

	start := time.Now()
	zpPerfInvoke(fn, args, kwargs)
	end := time.Now()

	runtime.ReadMemStats(&ms)
	memoryAfter := ms.HeapAlloc
	peakMemory := ms.HeapAlloc
	memoryDelta := int64(memoryAfter) - int64(memoryBefore)
	elapsed := zpPerfSeconds(end.Sub(start))

	memoryProfile := zpPerfObj(
		"before_bytes", memoryBefore,
		"after_bytes", memoryAfter,
		"peak_bytes", peakMemory,
		"delta_bytes", memoryDelta,
	)
	metadata := map[string]any{"memory_profile": memoryProfile}

	result := zpPerfNewBenchmarkResult(zpPerfResultName(name, fn), elapsed, elapsed, elapsed, 0)
	result.AllTimes = []float64{elapsed}
	peakMB := float64(peakMemory) / (1024 * 1024)
	deltaMB := float64(memoryDelta) / (1024 * 1024)
	result.PeakMemory = &peakMB
	result.MemoryDelta = &deltaMB
	result.Metadata = metadata
	b.Results = append(b.Results, result)
	return result
}

// CheckTarget checks if a benchmark result meets performance targets.
func (b *PerformanceBenchmarker) CheckTarget(result *BenchmarkResult, target *PerformanceTarget) bool {
	if result.MeanTime > target.MaxTime {
		return false
	}
	if target.MaxMemory != nil && *target.MaxMemory != 0 && result.PeakMemory != nil && *result.PeakMemory != 0 {
		if *result.PeakMemory > *target.MaxMemory/(1024*1024) {
			return false
		}
	}
	if len(target.PercentileTargets) > 0 && len(result.AllTimes) > 0 {
		for percentile, maxTime := range target.PercentileTargets {
			var percentileValue float64
			if len(result.AllTimes) >= 100 {
				percentileValue = zpPerfQuantiles(result.AllTimes, 100)[percentile-1]
			} else {
				percentileValue = zpPerfMax(result.AllTimes)
			}
			if percentileValue > maxTime {
				return false
			}
		}
	}
	return true
}

// Compare compares two benchmark results.
func (b *PerformanceBenchmarker) Compare(result1 *BenchmarkResult, result2 *BenchmarkResult) BenchmarkComparison {
	var speedup float64
	if result2.MeanTime > 0 {
		speedup = result1.MeanTime / result2.MeanTime
	} else {
		speedup = math.Inf(1)
	}
	winner := result1.Name
	if speedup > 1 {
		winner = result2.Name
	}

	var significance *float64
	if len(result1.AllTimes) > 0 && len(result2.AllTimes) > 0 {
		combinedStd := (result1.StdDev + result2.StdDev) / 2
		if combinedStd > 0 {
			difference := math.Abs(result1.MeanTime - result2.MeanTime)
			value := difference / combinedStd
			significance = &value
		}
	}
	return BenchmarkComparison{Speedup: speedup, Winner: winner, StatisticalSignificance: significance}
}

// Profile is profile: Python uses cProfile/pstats, which has no Go equivalent. The
// callable is executed and the same result shape is returned with empty profiling data.
func (b *PerformanceBenchmarker) Profile(fn any, args []any, kwargs map[string]any, profileType string) *entities.OrderedMap[any] {
	if kwargs == nil {
		kwargs = map[string]any{}
	}
	_ = profileType
	zpPerfInvoke(fn, args, kwargs)
	return zpPerfObj("function_calls", zpPerfObj(), "time_per_line", zpPerfObj(), "hotspots", []any{})
}

// DetectRegression detects a performance regression.
func (b *PerformanceBenchmarker) DetectRegression(current *BenchmarkResult, historical []*BenchmarkResult, threshold float64) bool {
	if len(historical) == 0 {
		return false
	}
	means := make([]float64, len(historical))
	for i, r := range historical {
		means[i] = r.MeanTime
	}
	historicalMean := zpPerfMean(means)
	return current.MeanTime > historicalMean*(1+threshold)
}

// CalculateRegressionSeverity calculates the severity of a regression (0-1 scale).
func (b *PerformanceBenchmarker) CalculateRegressionSeverity(current *BenchmarkResult, historical []*BenchmarkResult) float64 {
	if len(historical) == 0 {
		return 0.0
	}
	means := make([]float64, len(historical))
	for i, r := range historical {
		means[i] = r.MeanTime
	}
	historicalMean := zpPerfMean(means)
	if historicalMean == 0 {
		return 0.0
	}
	percentSlower := (current.MeanTime - historicalMean) / historicalMean
	return math.Min(1.0, math.Max(0.0, percentSlower))
}

// ExportResults exports benchmark results as json or csv (any other format is "").
func (b *PerformanceBenchmarker) ExportResults(format string) string {
	switch format {
	case "json":
		data := []any{}
		for _, result := range b.Results {
			data = append(data, zpPerfObj(
				"name", result.Name,
				"mean_time", result.MeanTime,
				"min_time", result.MinTime,
				"max_time", result.MaxTime,
				"std_dev", result.StdDev,
				"is_async", result.IsAsync,
				"cached", result.Cached,
			))
		}
		dumped, _ := value_objects.PyJSONDumps(data, 2)
		return dumped
	case "csv":
		var sb strings.Builder
		sb.WriteString(zpPerfCSVRow([]string{"name", "mean_time", "min_time", "max_time", "std_dev"}))
		for _, result := range b.Results {
			sb.WriteString(zpPerfCSVRow([]string{
				result.Name,
				value_objects.PyStr(result.MeanTime),
				value_objects.PyStr(result.MinTime),
				value_objects.PyStr(result.MaxTime),
				value_objects.PyStr(result.StdDev),
			}))
		}
		return sb.String()
	}
	return ""
}

// zpPerfMeasureSession models the measure @contextmanager. Call Stop() from a defer;
// it records elapsed_time and appends the result to the benchmarker.
type zpPerfMeasureSession struct {
	bench        *PerformanceBenchmarker
	name         string
	ElapsedTime  float64
	ResultStored bool
	start        time.Time
	finished     bool
}

// Measure is measure: returns a session whose Stop records the elapsed time.
func (b *PerformanceBenchmarker) Measure(name string) *zpPerfMeasureSession {
	return &zpPerfMeasureSession{bench: b, name: name, start: time.Now()}
}

// Stop finalizes the measure session: it stores elapsed_time, appends the result and
// sets result_stored.
func (s *zpPerfMeasureSession) Stop() {
	if s.finished {
		return
	}
	s.finished = true
	elapsed := zpPerfSeconds(time.Since(s.start))
	s.ElapsedTime = elapsed
	result := zpPerfNewBenchmarkResult(s.name, elapsed, elapsed, elapsed, 0)
	result.AllTimes = []float64{elapsed}
	s.bench.Results = append(s.bench.Results, result)
	s.ResultStored = true
}

// GetResults returns results by name.
func (b *PerformanceBenchmarker) GetResults(name string) []*BenchmarkResult {
	results := []*BenchmarkResult{}
	for _, result := range b.Results {
		if result.Name == name {
			results = append(results, result)
		}
	}
	return results
}

// AnalyzeStatistics analyzes statistical properties of a benchmark result. The
// percentiles dict has integer keys in Python; Go uses an ordered map with decimal
// string keys (JSON emits the same "25" keys).
func (b *PerformanceBenchmarker) AnalyzeStatistics(result *BenchmarkResult) *entities.OrderedMap[any] {
	if len(result.AllTimes) == 0 {
		return entities.NewOrderedMap[any]()
	}
	times := result.AllTimes
	sorted := append([]float64{}, times...)
	sort.Float64s(sorted)

	percentiles := entities.NewOrderedMap[any]()
	for _, p := range []int{25, 50, 75, 90, 95, 99} {
		var value float64
		if len(times) >= 100 {
			value = zpPerfQuantiles(times, 100)[p-1]
		} else {
			idx := int(float64(len(times)) * float64(p) / 100)
			if idx > len(times)-1 {
				idx = len(times) - 1
			}
			value = sorted[idx]
		}
		percentiles.Set(strconv.Itoa(p), value)
	}

	q1Any, _ := percentiles.Get("25")
	q3Any, _ := percentiles.Get("75")
	q1 := q1Any.(float64)
	q3 := q3Any.(float64)
	iqr := q3 - q1
	lowerBound := q1 - 1.5*iqr
	upperBound := q3 + 1.5*iqr
	outliers := []any{}
	for _, t := range times {
		if t < lowerBound || t > upperBound {
			outliers = append(outliers, t)
		}
	}

	var confidenceInterval [2]float64
	if len(times) > 1 {
		margin := 1.96 * result.StdDev / math.Pow(float64(len(times)), 0.5)
		confidenceInterval = [2]float64{result.MeanTime - margin, result.MeanTime + margin}
	} else {
		confidenceInterval = [2]float64{result.MeanTime, result.MeanTime}
	}

	var variance any = 0
	if result.StdDev != 0 {
		variance = result.StdDev * result.StdDev
	}
	var coefficientOfVariation any = 0
	if result.MeanTime > 0 {
		coefficientOfVariation = result.StdDev / result.MeanTime
	}

	return zpPerfObj(
		"percentiles", percentiles,
		"outliers", outliers,
		"confidence_interval", confidenceInterval,
		"variance", variance,
		"coefficient_of_variation", coefficientOfVariation,
	)
}

// BenchmarkAdaptive is benchmark_adaptive (confidence_level is accepted but unused in
// Python too; the margin is the hard-coded 1.96).
func (b *PerformanceBenchmarker) BenchmarkAdaptive(fn any, name string, minRuns, maxRuns int, confidenceLevel float64, args []any, kwargs map[string]any) *BenchmarkResult {
	if kwargs == nil {
		kwargs = map[string]any{}
	}
	_ = confidenceLevel
	allTimes := []float64{}

	for i := 0; i < minRuns; i++ {
		start := time.Now()
		zpPerfInvoke(fn, args, kwargs)
		allTimes = append(allTimes, zpPerfSeconds(time.Since(start)))
	}

	for len(allTimes) < maxRuns {
		mean := zpPerfMean(allTimes)
		std := 0.0
		if len(allTimes) > 1 {
			std = zpPerfStdev(allTimes)
		}
		if std > 0 {
			cv := std / mean
			if cv < 0.05 {
				break
			}
		}
		for i := 0; i < 10; i++ {
			start := time.Now()
			zpPerfInvoke(fn, args, kwargs)
			allTimes = append(allTimes, zpPerfSeconds(time.Since(start)))
		}
	}

	mean := zpPerfMean(allTimes)
	std := 0.0
	if len(allTimes) > 1 {
		std = zpPerfStdev(allTimes)
	}
	margin := 0.0
	if std > 0 {
		margin = 1.96 * std / math.Pow(float64(len(allTimes)), 0.5)
	}
	confidenceInterval := [2]float64{mean - margin, mean + margin}

	result := zpPerfNewBenchmarkResult(name, mean, zpPerfMin(allTimes), zpPerfMax(allTimes), std)
	result.AllTimes = allTimes
	result.ConfidenceInterval = &confidenceInterval
	b.Results = append(b.Results, result)
	return result
}

// GenerateReport is generate_report. suite is accepted but unused in Python too.
func (b *PerformanceBenchmarker) GenerateReport(suite *BenchmarkSuite, includeCharts bool, includeRecommendations bool) *entities.OrderedMap[any] {
	_ = suite
	summary := entities.NewOrderedMap[any]()
	summary.Set("total_benchmarks", len(b.Results))
	var meanExecutionTime any = 0
	if len(b.Results) > 0 {
		means := make([]float64, len(b.Results))
		for i, r := range b.Results {
			means[i] = r.MeanTime
		}
		meanExecutionTime = zpPerfMean(means)
	}
	summary.Set("mean_execution_time", meanExecutionTime)

	detailedResults := []any{}
	for _, r := range b.Results {
		detailedResults = append(detailedResults, zpPerfObj(
			"name", r.Name,
			"mean_time", r.MeanTime,
			"min_time", r.MinTime,
			"max_time", r.MaxTime,
			"std_dev", r.StdDev,
		))
	}

	report := zpPerfObj("summary", summary, "detailed_results", detailedResults)

	if includeCharts {
		labels := []any{}
		values := []any{}
		for _, r := range b.Results {
			labels = append(labels, r.Name)
			values = append(values, r.MeanTime)
		}
		report.Set("charts", zpPerfObj(
			"execution_times", zpPerfObj(
				"type", "bar",
				"data", zpPerfObj("labels", labels, "values", values),
			),
		))
	}
	if includeRecommendations {
		report.Set("recommendations", b.generateRecommendationsForReport())
	}
	return report
}

// generateRecommendationsForReport is _generate_recommendations_for_report.
func (b *PerformanceBenchmarker) generateRecommendationsForReport() []string {
	if len(b.Results) == 0 {
		return []string{"No results to analyze"}
	}
	recommendations := []string{}

	slowest := b.Results[0]
	for _, r := range b.Results[1:] {
		if r.MeanTime > slowest.MeanTime {
			slowest = r
		}
	}
	if slowest.MeanTime > 0.1 {
		recommendations = append(recommendations, fmt.Sprintf("Optimize '%s' - it's the slowest operation at %.3fs", slowest.Name, slowest.MeanTime))
	}

	highVariance := 0
	for _, r := range b.Results {
		if r.StdDev > r.MeanTime*0.5 {
			highVariance++
		}
	}
	if highVariance > 0 {
		recommendations = append(recommendations, fmt.Sprintf("%d operations have high variance - investigate stability", highVariance))
	}

	if len(recommendations) == 0 {
		return []string{"Performance is within acceptable ranges"}
	}
	return recommendations
}

// zpPerfObj builds an insertion-ordered dict.
func zpPerfObj(kv ...any) *entities.OrderedMap[any] {
	o := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		o.Set(kv[i].(string), kv[i+1])
	}
	return o
}

// zpPerfInvoke mirrors func(*args, **kwargs): args must be a []any and kwargs a
// map[string]any. The checks run in Python's evaluation order (args, then kwargs,
// then callability) so the error matches the first failing step.
func zpPerfInvoke(fn any, args any, kwargs any) any {
	argList, ok := zpPerfAsTuple(args)
	if !ok {
		panic(fmt.Sprintf("argument after * must be an iterable, not %s", zpPerfTypeName(args)))
	}
	kwMap, ok := zpPerfAsDict(kwargs)
	if !ok {
		panic(fmt.Sprintf("argument after ** must be a mapping, not %s", zpPerfTypeName(kwargs)))
	}
	switch f := fn.(type) {
	case zpPerfFunc:
		return f(argList, kwMap)
	case func() any:
		return f()
	case func():
		f()
		return nil
	}
	panic(fmt.Sprintf("'%s' object is not callable", zpPerfTypeName(fn)))
}

// zpPerfAsTuple treats a nil args value as the Python default empty tuple.
func zpPerfAsTuple(v any) ([]any, bool) {
	if v == nil {
		return []any{}, true
	}
	if list, ok := v.([]any); ok {
		return list, true
	}
	return nil, false
}

// zpPerfAsDict treats a nil kwargs value as the Python default empty dict.
func zpPerfAsDict(v any) (map[string]any, bool) {
	if v == nil {
		return map[string]any{}, true
	}
	if m, ok := v.(map[string]any); ok {
		return m, true
	}
	return nil, false
}

// zpPerfTypeName is the Python type name used in TypeError text.
func zpPerfTypeName(v any) string {
	if v == nil {
		return "NoneType"
	}
	switch v.(type) {
	case string:
		return "str"
	case bool:
		return "bool"
	case int:
		return "int"
	case float64:
		return "float"
	case BenchmarkCategory:
		return "BenchmarkCategory"
	}
	t := reflect.TypeOf(v)
	if t.Kind() == reflect.Func {
		return "function"
	}
	return t.String()
}

// zpPerfSeconds converts a duration to perf_counter-style seconds.
func zpPerfSeconds(d time.Duration) float64 { return float64(d.Nanoseconds()) / 1e9 }

// zpPerfResultName mirrors `name or func.__name__`.
func zpPerfResultName(name *string, fn any) string {
	if name != nil && *name != "" {
		return *name
	}
	return zpPerfCallableName(fn)
}

// zpPerfCallableName approximates Python func.__name__ with the Go function name.
func zpPerfCallableName(fn any) string {
	rv := reflect.ValueOf(fn)
	if rv.IsValid() && rv.Kind() == reflect.Func {
		if f := runtime.FuncForPC(rv.Pointer()); f != nil {
			full := f.Name()
			if i := strings.LastIndexByte(full, '.'); i >= 0 {
				return full[i+1:]
			}
			return full
		}
	}
	panic(fmt.Sprintf("'%s' object has no attribute '__name__'", zpPerfTypeName(fn)))
}

// zpPerfOptStr returns the value or nil (Python None).
func zpPerfOptStr(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// zpPerfOptTimeISO returns the naive ISO string or nil (Python None).
func zpPerfOptTimeISO(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormatNaive(*t)
}

// zpPerfSizeof approximates sys.getsizeof for the json.dumps fallback.
func zpPerfSizeof(v any) int {
	if v == nil {
		return 0
	}
	rv := reflect.ValueOf(v)
	if !rv.IsValid() {
		return 0
	}
	return int(rv.Type().Size())
}

// zpPerfCSVRow mirrors csv.writer.writerow (default dialect: ',' delimiter,
// '"' quotechar, minimal quoting, "\r\n" line terminator).
func zpPerfCSVRow(fields []string) string {
	var sb strings.Builder
	for i, field := range fields {
		if i > 0 {
			sb.WriteByte(',')
		}
		sb.WriteString(zpPerfCSVField(field))
	}
	sb.WriteString("\r\n")
	return sb.String()
}

func zpPerfCSVField(field string) string {
	if !strings.ContainsAny(field, ",\"\r\n") {
		return field
	}
	return "\"" + strings.ReplaceAll(field, "\"", "\"\"") + "\""
}

// zpPerfMean mirrors statistics.mean: exact rational sum divided by n.
func zpPerfMean(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	total := new(big.Rat)
	for _, v := range values {
		r := zpPerfRatOf(v)
		if r == nil {
			return value_objects.PySum(values) / float64(len(values))
		}
		total.Add(total, r)
	}
	total.Quo(total, new(big.Rat).SetInt64(int64(len(values))))
	f, _ := total.Float64()
	return f
}

// zpPerfMedian mirrors statistics.median: middle value, or the mean of the two middle
// values.
func zpPerfMedian(values []float64) float64 {
	n := len(values)
	if n == 0 {
		return math.NaN()
	}
	sorted := append([]float64{}, values...)
	sort.Float64s(sorted)
	if n%2 == 1 {
		return sorted[n/2]
	}
	i := n / 2
	return (sorted[i-1] + sorted[i]) / 2
}

// zpPerfQuantiles mirrors statistics.quantiles(data, n=n, method="exclusive"): it
// returns the n-1 cut points.
func zpPerfQuantiles(data []float64, n int) []float64 {
	if n < 1 {
		panic("n must be at least 1")
	}
	if len(data) < 2 {
		panic("must have at least two data points")
	}
	sorted := append([]float64{}, data...)
	sort.Float64s(sorted)
	ld := len(sorted)
	m := ld + 1
	result := make([]float64, 0, n-1)
	for i := 1; i < n; i++ {
		j := i * m / n
		if j < 1 {
			j = 1
		} else if j > ld-1 {
			j = ld - 1
		}
		delta := i*m - j*n
		result = append(result, (sorted[j-1]*float64(n-delta)+sorted[j]*float64(delta))/float64(n))
	}
	return result
}

// zpPerfStdev mirrors statistics.stdev: sqrt(sum((x-mean)^2)/(n-1)) with exact
// deviations; fewer than two values gives 0 (Python raises StatisticsError).
func zpPerfStdev(values []float64) float64 {
	n := len(values)
	if n < 2 {
		return 0
	}
	total := new(big.Rat)
	for _, v := range values {
		r := zpPerfRatOf(v)
		if r == nil {
			return 0
		}
		total.Add(total, r)
	}
	mean := new(big.Rat).Quo(total, new(big.Rat).SetInt64(int64(n)))
	sumSquares := new(big.Rat)
	for _, v := range values {
		r := zpPerfRatOf(v)
		diff := new(big.Rat).Sub(r, mean)
		sumSquares.Add(sumSquares, new(big.Rat).Mul(diff, diff))
	}
	return value_objects.PySqrtRat(new(big.Rat).Quo(sumSquares, new(big.Rat).SetInt64(int64(n-1))))
}

// zpPerfMin mirrors min().
func zpPerfMin(values []float64) float64 {
	if len(values) == 0 {
		panic("min() arg is an empty sequence")
	}
	m := values[0]
	for _, v := range values[1:] {
		if v < m {
			m = v
		}
	}
	return m
}

// zpPerfMax mirrors max().
func zpPerfMax(values []float64) float64 {
	if len(values) == 0 {
		panic("max() arg is an empty sequence")
	}
	m := values[0]
	for _, v := range values[1:] {
		if v > m {
			m = v
		}
	}
	return m
}

// zpPerfRatOf converts a finite float to its exact rational value.
func zpPerfRatOf(f float64) *big.Rat {
	r := new(big.Rat)
	if r.SetFloat64(f) == nil {
		return nil
	}
	return r
}
