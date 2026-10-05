package value_objects

import "time"

// ClientConfig is the client configuration for synchronization.
type ClientConfig struct {
	ClientID           string
	ClientName         string
	AuthMethod         ClientAuthMethod
	AuthCredentials    map[string]any
	SyncPermissions    []string
	RateLimit          int // requests per minute (default 100)
	SyncFrequency      int // seconds (default 300)
	AllowedRuleTypes   []RuleType
	AutoSync           bool
	ConflictResolution ConflictResolution
	LastSync           *float64
	SyncHistory        []string
}

// NewClientConfig applies the Python defaults (rate 100, frequency 300, all rule
// types, auto-sync, MERGE) and validates. Adjust fields and call Validate to re-check.
func NewClientConfig(clientID, clientName string, auth ClientAuthMethod, creds map[string]any, permissions []string) (*ClientConfig, error) {
	c := &ClientConfig{
		ClientID: clientID, ClientName: clientName, AuthMethod: auth, AuthCredentials: creds, SyncPermissions: permissions,
		RateLimit: 100, SyncFrequency: 300, AllowedRuleTypes: append([]RuleType{}, RuleTypeValues...), AutoSync: true,
		ConflictResolution: ConflictResolutionMerge, SyncHistory: []string{},
	}
	return c, c.Validate()
}

// Validate mirrors __post_init__.
func (c *ClientConfig) Validate() error {
	switch {
	case c.ClientID == "":
		return valueErrorf("Client ID cannot be empty")
	case c.ClientName == "":
		return valueErrorf("Client name cannot be empty")
	case c.RateLimit <= 0:
		return valueErrorf("Rate limit must be positive")
	case c.SyncFrequency <= 0:
		return valueErrorf("Sync frequency must be positive")
	}
	return nil
}

func (c *ClientConfig) AddPermission(p string) {
	if !containsString(c.SyncPermissions, p) {
		c.SyncPermissions = append(c.SyncPermissions, p)
	}
}

func (c *ClientConfig) RemovePermission(p string) {
	for i, x := range c.SyncPermissions {
		if x == p {
			c.SyncPermissions = append(c.SyncPermissions[:i], c.SyncPermissions[i+1:]...)
			return
		}
	}
}

func (c *ClientConfig) HasPermission(p string) bool { return containsString(c.SyncPermissions, p) }

func (c *ClientConfig) CanSyncRuleType(t RuleType) bool {
	for _, x := range c.AllowedRuleTypes {
		if x == t {
			return true
		}
	}
	return false
}

// AddToHistory appends an entry, keeping only the last 100.
func (c *ClientConfig) AddToHistory(entry string) {
	c.SyncHistory = append(c.SyncHistory, entry)
	if len(c.SyncHistory) > 100 {
		c.SyncHistory = c.SyncHistory[len(c.SyncHistory)-100:]
	}
}

// SyncRequest is a synchronization request.
type SyncRequest struct {
	RequestID string
	ClientID  string
	Operation SyncOperation
	Rules     map[string]any
	Metadata  map[string]any
	Timestamp float64
	Priority  int // default 1
}

// NewSyncRequest validates the request (pass priority 1 for the Python default).
func NewSyncRequest(requestID, clientID string, op SyncOperation, rules, metadata map[string]any, timestamp float64, priority int) (*SyncRequest, error) {
	switch {
	case requestID == "":
		return nil, valueErrorf("Request ID cannot be empty")
	case clientID == "":
		return nil, valueErrorf("Client ID cannot be empty")
	case priority < 1:
		return nil, valueErrorf("Priority must be at least 1")
	}
	return &SyncRequest{requestID, clientID, op, rules, metadata, timestamp, priority}, nil
}

func (r *SyncRequest) IsHighPriority() bool { return r.Priority >= 5 }

// SyncResult is the result of a synchronization operation.
type SyncResult struct {
	RequestID      string
	ClientID       string
	Status         SyncStatus
	Operation      SyncOperation
	ProcessedRules []string
	Conflicts      []map[string]any
	Errors         []string
	Warnings       []string
	SyncDuration   float64
	Timestamp      float64
	ChangesApplied int
}

// NewSyncResult validates the result.
func NewSyncResult(requestID, clientID string, status SyncStatus, op SyncOperation, processed []string,
	conflicts []map[string]any, errs, warnings []string, syncDuration, timestamp float64, changesApplied int) (*SyncResult, error) {
	switch {
	case requestID == "":
		return nil, valueErrorf("Request ID cannot be empty")
	case clientID == "":
		return nil, valueErrorf("Client ID cannot be empty")
	case syncDuration < 0:
		return nil, valueErrorf("Sync duration cannot be negative")
	}
	return &SyncResult{requestID, clientID, status, op, processed, conflicts, errs, warnings, syncDuration, timestamp, changesApplied}, nil
}

func (r *SyncResult) IsSuccessful() bool {
	return r.Status == SyncStatusCompleted && len(r.Errors) == 0
}
func (r *SyncResult) HasConflicts() bool { return len(r.Conflicts) > 0 }
func (r *SyncResult) HasWarnings() bool  { return len(r.Warnings) > 0 }
func (r *SyncResult) AddError(e string) {
	if !containsString(r.Errors, e) {
		r.Errors = append(r.Errors, e)
	}
}
func (r *SyncResult) AddWarning(w string) {
	if !containsString(r.Warnings, w) {
		r.Warnings = append(r.Warnings, w)
	}
}
func (r *SyncResult) AddConflict(c map[string]any) { r.Conflicts = append(r.Conflicts, c) }

// RuleConflict is rule conflict information.
type RuleConflict struct {
	RulePath            string
	ClientVersion       string
	ServerVersion       string
	ConflictType        string
	ClientContent       string
	ServerContent       string
	SuggestedResolution string
	AutoResolvable      bool
}

// NewRuleConflict validates path and conflict type.
func NewRuleConflict(rulePath, clientVersion, serverVersion, conflictType, clientContent, serverContent, suggested string, autoResolvable bool) (*RuleConflict, error) {
	if rulePath == "" {
		return nil, valueErrorf("Rule path cannot be empty")
	}
	if conflictType == "" {
		return nil, valueErrorf("Conflict type cannot be empty")
	}
	return &RuleConflict{rulePath, clientVersion, serverVersion, conflictType, clientContent, serverContent, suggested, autoResolvable}, nil
}

func (c *RuleConflict) RequiresManualResolution() bool { return !c.AutoResolvable }

// CompositionResult is the result of a rule composition. Python types
// inheritance_chain as list[RuleInheritance] from entities.rule_entity; a
// value_objects → entities import would cycle in Go, so the entity type is a
// type parameter (instantiate with entities.RuleInheritance).
type CompositionResult[I any] struct {
	ComposedContent     string
	SourceRules         []string
	InheritanceChain    []I
	ConflictsResolved   []string
	CompositionMetadata map[string]any
	Success             bool
	Warnings            []string
}

// NewCompositionResult validates that a successful composition has content.
func NewCompositionResult[I any](composed string, sources []string, chain []I, resolved []string, metadata map[string]any, success bool) (*CompositionResult[I], error) {
	if composed == "" && success {
		return nil, valueErrorf("Successful composition must have content")
	}
	return &CompositionResult[I]{composed, sources, chain, resolved, metadata, success, []string{}}, nil
}

func (r *CompositionResult[I]) HasWarnings() bool    { return len(r.Warnings) > 0 }
func (r *CompositionResult[I]) HasInheritance() bool { return len(r.InheritanceChain) > 0 }
func (r *CompositionResult[I]) AddWarning(w string) {
	if !containsString(r.Warnings, w) {
		r.Warnings = append(r.Warnings, w)
	}
}

// CacheEntry is a cache entry for rule content; C is entities.RuleContent
// (type parameter for the same import-cycle reason as CompositionResult).
type CacheEntry[C any] struct {
	Content     C
	Timestamp   float64 // unix seconds
	AccessCount int
	TTL         float64
}

// NewCacheEntry validates ttl and access count.
func NewCacheEntry[C any](content C, timestamp float64, accessCount int, ttl float64) (*CacheEntry[C], error) {
	if ttl <= 0 {
		return nil, valueErrorf("TTL must be positive")
	}
	if accessCount < 0 {
		return nil, valueErrorf("Access count cannot be negative")
	}
	return &CacheEntry[C]{content, timestamp, accessCount, ttl}, nil
}

func unixNow() float64 { return float64(time.Now().UnixNano()) / 1e9 }

func (e *CacheEntry[C]) IsExpired() bool  { return unixNow() > e.Timestamp+e.TTL }
func (e *CacheEntry[C]) IncrementAccess() { e.AccessCount++ }
func (e *CacheEntry[C]) UpdateTimestamp() { e.Timestamp = unixNow() }

// RuleHierarchyInfo is information about rule hierarchy.
type RuleHierarchyInfo struct {
	TotalRules               int
	MaxDepth                 int
	InheritanceRelationships int
	CircularDependencies     [][]string
	RuleTypesDistribution    map[string]int
	FormatDistribution       map[string]int
}

// NewRuleHierarchyInfo validates counts.
func NewRuleHierarchyInfo(total, maxDepth, relationships int, circular [][]string, types, formats map[string]int) (*RuleHierarchyInfo, error) {
	if total < 0 {
		return nil, valueErrorf("Total rules cannot be negative")
	}
	if maxDepth < 0 {
		return nil, valueErrorf("Max depth cannot be negative")
	}
	return &RuleHierarchyInfo{total, maxDepth, relationships, circular, types, formats}, nil
}

func (h *RuleHierarchyInfo) HasCircularDependencies() bool { return len(h.CircularDependencies) > 0 }
func (h *RuleHierarchyInfo) IsHealthy() bool               { return !h.HasCircularDependencies() }
