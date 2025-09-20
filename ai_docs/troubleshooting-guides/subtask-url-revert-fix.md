# Fix: Subtask URL Immediately Reverting When Opening Detail Dialog

## Problem Description

When users clicked on a subtask detail button, the following sequence occurred:
1. Dialog would start to open
2. URL would change to include subtask ID: `.../task/{taskId}/subtask/{subtaskId}`
3. URL would immediately revert back to: `.../task/{taskId}`
4. This caused subtask to not be found and triggered 404 errors

## Root Cause Analysis

The issue was a race condition in the `LazySubtaskList.tsx` component:

1. **Detail button click** → `handleViewDetails()` → `navigate()` with subtask URL
2. **URL parameter changes** → `useEffect` monitoring `subtaskId` triggers
3. **Dialog opens** → `setDetailsDialog({ open: true, subtask })`
4. **SubtaskDetailsDialog renders** → `onOpenChange(false)` triggered immediately
5. **Race condition** → `handleSubtaskDialogClose()` called → URL reverts

The problem was in the `onOpenChange` handler (lines 851-855) which called `handleSubtaskDialogClose()` immediately when the dialog's `open` prop became `false` for ANY reason, including internal component state changes during initialization.

## Solution Implemented

Added a state flag `isOpeningDialog` to track when the dialog is being programmatically opened:

### 1. Added State Variable
```typescript
// Track when we're programmatically opening a dialog to prevent race conditions
const [isOpeningDialog, setIsOpeningDialog] = useState(false);
```

### 2. Modified onOpenChange Handler
```typescript
onOpenChange={(open) => {
  if (!open && !isOpeningDialog) {
    // Only handle close events when we're not in the process of opening
    // This prevents race conditions during dialog initialization
    handleSubtaskDialogClose();
  }
}}
```

### 3. Updated URL Effect Hook
Set the flag when opening dialog from URL parameters:
```typescript
setIsOpeningDialog(true);
loadFullSubtask(subtaskId).then(subtask => {
  if (subtask) {
    setDetailsDialog({ open: true, subtask });
    // Clear the opening flag after dialog stabilizes
    setTimeout(() => setIsOpeningDialog(false), 200);
  }
  // ... error handling also clears flag
});
```

### 4. Updated Action Handler
Set the flag when opening dialog from action buttons:
```typescript
// Set opening flag for details dialog to prevent race conditions
if (action === 'details') {
  setIsOpeningDialog(true);
}
// ... dialog opening logic
// Clear flag after stabilization
setTimeout(() => setIsOpeningDialog(false), 200);
```

## Files Modified

- `/home/daihungpham/__projects__/4genthub/agenthub-frontend/src/components/LazySubtaskList.tsx`
  - Added `isOpeningDialog` state variable
  - Modified `onOpenChange` handler (lines ~865-870)
  - Updated useEffect for URL monitoring (lines ~424-442, ~449-466)
  - Updated `handleSubtaskAction` function (lines ~555-603)

## Testing Verification

- ✅ TypeScript compilation passes (`npm run build`)
- ✅ No syntax errors or type issues
- ✅ Build completes successfully

## Expected Behavior After Fix

1. User clicks subtask detail button
2. URL changes to include subtask ID and stays there
3. Dialog opens properly without URL reversion
4. User can interact with dialog normally
5. Only when user actually closes dialog does URL revert back

## Prevention Strategy

The `isOpeningDialog` flag provides a 200ms grace period during which `onOpenChange(false)` events are ignored. This prevents race conditions during dialog initialization while still allowing proper closing behavior when the user actually wants to close the dialog.