package routes

import (
	"context"
	"strings"

	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// MachineWorkFinder provides task discovery for a machine/room.
type MachineWorkFinder interface {
	FindAll(ctx context.Context) ([]*taskdomain.Task, error)
}

// MachineWorkItem represents a task ready for execution by a seat in a room.
type MachineWorkItem struct {
	ID                 string   `json:"id"`
	Title              string   `json:"title"`
	Status             string   `json:"status"`
	Assignee           string   `json:"assignee"`
	ClaimedBy          *string  `json:"claimed_by"`
	AcceptanceCriteria []string `json:"acceptance_criteria"`
	Scope              []string `json:"scope"`
}

// GetMachineWork finds active (todo, in_progress, review) tasks assigned to a room/machine's seats (O7).
func GetMachineWork(ctx context.Context, machine string, finder MachineWorkFinder) ([]MachineWorkItem, error) {
	all, err := finder.FindAll(ctx)
	if err != nil {
		return nil, err
	}

	var work []MachineWorkItem
	for _, t := range all {
		if t == nil || t.Status == nil {
			continue
		}
		status := t.Status.String()
		if status == "done" || status == "cancelled" || status == "archived" {
			continue
		}

		// Strict seat key matching: "room/seat" or room prefix
		matchedAssignee := ""
		for _, a := range t.Assignees {
			if strings.HasPrefix(a, machine+"/") || a == machine {
				matchedAssignee = a
				break
			}
		}
		if matchedAssignee == "" {
			continue
		}

		tID := ""
		if t.ID != nil {
			tID = t.ID.Value
		}

		work = append(work, MachineWorkItem{
			ID:                 tID,
			Title:              t.Title,
			Status:             status,
			Assignee:           matchedAssignee,
			ClaimedBy:          t.ClaimedBy,
			AcceptanceCriteria: t.AcceptanceCriteria,
			Scope:              t.Scope,
		})
	}

	return work, nil
}
