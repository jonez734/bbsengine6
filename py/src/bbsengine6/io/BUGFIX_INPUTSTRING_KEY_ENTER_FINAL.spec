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

### Echo Command Handlers and Lock Requirements

**File**: `bbsengine6/py/src/bbsengine6/io/echo.py`

#### Handlers that NEED `_current_stream_lock` (4 total)
These handlers read and/or modify shared terminal state affecting output behavior:

1. **`_handle_word()` (lines 333-388)** ✅
   - Reads: cursor position, wordwrap flag, indent
   - Modifies: cursor_col, _first_line_after_f6
   - Reason: Word wrapping logic depends on current cursor position
   - Lock: Line 357 (correct)

2. **`_handle_acs()` (lines 541-570)** ✅
   - Modifies: `_terminal_state.cursor_col` (line 560)
   - Reason: ACS characters affect cursor position
   - Lock: Line 559 (correct)

3. **`_acs_on()` / `_acs_off()` (lines 513-538)** ✅
   - Modifies: `_terminal_state.acs` flag (lines 520, 534)
   - Reason: ACS state affects subsequent output rendering
   - Lock: Lines 518, 532 (correct)

4. **`echo()` function - end-of-line handling (lines 1256-1258)** ✅
   - Modifies: `_terminal_state.cursor_col`, `_terminal_state.cursor_row`
   - Reason: Tracks cursor after output
   - Lock: Line 1256 (correct)

5. **`echo_iter()` - whitespace handling (lines 1177-1178)** ✅
   - Modifies: `_terminal_state.cursor_col`
   - Reason: Updates cursor position for whitespace
   - Lock: Line 1177 (correct)

#### Handlers that DON'T need `_current_stream_lock` (REMOVED)
These handlers only set cursor position without reading current state or affecting output behavior:

1. **`_handle_curpos()` (lines 598-618)** ❌ REMOVED
   - Only sets: `_terminal_state.cursor_row`, `_terminal_state.cursor_col`
   - Doesn't read existing state or affect output behavior
   - Reason: Just local tracking, no cross-thread coordination needed
   - Old lock: Lines 613-615 (unnecessary)

2. **`_handle_f6()` (lines 621-650)** ❌ REMOVED
   - Only sets: `_terminal_state.cursor_col` (lines 645, 648)
   - Doesn't depend on current state values
   - Reason: Just sets position, doesn't read or compute based on existing state
   - Old lock: Lines 644-648 (unnecessary)

#### Other handlers (no locks needed)
These just generate escape sequences without modifying terminal state:

- `_handle_decstbm()` - Set scrolling region
- `_handle_reset()` - Reset terminal
- `_handle_home()` - Cursor home
- `_handle_ed()` - Erase display
- `_handle_elo()` - Erase to end of line
- `_handle_cuu()`, `_handle_cud()`, `_handle_cuf()`, `_handle_cub()` - Cursor movement
- `_handle_cha()` - Cursor horizontal absolute
- And others that just emit ANSI codes

Different locks used for other purposes:
- `_handle_decsc()` / `_handle_decrc()` - use `_terminal_state_lock` + `_terminal_state_stack_lock` (correct for stack operations)
- `_handle_indent()` - uses `_terminal_state_lock` (correct for setting indent)

### The Distinction

**NEED lock**: Handlers that **read current state OR modify state affecting subsequent output behavior**
- Example: `_handle_word()` reads cursor_col to decide if word wraps
- Example: `_handle_acs()` modifies cursor_col which affects next word positioning

**DON'T need lock**: Handlers that **only set cursor position without reading/computing based on current state**
- Example: `_handle_curpos()` just overwrites cursor position unconditionally
- Example: `_handle_f6()` just sets indent position without reading anything

### Why Lock Wasn't Needed in inputstring()

- `echo()` manages its own synchronization internally
- `_terminal_state` is just local tracking for cursor position
- Holding the lock across echo() → getch() creates contention
- `getch()` needs clean lock acquisition without prior contention
- Solution: Move echo() outside the lock, let both functions manage locks independently

## Commits Summary

| Hash | Message |
|------|---------|
| `0e5315d` | Fix deadlock in getch_str() by releasing lock during select() wait |
| `e22531b` | Improve getch_str() lock handling to match proven approach |
| `8e78454` | Fix inputstring() lock contention with getch() |
| `ca1f097` | Fix inputstring() hang by removing lock around echo before getch() |
| `2ed1362` | **Fix inputstring KEY_ENTER hang: remove unnecessary lock from echo command handlers** (FINAL FIX) |

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
