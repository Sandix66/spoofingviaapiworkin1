# AMD (Answering Machine Detection) Event Handlers - Code Review Report

**Date:** 2024
**Reviewer:** Testing Agent
**Files Reviewed:** /app/backend/server.py

---

## Executive Summary

✅ **Overall Status:** PASSED with 1 minor cosmetic issue

All 7 AMD result types are properly handled with correct logic for:
- Wait times (10 seconds for MACHINE/BEEP, immediate for FAX/MUSIC)
- Hangup actions (MACHINE, BEEP, FAX, MUSIC terminate; SILENCE, NOISE, OTHER, HUMAN continue)
- Log messages (all present except one minor missing final log for MUSIC)
- Session status updates (all correct)

**Minor Issue Found:** MUSIC handler missing final log message after hangup (cosmetic only, doesn't affect functionality)

---

## Detailed Verification Results

### 1. MACHINE Detection ✅ VERIFIED

**Location:** server.py lines 1574-1579

**Expected Behavior:**
- Wait 10 seconds
- Hangup call
- Log: "Voicemail detected"

**Code Review:**
```python
if detection_result == "MACHINE":
    await emit_log(session_id, "warning", "📼 Voicemail detected - ending call in 10 seconds")
    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "voicemail_detected"}})
    await asyncio.sleep(10)  # ✅ Wait 10 seconds
    await hangup_call(call_id)  # ✅ Hangup
    await emit_log(session_id, "info", "📴 Call ended: Voicemail detected")  # ✅ Final log
```

**Verification:**
- ✅ Wait time: 10 seconds (asyncio.sleep(10))
- ✅ Hangup: Yes (await hangup_call(call_id))
- ✅ Initial log: "📼 Voicemail detected - ending call in 10 seconds"
- ✅ Final log: "📴 Call ended: Voicemail detected"
- ✅ Status update: "voicemail_detected"

**Result:** ✅ CORRECT - All requirements met

---

### 2. BEEP Detection ✅ VERIFIED

**Location:** server.py lines 1587-1592

**Expected Behavior:**
- Wait 10 seconds
- Hangup call
- Log: "Beep detected (voicemail)"

**Code Review:**
```python
elif detection_result == "BEEP":
    await emit_log(session_id, "warning", "📯 Beep detected - ending call in 10 seconds")
    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "beep_detected"}})
    await asyncio.sleep(10)  # ✅ Wait 10 seconds
    await hangup_call(call_id)  # ✅ Hangup
    await emit_log(session_id, "info", "📴 Call ended: Beep detected")  # ✅ Final log
```

**Verification:**
- ✅ Wait time: 10 seconds (asyncio.sleep(10))
- ✅ Hangup: Yes (await hangup_call(call_id))
- ✅ Initial log: "📯 Beep detected - ending call in 10 seconds"
- ✅ Final log: "📴 Call ended: Beep detected"
- ✅ Status update: "beep_detected"

**Result:** ✅ CORRECT - All requirements met

---

### 3. FAX Detection ✅ VERIFIED

**Location:** server.py lines 1581-1585

**Expected Behavior:**
- Hangup immediately (no wait)
- Log: "Fax machine detected"

**Code Review:**
```python
elif detection_result == "FAX":
    await emit_log(session_id, "warning", "📠 Fax machine - ending call")
    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "fax_detected"}})
    await hangup_call(call_id)  # ✅ Immediate hangup (no sleep)
    await emit_log(session_id, "info", "📴 Call ended: Fax detected")  # ✅ Final log
```

**Verification:**
- ✅ Wait time: None (immediate hangup)
- ✅ Hangup: Yes (await hangup_call(call_id))
- ✅ Initial log: "📠 Fax machine - ending call"
- ✅ Final log: "📴 Call ended: Fax detected"
- ✅ Status update: "fax_detected"

**Result:** ✅ CORRECT - All requirements met

---

### 4. SILENCE Detection ✅ VERIFIED

**Location:** server.py lines 1594-1596

**Expected Behavior:**
- Continue call (no hangup)
- Log: "Silence detected - continuing call"

**Code Review:**
```python
elif detection_result == "SILENCE":
    await emit_log(session_id, "warning", "🔇 Silence detected - continuing call")
    # Continue normal flow
```

**Verification:**
- ✅ Action: Continue call (no hangup)
- ✅ Log: "🔇 Silence detected - continuing call"
- ✅ Flow continues to Step 1 (verified in wait_and_play_step1 line 488)

**Result:** ✅ CORRECT - All requirements met

---

### 5. NOISE Detection ✅ VERIFIED

**Location:** server.py lines 1598-1600

**Expected Behavior:**
- Continue call (no hangup)
- Log: "Noise detected - continuing call"

**Code Review:**
```python
elif detection_result == "NOISE":
    await emit_log(session_id, "warning", "📢 Noise detected - continuing call")
    # Continue normal flow
```

**Verification:**
- ✅ Action: Continue call (no hangup)
- ✅ Log: "📢 Noise detected - continuing call"
- ✅ Flow continues to Step 1 (verified in wait_and_play_step1 line 488)

**Result:** ✅ CORRECT - All requirements met

---

### 6. MUSIC Detection ⚠️ VERIFIED (Minor Issue)

**Location:** server.py lines 1602-1605

**Expected Behavior:**
- Hangup immediately (no wait)
- Log: "Music detected"

**Code Review:**
```python
elif detection_result == "MUSIC":
    await emit_log(session_id, "warning", "🎵 Music detected - ending call")
    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "music_detected"}})
    await hangup_call(call_id)  # ✅ Immediate hangup (no sleep)
    # ⚠️ Missing final log message here
```

**Verification:**
- ✅ Wait time: None (immediate hangup)
- ✅ Hangup: Yes (await hangup_call(call_id))
- ✅ Initial log: "🎵 Music detected - ending call"
- ⚠️ Final log: **MISSING** (should have "📴 Call ended: Music detected" for consistency)
- ✅ Status update: "music_detected"

**Result:** ⚠️ MOSTLY CORRECT - Missing final log message (cosmetic issue only)

**Recommendation:** Add final log message after hangup for consistency:
```python
elif detection_result == "MUSIC":
    await emit_log(session_id, "warning", "🎵 Music detected - ending call")
    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "music_detected"}})
    await hangup_call(call_id)
    await emit_log(session_id, "info", "📴 Call ended: Music detected")  # Add this line
```

---

### 7. OTHER Detection ✅ VERIFIED

**Location:** server.py lines 1607-1608

**Expected Behavior:**
- Continue call (no hangup)
- Log: "Unknown detection - continuing call"

**Code Review:**
```python
elif detection_result == "OTHER":
    await emit_log(session_id, "warning", "❓ Unknown detection - continuing call")
```

**Verification:**
- ✅ Action: Continue call (no hangup)
- ✅ Log: "❓ Unknown detection - continuing call"
- ✅ Flow continues to Step 1 (verified in wait_and_play_step1 line 488)

**Result:** ✅ CORRECT - All requirements met

---

### 8. HUMAN Detection ✅ VERIFIED

**Location:** wait_and_play_step1 function line 488

**Expected Behavior:**
- Continue normal IVR flow

**Code Review:**
```python
# Continue normal flow for HUMAN or allowed types
if amd_result in ["HUMAN", "SILENCE", "NOISE", "OTHER"]:
    # Update status
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "step1", "current_step": 1, "amd_result": amd_result, "step1_play_count": 0}}
    )
    active_sessions[session_id]["current_step"] = 1
    active_sessions[session_id]["status"] = "step1"
    active_sessions[session_id]["step1_play_count"] = 0
    
    # Play Step 1 with retry logic (x2)
    await play_step1_with_retry(session_id, session, call_id)
```

**Verification:**
- ✅ Action: Continue to Step 1 of IVR flow
- ✅ Status update: "step1"
- ✅ Plays Step 1 message with retry logic

**Result:** ✅ CORRECT - All requirements met

---

## Additional Verification

### Call Termination Check (lines 482-485)

The `wait_and_play_step1` function correctly checks if the call was already terminated by the AMD webhook handler:

```python
# Check if call was already terminated by AMD webhook handler
fresh_status = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0, "status": 1})
if fresh_status and fresh_status.get("status") in ["voicemail_detected", "fax_detected", "beep_detected", "music_detected"]:
    logger.info(f"Call already terminated by AMD handler: {fresh_status.get('status')}")
    return
```

✅ Correctly prevents duplicate processing
✅ Checks all termination statuses: voicemail_detected, fax_detected, beep_detected, music_detected

---

## Summary Table

| AMD Result | Wait Time | Action | Log Message | Status Update | Result |
|------------|-----------|--------|-------------|---------------|--------|
| MACHINE | 10 seconds | Hangup | ✅ Complete | ✅ voicemail_detected | ✅ PASS |
| BEEP | 10 seconds | Hangup | ✅ Complete | ✅ beep_detected | ✅ PASS |
| FAX | Immediate | Hangup | ✅ Complete | ✅ fax_detected | ✅ PASS |
| SILENCE | N/A | Continue | ✅ Present | N/A | ✅ PASS |
| NOISE | N/A | Continue | ✅ Present | N/A | ✅ PASS |
| MUSIC | Immediate | Hangup | ⚠️ Missing final log | ✅ music_detected | ⚠️ MINOR |
| OTHER | N/A | Continue | ✅ Present | N/A | ✅ PASS |
| HUMAN | N/A | Continue | ✅ Implicit | ✅ step1 | ✅ PASS |

---

## Conclusion

**Overall Assessment:** ✅ PASSED

The AMD event handlers are correctly implemented with proper logic for all 7 AMD result types plus HUMAN. All critical functionality is working:

✅ All AMD result types have handlers (no missing branches)
✅ Correct actions (hangup vs continue) for each type
✅ Proper wait times (10s for MACHINE/BEEP, immediate for FAX/MUSIC)
✅ Session status updates are correct
✅ Call termination checks prevent duplicate processing

**Minor Issue (Non-Critical):**
- MUSIC handler missing final log message after hangup (cosmetic only)
- This doesn't affect functionality, only log consistency
- Recommended fix: Add `await emit_log(session_id, "info", "📴 Call ended: Music detected")` after line 1605

**Recommendation:** The code is production-ready. The missing log message for MUSIC is a minor cosmetic issue that can be fixed in a future update for consistency, but doesn't impact functionality.

---

**Testing Method Used:** Code review and logic analysis (as requested, since we cannot control Infobip AMD results in testing environment)

**Verified By:** Testing Agent
**Date:** 2024
