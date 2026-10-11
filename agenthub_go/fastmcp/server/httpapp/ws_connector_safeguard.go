// ws_connector_safeguard.go holds the connector socket's phase-1 vocabulary that is not the frame
// loop itself: the protocol version, the heartbeat, the capabilities the server enables, the
// per-connector liveness the rigd dead-man needs, and the alerts 7.3 raises.
//
// It is a file of its own so the frame loop in ws_mount.go stays a frame loop: everything here is
// either a constant the doc names or the machinery behind one of its two alerts.
package httpapp

import (
	"context"
	"strings"
	"sync"
	"time"

	rigdb "agenthub/fastmcp/rig_safeguard/infrastructure/database"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// The connector socket's ruled vocabulary (rigd-boundaries.md 2.2, 2.3, 7.6).
const (
	// connectorProtocolVersion is the version this server speaks. ready.protocol is the smaller of
	// hello.protocol and this one, and a missing hello.protocol means 1 (2.2).
	connectorProtocolVersion = 1
	// connectorHeartbeatSeconds is ready.heartbeat_s: how often the client pings. Three of them are
	// both the server's idle close below and the rigd dead-man (2.2, 7.3).
	connectorHeartbeatSeconds = 25
	// connectorCapabilityIngest and connectorCapabilitySafeguards are the capabilities this server
	// enables in phase 1 (2.3.4, 7.6). `commands` is phase 2 and `ledger` is P4, and the server never
	// echoes a capability it cannot serve: that is what stops a phase-1 client from sending their
	// frames at all (2.3.1).
	connectorCapabilityIngest     = "ingest"
	connectorCapabilitySafeguards = "safeguards"
	// safeguardAlertEventType and rigSafeguardEntity are 7.3's two ruled names: the notification the
	// server raises is `safeguard_alert`, and it travels as the new entity `rig_safeguard` on the
	// existing data-change push.
	safeguardAlertEventType = "safeguard_alert"
	rigSafeguardEntity      = "rig_safeguard"
)

// wsConnectorIdleTimeout is the server's own heartbeat close (2.2): a socket that has sent no frame
// for 3 x heartbeat_s is closed. It keeps both sides under the production proxy's read timeout, and
// it is what lets the rigd dead-man below notice a machine that vanished without closing its
// sockets. It is a variable so a test can drive the close without waiting 75 seconds.
var wsConnectorIdleTimeout = func() time.Duration {
	return 3 * connectorHeartbeatSeconds * time.Second
}

// wsConnectorDeadmanAfter arms the rigd dead-man. It is a seam, so the alert is tested by driving
// the callback rather than by reading wall time.
var wsConnectorDeadmanAfter = time.AfterFunc

// wsCapabilities reads hello.capabilities. Anything that is not a list of non-empty strings is not a
// capability the client advertised (2.3.5: an unreadable field is not an error).
func wsCapabilities(v any) map[string]bool {
	caps := map[string]bool{}
	list, ok := v.([]any)
	if !ok {
		return caps
	}
	for _, item := range list {
		if name, ok := item.(string); ok && name != "" {
			caps[name] = true
		}
	}
	return caps
}

// wsEnabledCapabilities is ready.capabilities: the subset of the client's list that this server
// enables, named in the server's own order. A client that advertised none is echoed none, and the
// frames it has always sent keep working - the echo gates the capability-bound kinds only (2.3.1),
// never the ingest a phase-1 client already relies on.
func wsEnabledCapabilities(advertised map[string]bool) []any {
	enabled := []any{}
	for _, name := range []string{connectorCapabilityIngest, connectorCapabilitySafeguards} {
		if advertised[name] {
			enabled = append(enabled, name)
		}
	}
	return enabled
}

// wsConnectorLiveness is what one connector's hello made the server remember.
type wsConnectorLiveness struct {
	// safeguards is true when the server echoed `safeguards`, which is the gate on the safeguard
	// frame (2.3.1, 7.6).
	safeguards bool
	// deadman is the armed rigd dead-man for this connector, nil when none is pending.
	deadman *time.Timer
}

var (
	wsConnectorLivenessMu    sync.Mutex
	wsConnectorLivenessByKey = map[string]*wsConnectorLiveness{}
)

// wsNoteConnectorHello records what a hello advertised and cancels a pending dead-man: the
// connector is back, so the silence it was armed for did not happen. Every hello records, including
// a re-sent one, because a client may re-advertise its capabilities on any reconnect.
func wsNoteConnectorHello(userID, connectorID string, enabled []any) {
	safeguards := false
	for _, name := range enabled {
		if name == connectorCapabilitySafeguards {
			safeguards = true
		}
	}
	wsConnectorLivenessMu.Lock()
	defer wsConnectorLivenessMu.Unlock()
	key := wsConnectorKey(userID, connectorID)
	state := wsConnectorLivenessByKey[key]
	if state == nil {
		state = &wsConnectorLiveness{}
		wsConnectorLivenessByKey[key] = state
	}
	state.safeguards = safeguards
	if state.deadman != nil {
		state.deadman.Stop()
		state.deadman = nil
	}
}

// wsConnectorSafeguardsEnabled reports whether the server echoed `safeguards` for this connector.
// A safeguard frame from a connector that did not advertise it is a frame kind the server does not
// serve for it: `unknown_type`, and the socket stays open (2.3).
func wsConnectorSafeguardsEnabled(userID, connectorID string) bool {
	wsConnectorLivenessMu.Lock()
	defer wsConnectorLivenessMu.Unlock()
	state := wsConnectorLivenessByKey[wsConnectorKey(userID, connectorID)]
	return state != nil && state.safeguards
}

// wsConnectorSocketCount is how many sockets this connector currently holds open.
func wsConnectorSocketCount(userID, connectorID string) int {
	wsOpenConnectorsMu.Lock()
	defer wsOpenConnectorsMu.Unlock()
	return wsOpenConnectors[wsConnectorKey(userID, connectorID)]
}

// wsArmConnectorDeadman arms 7.3's dead-man when the LAST socket of a connector closes: a connector
// that advertised safeguards and stays offline past its heartbeat close has no observer left on its
// machine, so the server is the one that says so. A connector that advertised nothing is forgotten
// here rather than kept, because there is nothing to watch and no state to hold.
func wsArmConnectorDeadman(userID, connectorID string) {
	key := wsConnectorKey(userID, connectorID)
	wsConnectorLivenessMu.Lock()
	state := wsConnectorLivenessByKey[key]
	if state == nil || !state.safeguards {
		delete(wsConnectorLivenessByKey, key)
		wsConnectorLivenessMu.Unlock()
		return
	}
	wsConnectorLivenessMu.Unlock()

	fire := func() {
		if wsConnectorSocketCount(userID, connectorID) > 0 {
			// The connector came back inside the heartbeat close: the dead-man was for a silence
			// that did not last, so it says nothing.
			return
		}
		// The error is dropped because there is no caller left to tell: the connector is gone, and
		// that is the case this alert exists for. What the push path does keep is the notice itself -
		// an offline user's alerts wait in the notification store for their next connect.
		_ = raiseRigdDeadmanAlert(context.Background(), userID, connectorID)
	}
	timer := wsConnectorDeadmanAfter(wsConnectorIdleTimeout(), fire)

	wsConnectorLivenessMu.Lock()
	state.deadman = timer
	wsConnectorLivenessMu.Unlock()
}

// raiseRigSafeguardAlert publishes the alert for one stored safeguard row. 7.3 rules the channel:
// the existing routes.BroadcastDataChange with the NEW entity `rig_safeguard` under the NEW
// event_type `safeguard_alert`, which is also the path that keeps the notification for an offline
// user and replays it when they next connect.
//
// The payload names the frame's own fields - the row the alert is about - plus connector_id, which
// is the machine the row came from. 7.3 fixes the event_type and the entity and does not fix the
// payload's shape, so the fields are the ones the frame already carries rather than a second
// vocabulary invented for the push.
func raiseRigSafeguardAlert(ctx context.Context, userID, connectorID string, row rigdb.RigSafeguardORM) error {
	data := entities.NewOrderedMap[any]()
	data.Set("connector_id", connectorID)
	data.Set("rig", row.Rig)
	data.Set("safeguard", row.Safeguard)
	data.Set("state", row.State)
	if row.PID != nil {
		data.Set("pid", *row.PID)
	}
	data.Set("restarts", row.Restarts)
	data.Set("age_s", row.AgeS)
	return routes.BroadcastDataChange(ctx, safeguardAlertEventType, rigSafeguardEntity,
		wsRigSafeguardEntityID(connectorID, row.Rig, row.Safeguard), userID, data, nil)
}

// raiseRigdDeadmanAlert is 7.3's dead-man for rigd itself: a connector that advertised safeguards
// stayed offline past its heartbeat close. On a machine with no OS supervisor this is the only
// observer of a dead rigd. It names the machine and no rig, because the alert is about the
// connector's own socket - the one silence the server judges (7.4).
func raiseRigdDeadmanAlert(ctx context.Context, userID, connectorID string) error {
	data := entities.NewOrderedMap[any]()
	data.Set("connector_id", connectorID)
	data.Set("safeguard", rigdb.SafeguardRigd)
	return routes.BroadcastDataChange(ctx, safeguardAlertEventType, rigSafeguardEntity,
		wsRigSafeguardEntityID(connectorID, "", rigdb.SafeguardRigd), userID, data, nil)
}

// wsRigSafeguardEntityID names one row as the push frame's entity_id: the parts of the key that are
// known, in the key's order. The dead-man knows no rig, so it names the connector and `rigd`.
func wsRigSafeguardEntityID(connectorID, rig, safeguard string) string {
	parts := []string{}
	for _, part := range []string{connectorID, rig, safeguard} {
		if part != "" {
			parts = append(parts, part)
		}
	}
	return strings.Join(parts, "/")
}

// wsCursor renders a stored client cursor for an ack: the value, or null when the session has none.
// The null is a ruled answer rather than an absence - it tells the client to read its source from
// the beginning, bounded by its own backfill limit (2.2).
func wsCursor(cursor *string) any {
	if cursor == nil {
		return nil
	}
	return *cursor
}

// wsInt64 is wsInt's wider form for the safeguard frame's counters. A value that is not a number is
// 0 rather than an error, the same leniency wsInt applies to the frames that already exist.
func wsInt64(v any) int64 {
	switch x := v.(type) {
	case int:
		return int64(x)
	case int64:
		return x
	case float64:
		return int64(x)
	}
	return 0
}

// wsOptInt is an optional integer field: absent or non-numeric is nil, so a safeguard that is not
// running stores a null pid rather than claiming process 0.
func wsOptInt(v any) *int {
	switch x := v.(type) {
	case int:
		return &x
	case int64:
		i := int(x)
		return &i
	case float64:
		i := int(x)
		return &i
	}
	return nil
}

// wsOptUnixMillis is an optional timestamp in the client's unix milliseconds - the one time format
// the doc states for this socket (ping.t, 2.2). A frame that carried an unreadable `at` stores no
// beat rather than a fabricated one: last_beat_at is the child's own time or nothing at all.
func wsOptUnixMillis(v any) *time.Time {
	switch x := v.(type) {
	case int:
		t := time.UnixMilli(int64(x)).UTC()
		return &t
	case int64:
		t := time.UnixMilli(x).UTC()
		return &t
	case float64:
		t := time.UnixMilli(int64(x)).UTC()
		return &t
	}
	return nil
}
