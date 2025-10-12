# Animation System Issue Analysis and Fix

## Root Cause Identified

The animation system has **TWO COMPETING ANIMATION MECHANISMS**:

### 1. Direct Callback System (LazyTaskList)
- TaskRow registers animation callbacks with LazyTaskList
- LazyTaskList calls these callbacks directly for optimistic UI updates
- Used for: Create, Update, Delete operations triggered by user actions

### 2. WebSocket Event System (WebSocketAnimationService)
- WebSocketAnimationService dispatches CustomEvents
- TaskRow listens for these CustomEvents
- Used for: Cross-user animations and real-time updates

## The Problem

Both systems are trying to trigger animations for the same events, causing:
1. **Timing conflicts** - Animation can be triggered twice
2. **State conflicts** - Animation state can be overwritten
3. **Event interference** - Events may cancel each other out

## The Solution

**Consolidate animation systems** to use the WebSocket event system as the primary mechanism while maintaining the callback system for backward compatibility.

## Implementation Plan

1. **Prioritize WebSocket events** for all animations
2. **Use callback system as fallback** when WebSocket is unavailable
3. **Add coordination logic** to prevent double-triggering
4. **Enhance debugging** to track both systems

## Files to Modify

1. `TaskRow.tsx` - Add coordination logic
2. `LazyTaskList.tsx` - Modify to prefer WebSocket events
3. `WebSocketAnimationService.ts` - Enhance event dispatch
4. `debug-animation-system.js` - Update for dual-system testing