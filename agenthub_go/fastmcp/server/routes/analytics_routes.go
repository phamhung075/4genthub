// analytics_routes.go ports the framework-independent computation helpers of
// server/routes/analytics_routes.py.
//
// The module's three FastAPI handlers query PostgreSQL through raw SQLAlchemy
// sessions (session.execute(text(...)) with row attribute access). The Go
// application/interface layers have no database-session surface and the domain
// repositories expose no equivalent aggregate queries, so the handlers were not
// ported. What is ported are the deterministic helpers whose behaviour the
// handlers delegate to: _analyze_context_lifecycle is SQL-only and is also left
// unported; _calculate_agent_efficiency, _generate_specialization_recommendations,
// _calculate_trend and _calculate_completion_trend are pure functions.
package routes

// calculateAgentEfficiency mirrors _calculate_agent_efficiency.
func calculateAgentEfficiency(completionRate, avgHours, blockedRatio float64) float64 {
	completionScore := (completionRate / 100) * 40
	speedScore := 30 - (avgHours/24)*10
	if speedScore < 0 {
		speedScore = 0
	}
	reliabilityScore := 30 - (blockedRatio * 100)
	if reliabilityScore < 0 {
		reliabilityScore = 0
	}
	return completionScore + speedScore + reliabilityScore
}

// generateSpecializationRecommendations mirrors
// _generate_specialization_recommendations.
func generateSpecializationRecommendations(agentMetrics []map[string]any) []string {
	if len(agentMetrics) == 0 {
		return []string{"No agent data available for recommendations"}
	}
	recommendations := []string{}

	top := agentMetrics[0]
	for _, a := range agentMetrics[1:] {
		if metricFloat(a, "efficiency_score") > metricFloat(top, "efficiency_score") {
			top = a
		}
	}
	if metricFloat(top, "efficiency_score") > 70 {
		recommendations = append(recommendations, "Consider having "+metricString(top, "agent_name")+" mentor other agents")
	}

	struggling := 0
	for _, a := range agentMetrics {
		if metricFloat(a, "completion_rate") < 50 {
			struggling++
		}
	}
	if struggling > 0 {
		recommendations = append(recommendations, "Some agents have low completion rates - consider task reassignment or additional support")
	}

	highVolume := 0
	for _, a := range agentMetrics {
		if metricFloat(a, "total_tasks") > 10 {
			highVolume++
		}
	}
	if float64(highVolume) < float64(len(agentMetrics))*0.5 {
		recommendations = append(recommendations, "Consider specializing agents for specific task types to improve efficiency")
	}
	return recommendations
}

// calculateTrend mirrors _calculate_trend.
func calculateTrend(values []float64) string {
	if len(values) < 2 {
		return "insufficient_data"
	}
	half := len(values) / 2
	recentAvg := sumFloats(values[:half]) / maxFloat(float64(half), 1)
	older := values[half:]
	olderAvg := sumFloats(older) / maxFloat(float64(len(values)-half), 1)
	if recentAvg > olderAvg*1.1 {
		return "improving"
	} else if recentAvg < olderAvg*0.9 {
		return "declining"
	}
	return "stable"
}

// calculateCompletionTrend mirrors _calculate_completion_trend.
func calculateCompletionTrend(dailyMetrics []map[string]any) string {
	completionRates := make([]float64, 0, len(dailyMetrics))
	for _, d := range dailyMetrics {
		created := metricFloat(d, "tasks_created")
		if created < 1 {
			created = 1
		}
		completionRates = append(completionRates, (metricFloat(d, "tasks_completed")/created)*100)
	}
	return calculateTrend(completionRates)
}

func metricFloat(m map[string]any, key string) float64 {
	v, ok := m[key]
	if !ok {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return n
	case float32:
		return float64(n)
	case int:
		return float64(n)
	case int64:
		return float64(n)
	}
	return 0
}

func metricString(m map[string]any, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func sumFloats(values []float64) float64 {
	total := 0.0
	for _, v := range values {
		total += v
	}
	return total
}

func maxFloat(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
