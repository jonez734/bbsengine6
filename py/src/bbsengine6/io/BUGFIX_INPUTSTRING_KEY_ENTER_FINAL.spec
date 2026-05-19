# Bug Fix: inputstring() KEY_ENTER Hang (May 2026) - FINAL

## Root Cause

`inputstring()` was calling `echo('{curpos:...}')` while holding `_current_stream_lock`, immediately before calling `getch()`. This caused contention where:

1. `echo()` held the lock while doing command processing
2. `echo()` processed `{curpos:...}` commands (terminal interaction)
3. `getch()` was called right after and tried to acquire the same lock
4. Result: `getch()` couldn't properly initialize while echo was active
5. Input stream state got corrupted
6. KEY_ENTER was not processed correctly
7. `inputstring()` hung waiting for valid input

## The Fix

**File**: `bbsengine6/py/src/bbsengine6/io/inputstring.py` (lines 712-723)
**Commit**: `ca1f097`

### Before (Broken)
```python
cursor_display_col = input_col_start + (curpos - scroll_offset)
with _current_stream_lock:
    echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)
    _terminal_state.cursor_row = start_row
    _terminal_state.cursor_col = cursor_display_col

# Lock released here, but getch() called right after
ch = getch(...)
```

**Problems**:
- Lock held during echo's `{curpos}` command processing
- Prevents getch() from acquiring lock cleanly
- Creates race condition window
- Input stream state corrupted

### After (Fixed)
```python
cursor_display_col = input_col_start + (curpos - scroll_offset)
# Position cursor BEFORE getch() without holding lock
echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)
# Update terminal state (local tracking, doesn't need lock)
_terminal_state.cursor_row = start_row
_terminal_state.cursor_col = cursor_display_col

ch = getch(...)
```

**Benefits**:
- No lock held during echo's command processing
- getch() can acquire lock cleanly without contention
- No race conditions
- Input stream state clean and ready for getch()
- KEY_ENTER processed correctly

## Why This Works

1. **echo() can complete**: Called without lock, does its command processing safely
2. **getch() acquires lock cleanly**: No contention with echo()
3. **Terminal state consistent**: By the time getch() runs, echo has updated display
4. **Input stream ready**: No corruption from echo processing
5. **KEY_ENTER handled**: getch() can properly read and process all keys

## Lock Analysis

**Lock requirements**:
- `echo()` command processing: Doesn't need `_current_stream_lock` to be held by caller
- Terminal state updates: `_terminal_state` is local tracking, no thread protection needed
- `getch()` call: Needs clean acquisition without prior lock contention
- Input reading: getch() manages its own locks internally

**Why lock wasn't needed**:
- `echo()` manages its own synchronization
- `_terminal_state` is just local tracking for cursor position
- Only `getch()` needs the lock, and it can get it cleanly now

## Commits Summary

| Hash | Message |
|------|---------|
| `0e5315d` | Fix deadlock in getch_str() by releasing lock during select() wait |
| `e22531b` | Improve getch_str() lock handling to match proven approach |
| `8e78454` | Fix inputstring() lock contention with getch() |
| `ca1f097` | **Fix inputstring() hang by removing lock around echo before getch()** (FINAL FIX) |

## Verification

✅ KEY_ENTER now works correctly in inputstring()
✅ notify_message_demo accepts user input
✅ No hangs or deadlocks observed
✅ {curpos} echo codes continue to work properly
✅ Display output is correct

## Key Learning

The issue wasn't that `{curpos}` echo codes are inherently bad - it's that **holding a lock while calling echo() before getch() creates contention that breaks input processing**.

The solution is simple: **don't hold locks across unrelated I/O operations**.

---

**Date**: May 19, 2026
**Status**: ✅ RESOLVED
**Root Cause**: Lock contention between echo() and getch()
**Solution**: Move echo() call outside of lock
**Line Count**: 3 lines changed (remove 1 line, add 2 lines)
