package repositories

import "testing"

func TestPortTaskRepoFactoryValidatesDefaultUserID(t *testing.T) {
	_, err := NewTaskRepositoryFactory(nil, portStrPtr(""), nil, nil)
	if err == nil || err.Error() != "Task repository factory initialization requires user authentication. No user ID was provided." {
		t.Fatalf("empty default_user_id: err = %v", err)
	}
	_, err = NewTaskRepositoryFactory(nil, portStrPtr("   "), nil, nil)
	if err == nil {
		t.Fatal("whitespace default_user_id: expected error")
	}
	f, err := NewTaskRepositoryFactory(nil, portStrPtr("  test-user  "), nil, nil)
	if err != nil {
		t.Fatalf("valid default_user_id: %v", err)
	}
	if f.DefaultUserID == nil || *f.DefaultUserID != "test-user" {
		t.Fatalf("DefaultUserID = %v, want stripped test-user", f.DefaultUserID)
	}
}

func TestPortTaskRepoFactoryCreateRequiresProjectID(t *testing.T) {
	f, err := NewTaskRepositoryFactory(nil, nil, nil, nil)
	if err != nil {
		t.Fatalf("constructor: %v", err)
	}
	_, err = f.CreateRepository("", "main", nil)
	if err == nil || err.Error() != "project_id is required" {
		t.Fatalf("CreateRepository: err = %v", err)
	}
	// Python defaults git_branch_name to "main"; with no backend registered the
	// next failure is the missing RepositoryFactory, proving the default path ran.
	_, err = f.CreateRepository("proj", "", portStrPtr("user"))
	if err == nil || err.Error() != "RepositoryFactory is not registered" {
		t.Fatalf("CreateRepository default branch: err = %v", err)
	}
}

func portStrPtr(s string) *string { return &s }
