// task_evidence_routes.go holds the WRITE path over the task-event ledger: the POST that records a
// client's evidence submission (the shas, the raw `git diff --numstat` text and the test result, and
// NOTHING else - no file contents, no test output bodies).
//
// It mirrors task_event_routes.go rather than widening UserTaskController, for the reason that file
// gives: a narrow interface keeps the change in the files this item owns. It also reuses that file's
// 404 seam verbatim - the task is asked for first, through the same controller GetTaskEvents uses, so
// a task this user cannot see is refused before anything is decided or written, and the negative can
// not be bypassed by filtering later.
//
// The route is guarded by the SAME wrapper as GET /{task_id}/events - the ordinary `authed` over
// AGENTHUB_TOKEN. There is no machine token: e5ecff63 removed it.
package routes

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// EvidenceNumstatMaxBytes is the cap on the raw `git diff --numstat` text one submission may carry.
// The numstat is the only unbounded part of a submission, and it is the part a reader checks the
// shas against, so a payload past this is refused with a message that NAMES the cap rather than
// truncated silently: a truncated numstat describes a diff that never happened.
const EvidenceNumstatMaxBytes = 1 << 20 // 1 MiB

// TaskEvidence is one submission, already read off the request body. It is the request's own fields
// and nothing else: the two shas, the raw numstat text, and the test block, whose failed list may be
// absent/empty and whose command may be empty (a submission with no test run).
type TaskEvidence struct {
	BaseSHA string
	HeadSHA string
	Numstat string
	// TestCommand/TestExitCode/TestFailed are the request's `test` object, flattened here because it
	// is three values rather than a nested type; evidencePayload nests them back into the wire shape.
	TestCommand  string
	TestExitCode int
	TestFailed   []string
}

// ErrEvidenceDuplicate is what the writer returns when the submission's head_sha is already the
// task's latest evidence. It is the 409's whole decision: the writer makes it inside the transaction
// that would append the entry, and this package only maps it to the status.
var ErrEvidenceDuplicate = errors.New("task_events: this head_sha is already this task's latest evidence")

// TaskEvidenceWriter is the minimal write surface the handler needs: one call that decides whether
// the submission duplicates the task's latest evidence and, when it does not, appends the
// evidence_submitted entry - the decision and the append together, inside one transaction.
//
// headSHA is passed beside payload because the decision reads it while the entry stores it: both come
// from the one TaskEvidence the handler validated, in one expression, so they cannot disagree.
type TaskEvidenceWriter interface {
	RecordEvidence(ctx context.Context, taskID string, headSHA string, payload map[string]any) (*taskdomain.TaskEvent, error)
}

// SubmitTaskEvidence ports POST /{task_id}/evidence.
//
// THE ORDER IS THE CONTRACT: the payload is validated first (422 for a blank sha or an over-cap
// numstat), then the task is asked for through the same controller GetTaskEvents uses (404 for one
// this user cannot see), and only then is the writer reached, which is where 409 lives.
func SubmitTaskEvidence(ctx context.Context, taskID string, evidence TaskEvidence, currentUser *authdomain.User,
	tasks UserTaskController, writer TaskEvidenceWriter) (*taskdomain.OrderedMap[any], error) {
	if strings.TrimSpace(evidence.BaseSHA) == "" {
		return nil, httpErr(422, "base_sha is required")
	}
	if strings.TrimSpace(evidence.HeadSHA) == "" {
		return nil, httpErr(422, "head_sha is required")
	}
	if len(evidence.Numstat) > EvidenceNumstatMaxBytes {
		return nil, httpErr(422, fmt.Sprintf("numstat is %d bytes, over the %d byte cap",
			len(evidence.Numstat), EvidenceNumstatMaxBytes))
	}

	userID := currentUserID(currentUser)

	// The task FIRST, through the same seam GetTaskEvents uses: !Success there is the 404, and the
	// writer is never reached for a task this user cannot see.
	result, err := tasks.GetTask(ctx, taskID, userID)
	if err != nil {
		return nil, httpErr(500, "Failed to get task")
	}
	if !result.Success {
		return nil, httpErr(404, "Task not found")
	}

	event, err := writer.RecordEvidence(ctx, taskID, evidence.HeadSHA, evidencePayload(evidence))
	if err != nil {
		if errors.Is(err, ErrEvidenceDuplicate) {
			return nil, httpErr(409, "Evidence for this head_sha has already been submitted")
		}
		return nil, httpErr(500, "Failed to record evidence")
	}

	return evidenceEventBody(event), nil
}

// evidencePayload is what the entry stores: the SAME fields as the request. The nested `test` block
// is the request's own shape, and `failed` is always emitted as an array so a reader does not have to
// treat absent and empty as two cases; nothing the client did not send is added.
func evidencePayload(evidence TaskEvidence) map[string]any {
	failed := evidence.TestFailed
	if failed == nil {
		failed = []string{}
	}
	return map[string]any{
		"base_sha": evidence.BaseSHA,
		"head_sha": evidence.HeadSHA,
		"numstat":  evidence.Numstat,
		"test": map[string]any{
			"command":   evidence.TestCommand,
			"exit_code": evidence.TestExitCode,
			"failed":    failed,
		},
	}
}

// evidenceEventBody is the created event as the ledger read returns it: the same eight keys in the
// same order GetTaskEvents builds per event, so a client parses the POST's answer and the read's rows
// with one reader. It is a second copy of that eight-line build on purpose - GetTaskEvents is not
// this item's to reshape - so the two must be kept in step by hand.
func evidenceEventBody(event *taskdomain.TaskEvent) *taskdomain.OrderedMap[any] {
	item := taskdomain.NewOrderedMap[any]()
	item.Set("id", event.ID)
	item.Set("task_id", event.TaskID)
	item.Set("seq", event.Seq)
	item.Set("kind", string(event.Kind))
	item.Set("actor_kind", string(event.ActorKind))
	item.Set("actor_id", event.ActorID)
	item.Set("payload", event.Payload)
	// The same RFC3339 string the ledger read emits (task_event_routes.go), so the POST's answer and
	// the read's rows are one shape: a time.Time is not JSON serializable by this server's writer.
	item.Set("created_at", event.CreatedAt.UTC().Format(time.RFC3339))
	return item
}
