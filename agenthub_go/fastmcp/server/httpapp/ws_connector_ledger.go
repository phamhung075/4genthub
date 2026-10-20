// ws_connector_ledger.go holds P4's nudge: the ONE server frame `/ws/connector` gains, `ledger_tip`,
// and the per-user registry of the sockets entitled to receive it.
//
// IT IS A NUDGE AND NOTHING ELSE (NEXT_GEN P4; agent-boundaries.md 2.2, 2.3). Correctness has ONE
// path - the client's own GET /api/v2/ledger from its cursor - and the socket only shortens the delay
// between a commit and that pull. The frame carries a tip and no entries, so a client that treated it
// as truth would still have to pull to learn anything; nothing on this side reads it either, and a
// socket that was never sent it converges exactly as one that was.
//
// THE RULE IT OBEYS is 2.3.1: a frame kind is sent only to a socket whose hello advertised the
// capability the kind belongs to and whose ready echoed it. The registry below is written from the
// ECHOED list - the same value the ready frame carried - so no second place decides that gate.
package httpapp

import (
	"context"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// connectorLedgerTipFrame is P4's one frame name. Like every frame this socket already speaks it is
// a flat object whose `type` names the kind (2.2).
const connectorLedgerTipFrame = "ledger_tip"

// wsLedgerTipWriteTimeout bounds one nudge write. wsConn's only deadline is the READ deadline the
// connector loop refreshes (the heartbeat close, 2.2); a nudge is written from the request that
// committed the decision, and it must not be able to hold that request on a peer that stopped
// reading. A socket that cannot take the frame inside this window fails the write, which is dropped
// like every other error here: the socket is then closed by its own read loop or idle timeout, and
// the client's reconnect re-reads the ledger from its cursor.
var wsLedgerTipWriteTimeout = 2 * time.Second

// wsLedgerTipByUser holds the live sockets entitled to `ledger_tip`, per authenticated subject.
//
// The subject is the one the socket authenticated with (handleConnector's *result.UserID) and the one
// the ledger's writer adapter is handed on the request, so the two agree without either normalizing
// for the other.
var (
	wsLedgerTipMu     sync.Mutex
	wsLedgerTipByUser = map[string]map[*wsConn]struct{}{}
)

// wsLedgerTipEntitled reports whether a ready's echoed capability list carried the ledger name.
func wsLedgerTipEntitled(capabilities []any) bool {
	for _, name := range capabilities {
		if name == connectorCapabilityLedger {
			return true
		}
	}
	return false
}

// wsRegisterLedgerTipSocket records one socket as entitled when ready echoed `ledger`, and forgets it
// when a re-sent hello no longer asks for the capability: a connector may re-advertise on any
// reconnect, so the gate belongs to the LAST handshake (2.3.1).
func wsRegisterLedgerTipSocket(userID string, conn *wsConn, capabilities []any) {
	if userID == "" || conn == nil {
		return
	}
	wsLedgerTipMu.Lock()
	defer wsLedgerTipMu.Unlock()
	sockets := wsLedgerTipByUser[userID]
	if !wsLedgerTipEntitled(capabilities) {
		if sockets != nil {
			delete(sockets, conn)
			if len(sockets) == 0 {
				delete(wsLedgerTipByUser, userID)
			}
		}
		return
	}
	if sockets == nil {
		sockets = map[*wsConn]struct{}{}
		wsLedgerTipByUser[userID] = sockets
	}
	sockets[conn] = struct{}{}
}

// wsUnregisterLedgerTipSocket forgets one socket. It is idempotent, and every closing socket calls
// it whether or not its handshake entitled it.
func wsUnregisterLedgerTipSocket(userID string, conn *wsConn) {
	if userID == "" || conn == nil {
		return
	}
	wsLedgerTipMu.Lock()
	defer wsLedgerTipMu.Unlock()
	sockets := wsLedgerTipByUser[userID]
	if sockets == nil {
		return
	}
	delete(sockets, conn)
	if len(sockets) == 0 {
		delete(wsLedgerTipByUser, userID)
	}
}

// wsLedgerTipSockets copies out ONE user's entitled sockets, so the fan-out writes with the lock
// released: a write may take up to wsLedgerTipWriteTimeout, and a slow socket must neither delay a
// second connector of the same user nor block a close.
func wsLedgerTipSockets(userID string) []*wsConn {
	wsLedgerTipMu.Lock()
	defer wsLedgerTipMu.Unlock()
	sockets := wsLedgerTipByUser[userID]
	out := make([]*wsConn, 0, len(sockets))
	for conn := range sockets {
		out = append(out, conn)
	}
	return out
}

// wsLedgerTipFrame builds P4's frame: the kind and the tip, and nothing else.
func wsLedgerTipFrame(userSeq int64) *entities.OrderedMap[any] {
	frame := entities.NewOrderedMap[any]()
	frame.Set("type", connectorLedgerTipFrame)
	frame.Set("user_seq", userSeq)
	return frame
}

// wsNotifyLedgerTip sends the tip to every socket of this user that is entitled to it, and does
// nothing else. It is called AFTER the write that moved the tip has committed, never inside that
// write's transaction: a nudge that arrived before the row was durable would send a client to read a
// ledger that does not have it yet.
//
// userSeq is the highest user_seq the commit took; a concurrent commit for the same user can leave the
// real tip higher, which costs the delayed client nothing - it pulls from its OWN cursor, so the frame
// is a reason to pull rather than a cursor of its own.
func wsNotifyLedgerTip(userID string, userSeq int64) {
	if userID == "" {
		return
	}
	for _, conn := range wsLedgerTipSockets(userID) {
		_ = wsSendWithin(context.Background(), conn, wsLedgerTipFrame(userSeq), wsLedgerTipWriteTimeout)
	}
}
