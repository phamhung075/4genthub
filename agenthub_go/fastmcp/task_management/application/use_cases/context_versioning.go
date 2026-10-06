package use_cases

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ChangeType mirrors context_versioning.ChangeType.
type ChangeType string

const (
	ChangeTypeCreate   ChangeType = "create"
	ChangeTypeUpdate   ChangeType = "update"
	ChangeTypeDelete   ChangeType = "delete"
	ChangeTypeMerge    ChangeType = "merge"
	ChangeTypeRollback ChangeType = "rollback"
)

func (e ChangeType) String() string { return string(e) }

// ContextVersion mirrors the context_versioning.ContextVersion dataclass (field
// order and defaults preserved).
type ContextVersion struct {
	VersionID     string
	ContextLevel  value_objects.ContextLevel
	ContextID     string
	VersionNumber int
	Data          *entities.OrderedMap[any]
	ChangeType    ChangeType
	ChangeSummary string
	ChangedBy     string
	CreatedAt     time.Time

	// Metadata.
	ParentVersionID *string
	ChildVersionIDs []string

	// Delta storage (optional).
	Delta       *entities.OrderedMap[any]
	IsMilestone bool
	Tags        []string
}

// GetHash mirrors ContextVersion.get_hash: sha256 of
// json.dumps(data, sort_keys=True).
func (v *ContextVersion) GetHash() (string, error) {
	dataStr, err := contextVersioningSortedDumpJSON(v.Data, -1)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(dataStr))
	return hex.EncodeToString(sum[:]), nil
}

// VersionDiff mirrors the context_versioning.VersionDiff dataclass.
type VersionDiff struct {
	FromVersion string
	ToVersion   string
	Added       *entities.OrderedMap[any]
	Modified    *entities.OrderedMap[any]
	Removed     []string
	UnifiedDiff string
}

// ContextVersioningContextService is the consumer-side view of the
// UnifiedContextService: rollback calls update_context after creating the new
// version.
type ContextVersioningContextService interface {
	UpdateContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID string) error
}

// contextVersioningKey is the Python (level.value, context_id) tuple key.
type contextVersioningKey struct {
	Level     string
	ContextID string
}

// ContextVersioningService mirrors context_versioning.ContextVersioningService.
type ContextVersioningService struct {
	contextService ContextVersioningContextService

	// VersionID -> version.
	Versions map[string]*ContextVersion
	// (level, context_id) -> [version_ids].
	VersionChains map[contextVersioningKey][]string
	// (level, context_id) -> current_version_id.
	CurrentVersions map[contextVersioningKey]string
}

// NewContextVersioningService mirrors ContextVersioningService.__init__.
func NewContextVersioningService(contextService ContextVersioningContextService) *ContextVersioningService {
	return &ContextVersioningService{
		contextService:  contextService,
		Versions:        map[string]*ContextVersion{},
		VersionChains:   map[contextVersioningKey][]string{},
		CurrentVersions: map[contextVersioningKey]string{},
	}
}

// CreateVersion mirrors ContextVersioningService.create_version.
func (s *ContextVersioningService) CreateVersion(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], changeType ChangeType, changeSummary string, changedBy string, isMilestone bool, tags []string) (*ContextVersion, error) {
	key := contextVersioningKey{string(contextLevel), contextID}

	// Get current version if exists.
	currentVersionID, hasCurrent := s.CurrentVersions[key]
	var parentVersion *ContextVersion
	var parentVersionID *string
	if hasCurrent && currentVersionID != "" {
		parentVersion = s.Versions[currentVersionID]
		parentID := currentVersionID
		parentVersionID = &parentID
	}

	// Determine version number.
	versionChain := s.VersionChains[key]
	versionNumber := len(versionChain) + 1

	// Generate version ID.
	versionID := fmt.Sprintf("v_%s_%d_%s", contextID, versionNumber, value_objects.NewUUIDv4()[:8])

	// Calculate delta if parent exists.
	var delta *entities.OrderedMap[any]
	if parentVersion != nil {
		delta = s.calculateDelta(parentVersion.Data, data)
	}

	versionTags := tags
	if len(versionTags) == 0 {
		versionTags = []string{}
	}

	// Create version.
	version := &ContextVersion{
		VersionID:       versionID,
		ContextLevel:    contextLevel,
		ContextID:       contextID,
		VersionNumber:   versionNumber,
		Data:            data.Copy(), // Shallow copy to preserve state.
		ChangeType:      changeType,
		ChangeSummary:   changeSummary,
		ChangedBy:       changedBy,
		CreatedAt:       time.Now().UTC(),
		ParentVersionID: parentVersionID,
		ChildVersionIDs: []string{},
		Delta:           delta,
		IsMilestone:     isMilestone,
		Tags:            versionTags,
	}

	// Update parent's children.
	if parentVersion != nil {
		parentVersion.ChildVersionIDs = append(parentVersion.ChildVersionIDs, versionID)
	}

	// Store version.
	s.Versions[versionID] = version

	// Update version chain.
	s.VersionChains[key] = append(s.VersionChains[key], versionID)

	// Update current version.
	s.CurrentVersions[key] = versionID

	return version, nil
}

// calculateDelta mirrors _calculate_delta.
func (s *ContextVersioningService) calculateDelta(oldData, newData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	added := entities.NewOrderedMap[any]()
	modified := entities.NewOrderedMap[any]()
	removed := []string{}

	// Find added and modified fields.
	for _, key := range newData.Keys() {
		value, _ := newData.Get(key)
		oldValue, exists := oldData.Get(key)
		if !exists {
			added.Set(key, value)
		} else if !value_objects.PyEqual(oldValue, value) {
			m := entities.NewOrderedMap[any]()
			m.Set("old", oldValue)
			m.Set("new", value)
			modified.Set(key, m)
		}
	}

	// Find removed fields.
	for _, key := range oldData.Keys() {
		if !newData.Has(key) {
			removed = append(removed, key)
		}
	}

	delta := entities.NewOrderedMap[any]()
	delta.Set("added", added)
	delta.Set("modified", modified)
	delta.Set("removed", removed)
	return delta
}

// GetVersion mirrors get_version.
func (s *ContextVersioningService) GetVersion(ctx context.Context, versionID string) *ContextVersion {
	return s.Versions[versionID]
}

// GetVersionHistory mirrors get_version_history.
func (s *ContextVersioningService) GetVersionHistory(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, limit, offset int) []*ContextVersion {
	key := contextVersioningKey{string(contextLevel), contextID}
	versionIDs := append([]string{}, s.VersionChains[key]...)

	// Reverse for newest first.
	for i, j := 0, len(versionIDs)-1; i < j; i, j = i+1, j-1 {
		versionIDs[i], versionIDs[j] = versionIDs[j], versionIDs[i]
	}

	// Apply pagination.
	versionIDs = contextVersioningPythonSlice(versionIDs, offset, offset+limit)

	// Get version objects.
	versions := []*ContextVersion{}
	for _, versionID := range versionIDs {
		if version, ok := s.Versions[versionID]; ok {
			versions = append(versions, version)
		}
	}
	return versions
}

// GetDiff mirrors get_diff.
func (s *ContextVersioningService) GetDiff(ctx context.Context, fromVersionID, toVersionID string) *VersionDiff {
	fromVersion, fromOK := s.Versions[fromVersionID]
	toVersion, toOK := s.Versions[toVersionID]
	if !fromOK || !toOK {
		return nil
	}

	// Calculate differences.
	added := entities.NewOrderedMap[any]()
	modified := entities.NewOrderedMap[any]()
	removed := []string{}

	for _, key := range toVersion.Data.Keys() {
		value, _ := toVersion.Data.Get(key)
		fromValue, exists := fromVersion.Data.Get(key)
		if !exists {
			added.Set(key, value)
		} else if !value_objects.PyEqual(fromValue, value) {
			m := entities.NewOrderedMap[any]()
			m.Set("from", fromValue)
			m.Set("to", value)
			modified.Set(key, m)
		}
	}

	for _, key := range fromVersion.Data.Keys() {
		if !toVersion.Data.Has(key) {
			removed = append(removed, key)
		}
	}

	// Generate unified diff.
	fromJSON, _ := contextVersioningSortedDumpJSON(fromVersion.Data, 2)
	toJSON, _ := contextVersioningSortedDumpJSON(toVersion.Data, 2)

	unifiedDiff := contextVersioningUnifiedDiff(
		strings.Split(fromJSON, "\n"),
		strings.Split(toJSON, "\n"),
		fmt.Sprintf("Version %d", fromVersion.VersionNumber),
		fmt.Sprintf("Version %d", toVersion.VersionNumber),
	)

	return &VersionDiff{
		FromVersion: fromVersionID,
		ToVersion:   toVersionID,
		Added:       added,
		Modified:    modified,
		Removed:     removed,
		UnifiedDiff: unifiedDiff,
	}
}

// Rollback mirrors rollback.
func (s *ContextVersioningService) Rollback(ctx context.Context, contextLevel value_objects.ContextLevel, contextID, targetVersionID, userID, reason string) (*ContextVersion, error) {
	// Get target version.
	targetVersion, ok := s.Versions[targetVersionID]
	if !ok || targetVersion == nil {
		return nil, value_objects.ValueErrorf("Version not found: %s", targetVersionID)
	}

	// Verify it belongs to the same context.
	if targetVersion.ContextLevel != contextLevel || targetVersion.ContextID != contextID {
		return nil, value_objects.ValueErrorf("Version belongs to different context")
	}

	// Create new version with rolled back data.
	rollbackVersion, err := s.CreateVersion(
		ctx,
		contextLevel,
		contextID,
		targetVersion.Data.Copy(),
		ChangeTypeRollback,
		fmt.Sprintf("Rollback to version %d: %s", targetVersion.VersionNumber, reason),
		userID,
		false,
		[]string{fmt.Sprintf("rollback_from_v%d", targetVersion.VersionNumber)},
	)
	if err != nil {
		return nil, err
	}

	// Update actual context.
	if err := s.contextService.UpdateContext(ctx, contextLevel, contextID, targetVersion.Data, userID); err != nil {
		return nil, err
	}

	return rollbackVersion, nil
}

// MergeVersions mirrors merge_versions.
func (s *ContextVersioningService) MergeVersions(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, versionIDs []string, mergeStrategy, userID string) (*ContextVersion, error) {
	if len(versionIDs) < 2 {
		return nil, value_objects.ValueErrorf("Need at least 2 versions to merge")
	}

	versions := []*ContextVersion{}
	for _, versionID := range versionIDs {
		if version, ok := s.Versions[versionID]; ok {
			versions = append(versions, version)
		}
	}

	if len(versions) == 0 {
		return nil, value_objects.ValueErrorf("No valid versions found")
	}

	var mergedData *entities.OrderedMap[any]
	switch mergeStrategy {
	case "latest_wins":
		// Sort by creation time and take latest (stable sort).
		sort.SliceStable(versions, func(i, j int) bool { return versions[i].CreatedAt.Before(versions[j].CreatedAt) })
		mergedData = versions[len(versions)-1].Data.Copy()

	case "union":
		// Combine all unique fields.
		mergedData = entities.NewOrderedMap[any]()
		for _, version := range versions {
			for _, key := range version.Data.Keys() {
				value, _ := version.Data.Get(key)
				mergedData.Set(key, value)
			}
		}

	default:
		return nil, value_objects.ValueErrorf("Unknown merge strategy: %s", mergeStrategy)
	}

	tags := []string{}
	for _, version := range versions {
		tags = append(tags, fmt.Sprintf("merged_v%d", version.VersionNumber))
	}

	return s.CreateVersion(
		ctx,
		contextLevel,
		contextID,
		mergedData,
		ChangeTypeMerge,
		fmt.Sprintf("Merged %d versions using %s", len(versions), mergeStrategy),
		userID,
		false,
		tags,
	)
}

// TagVersion mirrors tag_version.
func (s *ContextVersioningService) TagVersion(ctx context.Context, versionID string, tags []string) {
	version, ok := s.Versions[versionID]
	if ok && version != nil {
		version.Tags = append(version.Tags, tags...)
	}
}

// GetMilestoneVersions mirrors get_milestone_versions.
func (s *ContextVersioningService) GetMilestoneVersions(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string) []*ContextVersion {
	key := contextVersioningKey{string(contextLevel), contextID}
	versionIDs := s.VersionChains[key]

	milestones := []*ContextVersion{}
	for _, versionID := range versionIDs {
		if version, ok := s.Versions[versionID]; ok && version.IsMilestone {
			milestones = append(milestones, version)
		}
	}
	return milestones
}

// PruneOldVersions mirrors prune_old_versions.
func (s *ContextVersioningService) PruneOldVersions(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, keepCount int, keepMilestones bool) int {
	key := contextVersioningKey{string(contextLevel), contextID}
	versionIDs := s.VersionChains[key]

	if len(versionIDs) <= keepCount {
		return 0
	}

	// Sort by version number (the chain is already in version-number order).
	versionsToCheck := contextVersioningPrefixCopy(versionIDs, keepCount)
	pruned := 0

	for _, versionID := range versionsToCheck {
		version, ok := s.Versions[versionID]
		if ok && version != nil {
			// Keep milestones if requested.
			if keepMilestones && version.IsMilestone {
				continue
			}

			// Remove version.
			delete(s.Versions, versionID)
			s.VersionChains[key] = contextVersioningRemoveFirst(s.VersionChains[key], versionID)
			pruned++
		}
	}

	return pruned
}

// ExportVersionHistory mirrors export_version_history.
func (s *ContextVersioningService) ExportVersionHistory(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string) (string, error) {
	versions := s.GetVersionHistory(ctx, contextLevel, contextID, 1000, 0)

	exportData := entities.NewOrderedMap[any]()
	exportData.Set("context_level", string(contextLevel))
	exportData.Set("context_id", contextID)
	exportData.Set("export_date", value_objects.IsoFormat(time.Now().UTC()))

	versionList := []any{}
	for _, v := range versions {
		m := entities.NewOrderedMap[any]()
		m.Set("version_id", v.VersionID)
		m.Set("version_number", v.VersionNumber)
		m.Set("change_type", string(v.ChangeType))
		m.Set("change_summary", v.ChangeSummary)
		m.Set("changed_by", v.ChangedBy)
		m.Set("created_at", value_objects.IsoFormat(v.CreatedAt))
		m.Set("is_milestone", v.IsMilestone)
		m.Set("tags", v.Tags)
		m.Set("data", v.Data)
		versionList = append(versionList, m)
	}
	exportData.Set("versions", versionList)

	return value_objects.PyJSONDumps(exportData, 2)
}

// GetStorageStats mirrors get_storage_stats.
func (s *ContextVersioningService) GetStorageStats() *entities.OrderedMap[any] {
	totalVersions := len(s.Versions)
	totalSize := 0
	for _, version := range s.Versions {
		dataStr, err := value_objects.PyJSONDumps(version.Data, -1)
		if err != nil {
			continue
		}
		totalSize += len(dataStr)
	}

	contextsWithVersions := len(s.VersionChains)

	// Python int division: a float when contexts exist, int 0 otherwise.
	var average any = 0
	if contextsWithVersions > 0 {
		average = float64(totalVersions) / float64(contextsWithVersions)
	}

	stats := entities.NewOrderedMap[any]()
	stats.Set("total_versions", totalVersions)
	stats.Set("total_size_bytes", totalSize)
	stats.Set("contexts_tracked", contextsWithVersions)
	stats.Set("average_versions_per_context", average)
	return stats
}

// contextVersioningPythonSlice is Python's list[start:stop].
func contextVersioningPythonSlice(items []string, start, stop int) []string {
	n := len(items)
	if start < 0 {
		start += n
		if start < 0 {
			start = 0
		}
	} else if start > n {
		start = n
	}
	if stop < 0 {
		stop += n
		if stop < 0 {
			stop = 0
		}
	} else if stop > n {
		stop = n
	}
	if start >= stop {
		return []string{}
	}
	return items[start:stop]
}

// contextVersioningPrefixCopy is version_ids[:-keep_count] as a new list.
func contextVersioningPrefixCopy(items []string, keepCount int) []string {
	stop := -keepCount
	n := len(items)
	if stop < 0 {
		stop += n
		if stop < 0 {
			stop = 0
		}
	} else if stop > n {
		stop = n
	}
	return append([]string{}, items[:stop]...)
}

// contextVersioningRemoveFirst is list.remove (the first occurrence).
func contextVersioningRemoveFirst(items []string, value string) []string {
	for i, item := range items {
		if item == value {
			return append(items[:i], items[i+1:]...)
		}
	}
	return items
}

// contextVersioningSortKeys recursively converts OrderedMaps to plain maps so
// PyJSONDumps sorts every key, matching Python's json.dumps(sort_keys=True)
// which sorts recursively (PyJSONDumps preserves OrderedMap order otherwise).
func contextVersioningSortKeys(v any) any {
	switch x := v.(type) {
	case *entities.OrderedMap[any]:
		m := map[string]any{}
		for _, key := range x.Keys() {
			value, _ := x.Get(key)
			m[key] = contextVersioningSortKeys(value)
		}
		return m
	case map[string]any:
		m := map[string]any{}
		for key, value := range x {
			m[key] = contextVersioningSortKeys(value)
		}
		return m
	case []any:
		out := make([]any, len(x))
		for i, item := range x {
			out[i] = contextVersioningSortKeys(item)
		}
		return out
	}
	return v
}

// contextVersioningSortedDumpJSON is json.dumps(v, indent=indent, sort_keys=True).
func contextVersioningSortedDumpJSON(v any, indent int) (string, error) {
	return value_objects.PyJSONDumps(contextVersioningSortKeys(v), indent)
}

// contextVersioningMatch is difflib's Match namedtuple.
type contextVersioningMatch struct {
	i, j, size int
}

// contextVersioningMatcher is the subset of difflib.SequenceMatcher used by
// unified_diff (isjunk=None, autojunk=True).
type contextVersioningMatcher struct {
	a, b []string
	b2j  map[string][]int
}

func newContextVersioningMatcher(a, b []string) *contextVersioningMatcher {
	m := &contextVersioningMatcher{a: a, b: b}
	m.chainB()
	return m
}

// chainB mirrors SequenceMatcher.__chain_b with isjunk=None (no junk purge) and
// autojunk=True.
func (m *contextVersioningMatcher) chainB() {
	b2j := map[string][]int{}
	for i, elt := range m.b {
		b2j[elt] = append(b2j[elt], i)
	}
	if len(m.b) >= 200 {
		ntest := len(m.b)/100 + 1
		for elt, idxs := range b2j {
			if len(idxs) > ntest {
				delete(b2j, elt)
			}
		}
	}
	m.b2j = b2j
}

// findLongestMatch mirrors SequenceMatcher.find_longest_match.
func (m *contextVersioningMatcher) findLongestMatch(alo, ahi, blo, bhi int) contextVersioningMatch {
	besti, bestj, bestsize := alo, blo, 0
	j2len := map[int]int{}
	for i := alo; i < ahi; i++ {
		newj2len := map[int]int{}
		for _, j := range m.b2j[m.a[i]] {
			if j < blo {
				continue
			}
			if j >= bhi {
				break
			}
			k := j2len[j-1] + 1
			newj2len[j] = k
			if k > bestsize {
				besti, bestj, bestsize = i-k+1, j-k+1, k
			}
		}
		j2len = newj2len
	}
	// Extend the best by non-junk elements on each end (bjunk is empty).
	for besti > alo && bestj > blo && m.a[besti-1] == m.b[bestj-1] {
		besti, bestj, bestsize = besti-1, bestj-1, bestsize+1
	}
	for besti+bestsize < ahi && bestj+bestsize < bhi && m.a[besti+bestsize] == m.b[bestj+bestsize] {
		bestsize++
	}
	return contextVersioningMatch{besti, bestj, bestsize}
}

// getMatchingBlocks mirrors SequenceMatcher.get_matching_blocks.
func (m *contextVersioningMatcher) getMatchingBlocks() [][3]int {
	la, lb := len(m.a), len(m.b)
	queue := [][4]int{{0, la, 0, lb}}
	var matching [][3]int
	for len(queue) > 0 {
		q := queue[len(queue)-1]
		queue = queue[:len(queue)-1]
		x := m.findLongestMatch(q[0], q[1], q[2], q[3])
		if x.size > 0 {
			matching = append(matching, [3]int{x.i, x.j, x.size})
			if q[0] < x.i && q[2] < x.j {
				queue = append(queue, [4]int{q[0], x.i, q[2], x.j})
			}
			if x.i+x.size < q[1] && x.j+x.size < q[3] {
				queue = append(queue, [4]int{x.i + x.size, q[1], x.j + x.size, q[3]})
			}
		}
	}
	sort.Slice(matching, func(i, j int) bool {
		if matching[i][0] != matching[j][0] {
			return matching[i][0] < matching[j][0]
		}
		if matching[i][1] != matching[j][1] {
			return matching[i][1] < matching[j][1]
		}
		return matching[i][2] < matching[j][2]
	})

	// Collapse adjacent matching blocks.
	i1, j1, k1 := 0, 0, 0
	nonAdjacent := [][3]int{}
	for _, block := range matching {
		i2, j2, k2 := block[0], block[1], block[2]
		if i1+k1 == i2 && j1+k1 == j2 {
			k1 += k2
		} else {
			if k1 > 0 {
				nonAdjacent = append(nonAdjacent, [3]int{i1, j1, k1})
			}
			i1, j1, k1 = i2, j2, k2
		}
	}
	if k1 > 0 {
		nonAdjacent = append(nonAdjacent, [3]int{i1, j1, k1})
	}
	nonAdjacent = append(nonAdjacent, [3]int{la, lb, 0})
	return nonAdjacent
}

// contextVersioningOpcode is difflib's (tag, i1, i2, j1, j2).
type contextVersioningOpcode struct {
	tag            string
	i1, i2, j1, j2 int
}

// getOpcodes mirrors SequenceMatcher.get_opcodes.
func (m *contextVersioningMatcher) getOpcodes() []contextVersioningOpcode {
	i, j := 0, 0
	var answer []contextVersioningOpcode
	for _, block := range m.getMatchingBlocks() {
		ai, bj, size := block[0], block[1], block[2]
		tag := ""
		if i < ai && j < bj {
			tag = "replace"
		} else if i < ai {
			tag = "delete"
		} else if j < bj {
			tag = "insert"
		}
		if tag != "" {
			answer = append(answer, contextVersioningOpcode{tag, i, ai, j, bj})
		}
		i, j = ai+size, bj+size
		if size > 0 {
			answer = append(answer, contextVersioningOpcode{"equal", ai, i, bj, j})
		}
	}
	return answer
}

// getGroupedOpcodes mirrors SequenceMatcher.get_grouped_opcodes.
func (m *contextVersioningMatcher) getGroupedOpcodes(n int) [][]contextVersioningOpcode {
	codes := m.getOpcodes()
	if len(codes) == 0 {
		codes = []contextVersioningOpcode{{"equal", 0, 1, 0, 1}}
	}

	// Fixup leading and trailing groups if they show no changes.
	if codes[0].tag == "equal" {
		c := codes[0]
		codes[0] = contextVersioningOpcode{c.tag, max(c.i1, c.i2-n), c.i2, max(c.j1, c.j2-n), c.j2}
	}
	if codes[len(codes)-1].tag == "equal" {
		c := codes[len(codes)-1]
		codes[len(codes)-1] = contextVersioningOpcode{c.tag, c.i1, min(c.i2, c.i1+n), c.j1, min(c.j2, c.j1+n)}
	}

	nn := n + n
	var groups [][]contextVersioningOpcode
	var group []contextVersioningOpcode
	for _, c := range codes {
		// End the current group and start a new one whenever there is a large
		// range with no changes.
		if c.tag == "equal" && c.i2-c.i1 > nn {
			group = append(group, contextVersioningOpcode{c.tag, c.i1, min(c.i2, c.i1+n), c.j1, min(c.j2, c.j1+n)})
			groups = append(groups, group)
			group = nil
			c.i1 = max(c.i1, c.i2-n)
			c.j1 = max(c.j1, c.j2-n)
		}
		group = append(group, c)
	}
	if len(group) > 0 && !(len(group) == 1 && group[0].tag == "equal") {
		groups = append(groups, group)
	}
	return groups
}

// contextVersioningFormatRangeUnified mirrors difflib._format_range_unified.
func contextVersioningFormatRangeUnified(start, stop int) string {
	beginning := start + 1
	length := stop - start
	if length == 1 {
		return strconv.Itoa(beginning)
	}
	if length == 0 {
		beginning--
	}
	return strconv.Itoa(beginning) + "," + strconv.Itoa(length)
}

// contextVersioningUnifiedDiff mirrors
// "\n".join(difflib.unified_diff(a, b, fromfile, tofile, lineterm="")).
func contextVersioningUnifiedDiff(a, b []string, fromFile, toFile string) string {
	matcher := newContextVersioningMatcher(a, b)
	groups := matcher.getGroupedOpcodes(3)

	started := false
	out := []string{}
	for _, group := range groups {
		if !started {
			started = true
			out = append(out, "--- "+fromFile)
			out = append(out, "+++ "+toFile)
		}
		first := group[0]
		last := group[len(group)-1]
		file1Range := contextVersioningFormatRangeUnified(first.i1, last.i2)
		file2Range := contextVersioningFormatRangeUnified(first.j1, last.j2)
		out = append(out, "@@ -"+file1Range+" +"+file2Range+" @@")
		for _, c := range group {
			switch c.tag {
			case "equal":
				for _, line := range a[c.i1:c.i2] {
					out = append(out, " "+line)
				}
			case "replace":
				for _, line := range a[c.i1:c.i2] {
					out = append(out, "-"+line)
				}
				for _, line := range b[c.j1:c.j2] {
					out = append(out, "+"+line)
				}
			case "delete":
				for _, line := range a[c.i1:c.i2] {
					out = append(out, "-"+line)
				}
			case "insert":
				for _, line := range b[c.j1:c.j2] {
					out = append(out, "+"+line)
				}
			}
		}
	}
	return strings.Join(out, "\n")
}
