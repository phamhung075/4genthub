package database

// The asset's own names, held to being unique WITHOUT a server - the half the fake driver cannot see.
//
// WHY THE FAKE CANNOT SEE THIS CLASS. It records statements and enforces no names, so an asset that
// creates the same name twice runs happily there: the boot then fails on the FIRST REAL DATABASE, in
// one transaction, which rolls the WHOLE schema back and leaves a fresh database to createAll alone -
// 41 tables and none of the production tables the asset would have added. That is what
// uq_cache_context did (CREATE UNIQUE INDEX at :521, ADD CONSTRAINT of the same name at :608, and
// PostgreSQL refuses the second with SQLSTATE 42P07 because a UNIQUE constraint is backed by an index
// of the constraint's name, which already exists). The same class accounted for twelve more names in
// this asset, none of them reachable until the first one was fixed.
//
// The names collected are the ones created in one namespace: CREATE TABLE, CREATE [UNIQUE] INDEX and
// ALTER TABLE ... ADD CONSTRAINT (whose backing index carries the constraint's name). Comment lines
// are dropped first - a section header reading "-- CREATE TABLES" is prose, not a statement, and the
// port's own history has one phantom count from exactly that.

import (
	"regexp"
	"strings"
	"testing"
)

var (
	createdTableName      = regexp.MustCompile(`(?i)CREATE TABLE (?:IF NOT EXISTS )?(?:"?public"?\.)?"?(\w+)"?`)
	createdIndexName      = regexp.MustCompile(`(?i)CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?"?(\w+)"?`)
	createdConstraintName = regexp.MustCompile(`(?i)ADD CONSTRAINT "?(\w+)"?`)
)

// TestTheInitSQLCreatesNoObjectNameTwice fails on any name the asset creates more than once, and
// names the statements. A schema that cannot be applied in one transaction is not a schema.
func TestTheInitSQLCreatesNoObjectNameTwice(t *testing.T) {
	schema := string(databaseInitializerInitSQL)
	if strings.TrimSpace(schema) == "" {
		t.Fatal("the embedded init SQL is empty")
	}

	firstKind := map[string]string{}
	var collisions []string
	for _, line := range strings.Split(schema, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "--") {
			continue
		}
		for _, probe := range []struct {
			kind string
			re   *regexp.Regexp
		}{
			{"CREATE TABLE", createdTableName},
			{"CREATE INDEX", createdIndexName},
			{"ADD CONSTRAINT", createdConstraintName},
		} {
			for _, m := range probe.re.FindAllStringSubmatch(line, -1) {
				name := strings.ToLower(m[1])
				if earlier, seen := firstKind[name]; seen {
					collisions = append(collisions, name+" ("+earlier+" and "+probe.kind+")")
					continue
				}
				firstKind[name] = probe.kind
			}
		}
	}
	if len(collisions) > 0 {
		t.Errorf("the embedded init SQL creates these names more than once, so PostgreSQL refuses the second statement and the whole transaction rolls back: %s",
			strings.Join(collisions, ", "))
	}
	if len(firstKind) == 0 {
		t.Fatal("no created object name was found, so this guard measured nothing")
	}
	t.Logf("searched: %d distinct object names created by the embedded init SQL, %d collision(s)", len(firstKind), len(collisions))
}
