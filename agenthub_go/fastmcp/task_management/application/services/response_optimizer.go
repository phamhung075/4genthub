package services

import (
	"fmt"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResponseProfile mirrors response_optimizer.ResponseProfile.
type ResponseProfile string

const (
	ResponseProfileMinimal  ResponseProfile = "minimal"
	ResponseProfileStandard ResponseProfile = "standard"
	ResponseProfileDetailed ResponseProfile = "detailed"
	ResponseProfileDebug    ResponseProfile = "debug"
)

// ResponseProfileValues lists members in declaration order.
var ResponseProfileValues = []ResponseProfile{
	ResponseProfileMinimal, ResponseProfileStandard, ResponseProfileDetailed, ResponseProfileDebug,
}

func (p ResponseProfile) String() string { return string(p) }

// zpRespHighFrequencyOps mirrors ResponseOptimizer.HIGH_FREQUENCY_OPS.
var zpRespHighFrequencyOps = []string{
	"list", "get_status", "health_check", "ping", "get_metrics", "get_statistics", "list_agents",
}

// zpRespAIAgentIndicators mirrors ResponseOptimizer.AI_AGENT_INDICATORS.
var zpRespAIAgentIndicators = []string{
	"coding-agent", "@test-orchestrator-agent", "debugger-agent", "system-architect-agent",
	"documentation-agent", "ai-agent", "agent", "autonomous", "orchestrator",
}

// zpRespDebugIndicators mirrors ResponseOptimizer.DEBUG_INDICATORS.
var zpRespDebugIndicators = []string{"debug", "trace", "verbose", "development", "test"}

// ResponseOptimizer mirrors response_optimizer.ResponseOptimizer.
type ResponseOptimizer struct {
	metrics *entities.OrderedMap[any]
}

// NewResponseOptimizer mirrors ResponseOptimizer.__init__.
func NewResponseOptimizer() *ResponseOptimizer {
	o := &ResponseOptimizer{metrics: entities.NewOrderedMap[any]()}
	o.metrics.Set("total_optimized", 0)
	o.metrics.Set("total_bytes_saved", 0)
	o.metrics.Set("average_compression_ratio", 0.0)
	usage := entities.NewOrderedMap[any]()
	usage.Set("minimal", 0)
	usage.Set("standard", 0)
	usage.Set("detailed", 0)
	usage.Set("debug", 0)
	o.metrics.Set("profile_usage", usage)
	return o
}

// OptimizeResponse mirrors ResponseOptimizer.optimize_response.
func (o *ResponseOptimizer) OptimizeResponse(response *entities.OrderedMap[any], profile *ResponseProfile, requestContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if profile == nil {
		p := o.AutoSelectProfile(response, requestContext)
		profile = &p
	}
	originalSize := zpRespStrLen(response)
	optimized := zpRespDeepCopy(response).(*entities.OrderedMap[any])
	optimized = o.RemoveDuplicates(optimized)
	optimized = o.FlattenStructure(optimized)
	optimized = o.RemoveNulls(optimized).(*entities.OrderedMap[any])
	optimized = o.ApplyProfile(optimized, *profile)
	optimized = o.MergeMetadata(optimized)
	optimizedSize := zpRespStrLen(optimized)
	o.updateMetrics(originalSize, optimizedSize, *profile)
	return optimized
}

// AutoSelectProfile mirrors ResponseOptimizer.auto_select_profile.
func (o *ResponseOptimizer) AutoSelectProfile(response *entities.OrderedMap[any], requestContext *entities.OrderedMap[any]) ResponseProfile {
	if requestContext == nil {
		requestContext = entities.NewOrderedMap[any]()
	}
	if v, ok := requestContext.Get("profile"); ok {
		if s, ok := v.(string); ok {
			profileStr := value_objects.PyLower(s)
			for _, p := range ResponseProfileValues {
				if string(p) == profileStr {
					return p
				}
			}
		}
	}
	headers := zpRespGetMap(requestContext, "headers")
	if headers == nil {
		headers = entities.NewOrderedMap[any]()
	}
	params := zpRespGetMap(requestContext, "params")
	if params == nil {
		params = entities.NewOrderedMap[any]()
	}
	operation := value_objects.PyLower(zpRespGetString(response, "operation", ""))
	if value_objects.PyTruthy(zpRespGet(requestContext, "debug", false)) {
		return ResponseProfileDebug
	}
	var assignees any = []any{}
	if dv, ok := response.Get("data"); ok {
		data, isMap := dv.(*entities.OrderedMap[any])
		if !isMap {
			// Python: response.get("data", {}).get(...) raises AttributeError on a non-dict.
			panic("AttributeError: 'data' object has no attribute 'get'")
		}
		assignees = zpRespGet(data, "assignees", []any{})
	}
	userAgent := value_objects.PyLower(zpRespGetString(headers, "User-Agent", ""))
	for _, indicator := range zpRespAIAgentIndicators {
		if zpRespContains(value_objects.PyLower(value_objects.PyStr(assignees)), indicator) ||
			zpRespContains(userAgent, indicator) ||
			zpRespContains(value_objects.PyLower(value_objects.PyStr(params)), indicator) {
			return ResponseProfileDetailed
		}
	}
	for _, indicator := range zpRespDebugIndicators {
		if zpRespContains(value_objects.PyLower(value_objects.PyStr(headers)), indicator) ||
			zpRespContains(value_objects.PyLower(value_objects.PyStr(params)), indicator) {
			return ResponseProfileDebug
		}
	}
	for _, op := range zpRespHighFrequencyOps {
		if zpRespContains(operation, op) {
			return ResponseProfileMinimal
		}
	}
	if data := zpRespGetMap(response, "data"); data != nil {
		for _, key := range []string{"tasks", "items", "results", "contexts", "agents"} {
			if v, ok := data.Get(key); ok {
				if list, ok := v.([]any); ok && len(list) > 10 {
					return ResponseProfileMinimal
				}
			}
		}
	}
	return ResponseProfileStandard
}

// RemoveDuplicates mirrors ResponseOptimizer.remove_duplicates.
func (o *ResponseOptimizer) RemoveDuplicates(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if conf := zpRespGetMap(response, "confirmation"); conf != nil {
		if opDetailsAny, ok := conf.Get("operation_details"); ok {
			if operationDetails, ok := opDetailsAny.(*entities.OrderedMap[any]); ok {
				for _, field := range []string{"operation", "operation_id", "timestamp"} {
					rootVal, rootOk := response.Get(field)
					detailVal, detailOk := operationDetails.Get(field)
					if rootOk && detailOk && value_objects.PyEqual(rootVal, detailVal) {
						operationDetails.Delete(field)
					}
				}
				if operationDetails.Len() == 0 {
					conf.Delete("operation_details")
				}
			}
		}
	}
	if status, ok := response.Get("status"); ok {
		if success, ok2 := response.Get("success"); ok2 {
			if status == "success" && success == true {
				response.Delete("status")
			} else if status == "failure" && success == false {
				response.Delete("status")
			}
		}
	}
	if conf := zpRespGetMap(response, "confirmation"); conf != nil {
		if completed, ok := conf.Get("operation_completed"); ok {
			if value_objects.PyEqual(zpRespGet(response, "success", nil), completed) {
				conf.Delete("operation_completed")
			}
		}
	}
	return response
}

// FlattenStructure mirrors ResponseOptimizer.flatten_structure.
func (o *ResponseOptimizer) FlattenStructure(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if conf := zpRespGetMap(response, "confirmation"); conf != nil {
		// Python: confirmation.get("partial_failures", []) == [] -- an explicit None is not [].
		partial, hasPartial := conf.Get("partial_failures")
		if conf.Len() <= 3 && conf.Has("data_persisted") && (!hasPartial || zpRespIsEmptyList(partial)) {
			meta := zpRespGetMap(response, "meta")
			if meta == nil {
				meta = entities.NewOrderedMap[any]()
				response.Set("meta", meta)
			}
			meta.Set("persisted", zpRespGet(conf, "data_persisted", false))
			response.Delete("confirmation")
		}
	}
	return o.flattenSingleArrays(response).(*entities.OrderedMap[any])
}

// RemoveNulls mirrors ResponseOptimizer.remove_nulls.
func (o *ResponseOptimizer) RemoveNulls(data any) any {
	switch d := data.(type) {
	case *entities.OrderedMap[any]:
		cleaned := entities.NewOrderedMap[any]()
		essential := map[string]bool{
			"data": true, "projects": true, "updated_data": true, "subtasks": true,
			"dependencies": true, "labels": true, "assignees": true,
		}
		for _, key := range d.Keys() {
			value, _ := d.Get(key)
			if essential[key] {
				if key == "data" || key == "updated_data" {
					if value_objects.PyTruthy(value) {
						cleaned.Set(key, o.RemoveNulls(value))
					} else {
						cleaned.Set(key, entities.NewOrderedMap[any]())
					}
				} else {
					if value_objects.PyTruthy(value) {
						cleaned.Set(key, o.RemoveNulls(value))
					} else {
						cleaned.Set(key, []any{})
					}
				}
				continue
			}
			cleanedValue := o.RemoveNulls(value)
			if cleanedValue == nil {
				continue
			}
			if s, ok := cleanedValue.(string); ok && s == "" {
				continue
			}
			switch cv := cleanedValue.(type) {
			case []any:
				if len(cv) == 0 {
					continue
				}
			case *entities.OrderedMap[any]:
				if cv == nil || cv.Len() == 0 {
					continue
				}
			}
			cleaned.Set(key, cleanedValue)
		}
		return cleaned
	case []any:
		cleaned := make([]any, 0, len(d))
		for _, item := range d {
			if item == nil {
				continue
			}
			cleaned = append(cleaned, o.RemoveNulls(item))
		}
		return cleaned
	default:
		return data
	}
}

// ApplyProfile mirrors ResponseOptimizer.apply_profile.
func (o *ResponseOptimizer) ApplyProfile(response *entities.OrderedMap[any], profile ResponseProfile) *entities.OrderedMap[any] {
	switch profile {
	case ResponseProfileMinimal:
		minimal := map[string]bool{"success": true, "operation": true, "data": true, "error": true}
		filtered := entities.NewOrderedMap[any]()
		for _, k := range response.Keys() {
			if minimal[k] {
				v, _ := response.Get(k)
				filtered.Set(k, v)
			}
		}
		if v, ok := response.Get("data"); ok && !filtered.Has("data") {
			filtered.Set("data", v)
		}
		return filtered
	case ResponseProfileStandard:
		standard := map[string]bool{
			"success": true, "operation": true, "data": true, "meta": true,
			"operation_id": true, "timestamp": true, "error": true,
		}
		filtered := entities.NewOrderedMap[any]()
		for _, k := range response.Keys() {
			if standard[k] {
				v, _ := response.Get(k)
				filtered.Set(k, v)
			}
		}
		if response.Has("operation_id") || response.Has("timestamp") {
			if !filtered.Has("meta") {
				filtered.Set("meta", entities.NewOrderedMap[any]())
			}
			if v, ok := response.Get("operation_id"); ok {
				meta, _ := filtered.Get("meta")
				meta.(*entities.OrderedMap[any]).Set("id", v)
				filtered.Delete("operation_id")
			}
			if v, ok := response.Get("timestamp"); ok {
				meta, _ := filtered.Get("meta")
				meta.(*entities.OrderedMap[any]).Set("timestamp", v)
				filtered.Delete("timestamp")
			}
		}
		return filtered
	case ResponseProfileDetailed:
		filtered := entities.NewOrderedMap[any]()
		for _, k := range response.Keys() {
			if k == "confirmation" {
				continue
			}
			if k == "workflow_guidance" {
				continue
			}
			v, _ := response.Get(k)
			filtered.Set(k, v)
		}
		if guidance, ok := response.Get("workflow_guidance"); ok {
			if g, ok := guidance.(*entities.OrderedMap[any]); ok {
				filtered.Set("hints", o.simplifyWorkflowGuidance(g))
			}
		}
		return filtered
	default: // DEBUG
		debugResponse := response.Copy()
		if !debugResponse.Has("debug_info") {
			info := entities.NewOrderedMap[any]()
			info.Set("profile_used", "debug")
			info.Set("optimization_steps", []any{
				"duplicates_removed", "structure_flattened", "nulls_removed", "metadata_merged",
			})
			info.Set("original_size_estimate", zpRespStrLen(response))
			info.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
			debugResponse.Set("debug_info", info)
		}
		return debugResponse
	}
}

// MergeMetadata mirrors ResponseOptimizer.merge_metadata.
func (o *ResponseOptimizer) MergeMetadata(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !response.Has("meta") {
		response.Set("meta", entities.NewOrderedMap[any]())
	}
	meta, _ := response.Get("meta")
	metaMap, _ := meta.(*entities.OrderedMap[any])
	conf := zpRespGetMap(response, "confirmation")
	// data_persisted is false exactly when the call failed or carried no data, so an
	// operation_id on such a response names no row. Exposing it as "id" gave every caller
	// a phantom handle: a refused create returned meta.id, and every later update against
	// that id answered "Task not found". Absent proof of persistence is not proof of a row.
	persisted := false
	if conf != nil {
		if v, ok := conf.Get("data_persisted"); ok {
			persisted = value_objects.PyTruthy(v)
		}
	}
	for _, field := range []string{"operation_id", "timestamp", "operation"} {
		if v, ok := response.Get(field); ok {
			if field == "operation_id" {
				if persisted {
					metaMap.Set("id", v)
				}
			} else {
				metaMap.Set(field, v)
			}
			response.Delete(field)
		}
	}
	if conf != nil {
		if v, ok := conf.Get("data_persisted"); ok {
			metaMap.Set("persisted", v)
		}
		if v, ok := conf.Get("partial_failures"); ok && value_objects.PyTruthy(v) {
			metaMap.Set("partial_failures", v)
		}
		response.Delete("confirmation")
	}
	if !value_objects.PyTruthy(metaMap) {
		response.Delete("meta")
	}
	return response
}

func (o *ResponseOptimizer) flattenSingleArrays(data any) any {
	switch d := data.(type) {
	case *entities.OrderedMap[any]:
		flattened := entities.NewOrderedMap[any]()
		for _, key := range d.Keys() {
			value, _ := d.Get(key)
			if list, ok := value.([]any); ok && len(list) == 1 {
				flattened.Set(key, o.flattenSingleArrays(list[0]))
			} else {
				flattened.Set(key, o.flattenSingleArrays(value))
			}
		}
		return flattened
	case []any:
		out := make([]any, len(d))
		for i, item := range d {
			out[i] = o.flattenSingleArrays(item)
		}
		return out
	default:
		return data
	}
}

func (o *ResponseOptimizer) simplifyWorkflowGuidance(guidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	hints := entities.NewOrderedMap[any]()
	if nextSteps, ok := guidance.Get("next_steps"); ok {
		switch ns := nextSteps.(type) {
		case *entities.OrderedMap[any]:
			if recs, ok := ns.Get("recommendations"); ok && value_objects.PyTruthy(recs) {
				if list, ok := recs.([]any); ok {
					if len(list) > 0 {
						hints.Set("next", list[0])
					}
				} else {
					hints.Set("next", value_objects.PyStr(recs))
				}
			}
			if required, ok := ns.Get("required_actions"); ok && value_objects.PyTruthy(required) {
				switch r := required.(type) {
				case string:
					hints.Set("required", []any{r})
				case []any:
					if len(r) > 3 {
						r = r[:3]
					}
					hints.Set("required", r)
				default:
					hints.Set("required", []any{value_objects.PyStr(required)})
				}
			}
		case []any:
			if len(ns) > 0 {
				hints.Set("next", ns[0])
			}
		}
	}
	if optional, ok := guidance.Get("optional_actions"); ok {
		switch list := optional.(type) {
		case []any:
			if len(list) > 2 {
				list = list[:2]
			}
			hints.Set("tips", list)
		case string:
			r := []rune(list)
			if len(r) > 2 {
				r = r[:2]
			}
			hints.Set("tips", string(r))
		default:
			panic("TypeError: object is not subscriptable")
		}
	}
	if autoGuidance, ok := guidance.Get("autonomous_guidance"); ok {
		if ag, ok := autoGuidance.(*entities.OrderedMap[any]); ok {
			if confidence, ok := ag.Get("confidence"); ok {
				hints.Set("confidence", confidence)
			}
		}
	}
	return hints
}

func (o *ResponseOptimizer) calculateReductionPercentage(original, optimized int) float64 {
	if original == 0 {
		return 0.0
	}
	return (float64(original-optimized) / float64(original)) * 100
}

func (o *ResponseOptimizer) updateMetrics(originalSize, optimizedSize int, profile ResponseProfile) {
	totalOptimized, _ := o.metrics.Get("total_optimized")
	o.metrics.Set("total_optimized", totalOptimized.(int)+1)
	saved, _ := o.metrics.Get("total_bytes_saved")
	o.metrics.Set("total_bytes_saved", saved.(int)+(originalSize-optimizedSize))
	usageAny, _ := o.metrics.Get("profile_usage")
	usage := usageAny.(*entities.OrderedMap[any])
	count, _ := usage.Get(string(profile))
	usage.Set(string(profile), count.(int)+1)
	reduction := o.calculateReductionPercentage(originalSize, optimizedSize)
	avgAny, _ := o.metrics.Get("average_compression_ratio")
	avg := avgAny.(float64)
	total := totalOptimized.(int) + 1
	o.metrics.Set("average_compression_ratio", (avg*float64(total-1)+reduction)/float64(total))
}

// GetMetrics mirrors ResponseOptimizer.get_metrics.
func (o *ResponseOptimizer) GetMetrics() *entities.OrderedMap[any] {
	totalOptimized, _ := o.metrics.Get("total_optimized")
	saved, _ := o.metrics.Get("total_bytes_saved")
	avg, _ := o.metrics.Get("average_compression_ratio")
	usageAny, _ := o.metrics.Get("profile_usage")
	usage := usageAny.(*entities.OrderedMap[any])
	out := entities.NewOrderedMap[any]()
	out.Set("total_responses_optimized", totalOptimized)
	out.Set("total_bytes_saved", saved)
	out.Set("average_compression_ratio", fmt.Sprintf("%.1f%%", avg.(float64)))
	out.Set("target_compression", "60%")
	out.Set("target_achieved", avg.(float64) >= 60)
	out.Set("profile_usage", usage)
	var mostUsed any
	if totalOptimized.(int) > 0 {
		bestKey := ""
		bestVal := -1
		for _, k := range usage.Keys() {
			v, _ := usage.Get(k)
			if v.(int) > bestVal {
				bestVal = v.(int)
				bestKey = k
			}
		}
		mostUsed = bestKey
	}
	out.Set("most_used_profile", mostUsed)
	return out
}

func zpRespStrLen(v any) int { return utf8.RuneCountInString(value_objects.PyStr(v)) }

func zpRespGet(m *entities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}

func zpRespGetMap(m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	if v, ok := m.Get(key); ok {
		if mm, ok := v.(*entities.OrderedMap[any]); ok {
			return mm
		}
	}
	return nil
}

func zpRespGetString(m *entities.OrderedMap[any], key, def string) string {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return def
}

func zpRespContains(haystack, needle string) bool {
	if needle == "" {
		return false
	}
	for i := 0; i+len(needle) <= len(haystack); i++ {
		if haystack[i:i+len(needle)] == needle {
			return true
		}
	}
	return false
}

func zpRespIsEmptyList(v any) bool {
	list, ok := v.([]any)
	return ok && len(list) == 0
}

func zpRespDeepCopy(v any) any {
	switch x := v.(type) {
	case *entities.OrderedMap[any]:
		if x == nil {
			return (*entities.OrderedMap[any])(nil)
		}
		c := entities.NewOrderedMap[any]()
		for _, k := range x.Keys() {
			val, _ := x.Get(k)
			c.Set(k, zpRespDeepCopy(val))
		}
		return c
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = zpRespDeepCopy(e)
		}
		return out
	default:
		return v
	}
}
