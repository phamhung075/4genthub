package orm

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
)

// moduleVersionChecksum is the lowercase sha256 hex digest of content.
func moduleVersionChecksum(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

// nullableUUID returns an empty target column as NULL.
func nullableUUID(s string) any {
	if s == "" {
		return nil
	}
	return s
}

type moduleRefJSON struct {
	Slug    string `json:"slug"`
	Version string `json:"version"`
}

type opJSON struct {
	Kind    string `json:"kind"`
	Slug    string `json:"slug"`
	Version string `json:"version"`
	Content string `json:"content"`
}

type fileJSON struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

// encodeModuleRefs stores the refs in caller order.
func encodeModuleRefs(refs []resolver.ModuleRef) (json.RawMessage, error) {
	out := make([]moduleRefJSON, 0, len(refs))
	for _, ref := range refs {
		out = append(out, moduleRefJSON{Slug: ref.Slug, Version: ref.Version})
	}
	b, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(b), nil
}

// decodeModuleRefs parses a module_refs JSONB value.
func decodeModuleRefs(raw json.RawMessage) ([]resolver.ModuleRef, error) {
	if len(raw) == 0 {
		return []resolver.ModuleRef{}, nil
	}
	var rows []moduleRefJSON
	if err := json.Unmarshal(raw, &rows); err != nil {
		return nil, err
	}
	refs := make([]resolver.ModuleRef, 0, len(rows))
	for _, row := range rows {
		refs = append(refs, resolver.ModuleRef{Slug: row.Slug, Version: row.Version})
	}
	return refs, nil
}

// moduleRefsChecksum canonicalises the ref order so equal sets hash equally.
func moduleRefsChecksum(raw json.RawMessage) (string, error) {
	refs, err := decodeModuleRefs(raw)
	if err != nil {
		return "", err
	}
	sort.Slice(refs, func(i, j int) bool {
		if refs[i].Slug != refs[j].Slug {
			return refs[i].Slug < refs[j].Slug
		}
		return refs[i].Version < refs[j].Version
	})
	b, err := json.Marshal(refs)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}

// encodeOps stores the overlay ops in slice order.
func encodeOps(ops []resolver.Op) (json.RawMessage, error) {
	out := make([]opJSON, 0, len(ops))
	for _, op := range ops {
		out = append(out, opJSON{Kind: string(op.Kind), Slug: op.Slug, Version: op.Version, Content: op.Content})
	}
	b, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(b), nil
}

// decodeOps parses an ops JSONB value.
func decodeOps(raw json.RawMessage) ([]resolver.Op, error) {
	if len(raw) == 0 {
		return []resolver.Op{}, nil
	}
	var rows []opJSON
	if err := json.Unmarshal(raw, &rows); err != nil {
		return nil, err
	}
	ops := make([]resolver.Op, 0, len(rows))
	for _, row := range rows {
		ops = append(ops, resolver.Op{Kind: resolver.OpKind(row.Kind), Slug: row.Slug, Version: row.Version, Content: row.Content})
	}
	return ops, nil
}

// encodeFiles stores the resolved files in slice order.
func encodeFiles(files []domainrepo.ResolvedFile) (json.RawMessage, error) {
	out := make([]fileJSON, 0, len(files))
	for _, f := range files {
		out = append(out, fileJSON{Path: f.Path, Content: f.Content})
	}
	b, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(b), nil
}

// decodeFiles parses a files JSONB value.
func decodeFiles(raw json.RawMessage) ([]domainrepo.ResolvedFile, error) {
	if len(raw) == 0 {
		return []domainrepo.ResolvedFile{}, nil
	}
	var rows []fileJSON
	if err := json.Unmarshal(raw, &rows); err != nil {
		return nil, err
	}
	files := make([]domainrepo.ResolvedFile, 0, len(rows))
	for _, row := range rows {
		files = append(files, domainrepo.ResolvedFile{Path: row.Path, Content: row.Content})
	}
	return files, nil
}

// encodePolicy stores a policy object.
func encodePolicy(policy map[string]any) (json.RawMessage, error) {
	if policy == nil {
		return json.RawMessage("{}"), nil
	}
	b, err := json.Marshal(policy)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(b), nil
}

// decodePolicy parses a policy JSONB value.
func decodePolicy(raw json.RawMessage) (map[string]any, error) {
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	out := map[string]any{}
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func moduleToDomain(row *seatdb.ModuleORM) *domainrepo.Module {
	return &domainrepo.Module{
		ID: row.ID, UserID: row.UserID, Slug: row.Slug,
		Kind: resolver.ModuleKind(row.Kind), CreatedAt: row.CreatedAt,
	}
}

func moduleVersionToDomain(row *seatdb.ModuleVersionORM) *domainrepo.ModuleVersion {
	return &domainrepo.ModuleVersion{
		ID: row.ID, UserID: row.UserID, ModuleID: row.ModuleID,
		Version: row.Version, Content: row.Content, Checksum: row.Checksum,
		CreatedAt: row.CreatedAt,
	}
}

func seatTypeToDomain(row *seatdb.SeatTypeORM) *domainrepo.SeatType {
	return &domainrepo.SeatType{
		ID: row.ID, UserID: row.UserID, Slug: row.Slug, Name: row.Name,
		Description: row.Description, DefaultRuntime: row.DefaultRuntime, CreatedAt: row.CreatedAt,
	}
}

func seatTypeVersionToDomain(row *seatdb.SeatTypeVersionORM) (*domainrepo.SeatTypeVersion, error) {
	refs, err := decodeModuleRefs(row.ModuleRefs)
	if err != nil {
		return nil, err
	}
	return &domainrepo.SeatTypeVersion{
		ID: row.ID, UserID: row.UserID, SeatTypeID: row.SeatTypeID, Version: row.Version,
		ModuleRefs: refs, CreatedAt: row.CreatedAt,
	}, nil
}

func roomToDomain(row *seatdb.RoomORM) *domainrepo.Room {
	return &domainrepo.Room{
		ID: row.ID, UserID: row.UserID, Slug: row.Slug, Name: row.Name,
		CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt,
	}
}

func seatToDomain(row *seatdb.SeatORM) *domainrepo.Seat {
	return &domainrepo.Seat{
		ID: row.ID, UserID: row.UserID, RoomID: row.RoomID, SeatKey: row.SeatKey,
		SeatTypeID: row.SeatTypeID, PinnedVersion: row.PinnedVersion, Runtime: row.Runtime,
		Model: row.Model, Status: row.Status, CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt,
	}
}

func overlayToDomain(row *seatdb.OverlayORM) (*domainrepo.Overlay, error) {
	ops, err := decodeOps(row.Ops)
	if err != nil {
		return nil, err
	}
	overlay := &domainrepo.Overlay{
		ID: row.ID, UserID: row.UserID, Scope: row.Scope, Ops: ops,
		CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt,
	}
	if row.RoomID != nil {
		overlay.RoomID = *row.RoomID
	}
	if row.SeatID != nil {
		overlay.SeatID = *row.SeatID
	}
	return overlay, nil
}

func seatLinkToDomain(row *seatdb.SeatLinkORM) *domainrepo.SeatLink {
	return &domainrepo.SeatLink{
		ID: row.ID, UserID: row.UserID, FromSeatID: row.FromSeatID, ToSeatID: row.ToSeatID,
		Kind: row.Kind, Allow: row.Allow, CreatedAt: row.CreatedAt,
	}
}

func resolvedSeatToDomain(row *seatdb.ResolvedSeatORM) (*domainrepo.ResolvedSeat, error) {
	files, err := decodeFiles(row.Files)
	if err != nil {
		return nil, err
	}
	policy, err := decodePolicy(row.Policy)
	if err != nil {
		return nil, err
	}
	return &domainrepo.ResolvedSeat{
		ID: row.ID, UserID: row.UserID, SeatID: row.SeatID, Hash: row.Hash,
		Runtime: row.Runtime, Files: files, Policy: policy, CreatedAt: row.CreatedAt,
	}, nil
}

func seatSettingsToDomain(row *seatdb.SeatSettingsORM) *domainrepo.SeatSettings {
	return &domainrepo.SeatSettings{UserID: row.UserID, FollowLatest: row.FollowLatest}
}
