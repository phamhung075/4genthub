package orm

import (
	"context"
	"strings"
	"testing"
)

// The permission policy update is tenant scoped and touches nothing but the policy column.
func TestSeatUpdatePermissionPolicyIsUserScoped(t *testing.T) {
	f := &fakeDriver{}
	repo, err := NewORMSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatalf("NewORMSeatRepository: %v", err)
	}
	if err := repo.UpdatePermissionPolicy(context.Background(), testUser, "seat-1", "yolo"); err != nil {
		t.Fatalf("UpdatePermissionPolicy: %v", err)
	}
	found := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `UPDATE "seats" SET "permission_policy"`) {
			found = true
			if !strings.Contains(q, `WHERE "user_id" = $3 AND "id" = $4`) || strings.Contains(q, `"runtime"`) {
				t.Fatalf("update is not user scoped or touches other columns: %s", q)
			}
		}
	}
	if !found {
		t.Fatalf("no policy update recorded: %v", f.recorded())
	}
}
