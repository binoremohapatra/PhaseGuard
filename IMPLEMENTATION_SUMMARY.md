# Real In-Call Audio Capture Implementation Summary

## Date: 2025

## Overview

Real in-call audio capture has been successfully implemented for PhaseGuard using native Android AudioRecord with speakerphone detection. This allows capturing both sides of a phone call (user + scammer) when speakerphone is enabled, with real-time streaming to the backend AI for scam detection.

## What Was Implemented

### 1. Native Android Module - AudioCaptureModule.kt

**Location:** `apps/flutter/android/app/src/main/kotlin/com/phaseguard/phaseguard/AudioCaptureModule.kt`

**Features:**
- AudioRecord with MIC/VOICE_RECOGNITION sources
- 16kHz, mono, 16-bit PCM audio capture
- 50ms audio chunks via EventChannel
- Speakerphone state detection via AudioManager
- Audio amplitude monitoring (RMS calculation)
- Permission checking for RECORD_AUDIO
- Platform channel communication with Flutter

**Key Methods:**
- `checkPermission()` - Check RECORD_AUDIO permission
- `isSpeakerphoneOn()` - Check speakerphone state
- `startCapture(source)` - Start audio capture with specified source
- `stopCapture()` - Stop audio capture
- `getAudioStats()` - Get audio statistics for debugging

### 2. Flutter Service - audio_streaming.dart

**Location:** `apps/flutter/lib/services/audio_streaming.dart`

**Features:**
- Native AudioCaptureModule integration
- Real-time audio streaming to backend
- Speakerphone state monitoring (every 2 seconds)
- Audio source switching (MIC ↔ VOICE_RECOGNITION)
- Permission handling
- Forwarding audio chunks to RealtimeScamDetection

**Key Methods:**
- `checkPermission()` - Check RECORD_AUDIO permission
- `checkSpeakerphone()` - Check speakerphone state
- `startCapture(source)` - Start audio capture
- `stopCapture()` - Stop audio capture
- `switchAudioSource(source)` - Switch between MIC and VOICE_RECOGNITION
- `getAudioStats()` - Get audio statistics

### 3. Demo UI - scam_detection_demo.dart

**Location:** `apps/flutter/lib/screens/scam_detection_demo.dart`

**Features:**
- Permission request UI (RECORD_AUDIO)
- Speakerphone status display
- Audio amplitude monitoring
- Real-time transcript display
- Scam alert dialogs
- Audio source switching controls
- Backend connection management

**UI Components:**
- Permission status card
- Speakerphone status indicator
- Status display (recording, analyzing, scam detected)
- Recording controls (start/stop)
- Audio source switcher
- Live transcript display
- Scam alert popup

### 4. Platform Channel Registration - MainActivity.kt

**Location:** `apps/flutter/android/app/src/main/kotlin/com/phaseguard/phaseguard/MainActivity.kt`

**Changes:**
- Registered AudioCaptureModule
- Created MethodChannel for commands
- Created EventChannel for audio data
- Disabled out-of-scope modules (Shizuku, RecordingPriorityManager, etc.)

**Channels:**
- `phaseguard/audio_capture` - MethodChannel for commands
- `phaseguard/audio_capture_events` - EventChannel for audio data

### 5. Dependencies - pubspec.yaml

**Location:** `apps/flutter/pubspec.yaml`

**Changes:**
- Added `permission_handler: ^11.0.0` for runtime permissions

### 6. Disabled Out-of-Scope Modules

The following modules were disabled as they are out of scope for the current implementation:
- RecorderService.kt → RecorderService.kt.disabled
- RecordingPriorityManager.kt → RecordingPriorityManager.kt.disabled
- ShizukuAudioCapture.kt → ShizukuAudioCapture.kt.disabled
- ShizukuUserServiceManager.kt → ShizukuUserServiceManager.kt.disabled
- WrappedShellContext.kt → WrappedShellContext.kt.disabled
- IRecorderService.aidl → IRecorderService.aidl.disabled
- AudioRecorderJob.kt → AudioRecorderJob.kt.disabled
- HiddenApiBootstrap.kt → HiddenApiBootstrap.kt.disabled
- ServiceContext.kt → ServiceContext.kt.disabled

## Build Status

### Flutter Build
- **Status:** ✅ SUCCESS
- **Command:** `flutter build apk --debug`
- **Output:** `build/app/outputs/flutter-apk/app-debug.apk`
- **Errors:** 0
- **Warnings:** 16 (print statements, unused imports - non-blocking)

### Flutter Analyze
- **Status:** ✅ PASSED (with warnings)
- **Errors:** 0
- **Warnings:** 16 (non-blocking)
  - avoid_print statements (for debugging)
  - unused import in calls_screen.dart
  - prefer_initializing_formals (code style)

## Technical Architecture

### Audio Flow

```
Phone Call (Regular Phone)
    ↓
User Enables Speakerphone (Dialer)
    ↓
AudioCaptureModule detects speakerphone state
    ↓
AudioRecord starts (MIC or VOICE_RECOGNITION)
    ↓
Room audio captured (both sides via speaker)
    ↓
50ms chunks sent via EventChannel
    ↓
Flutter receives audio chunks
    ↓
RealtimeScamDetection streams to backend WebSocket
    ↓
Backend AI analyzes (STT + LLM + Fact-checking)
    ↓
Scam alert returned to app
```

### Audio Parameters
- **Sample Rate:** 16000 Hz
- **Channels:** Mono
- **Format:** 16-bit PCM (PCM16LE)
- **Chunk Size:** 50ms (configurable)
- **Sources:** MIC (primary), VOICE_RECOGNITION (fallback)

### Platform Channels
- **MethodChannel:** `phaseguard/audio_capture`
  - `checkPermission` - Check RECORD_AUDIO permission
  - `isSpeakerphoneOn` - Check speakerphone state
  - `startCapture` - Start audio capture
  - `stopCapture` - Stop audio capture
  - `getAudioStats` - Get audio statistics

- **EventChannel:** `phaseguard/audio_capture_events`
  - Audio data chunks (ByteArray)
  - Speakerphone state changes (Map)

## Testing Status

### Code Review
- ✅ Native module compiles
- ✅ Flutter code compiles
- ✅ Platform channels registered correctly
- ✅ Permissions declared in AndroidManifest.xml
- ✅ Build generates APK successfully

### Device Testing
- ⏳ **PENDING** - Requires real Android device
- ⏳ **PENDING** - Requires real phone call
- ⏳ **PENDING** - Requires Logcat analysis
- ⏳ **PENDING** - Requires backend verification

## How to Test

### Prerequisites
1. Backend running on `http://localhost:8000`
2. Real Android device (not emulator)
3. Android 10+ (API 29+)
4. Second phone for test call

### Step-by-Step Testing

#### Step 1: Install APK
```bash
cd apps/flutter
flutter build apk --debug
# Install build/app/outputs/flutter-apk/app-debug.apk on device
```

#### Step 2: Grant Permissions
1. Open PhaseGuard app
2. Navigate to "Scam Detection Demo"
3. Tap "Grant" for RECORD_AUDIO permission
4. Confirm permission in system dialog

#### Step 3: Initialize Backend
1. Tap "Initialize Backend Connection"
2. Verify status shows "Connected to backend"
3. Note the Call ID displayed

#### Step 4: Make Test Call
1. Use second phone to call the test device
2. Answer the call normally (don't enable speakerphone yet)
3. Go back to PhaseGuard app
4. Note: Speakerphone status should show "Disabled"

#### Step 5: Enable Speakerphone
1. Tap "Start Recording" in PhaseGuard
2. App shows "Enable Speakerphone" prompt
3. In phone dialer, tap speakerphone icon
4. Wait 2 seconds
5. Tap "Continue" in PhaseGuard

#### Step 6: Monitor Capture
1. Status should show "Recording & Analyzing..."
2. Speakerphone status should show "Enabled"
3. Audio amplitude should show non-zero value (e.g., 500-5000)
4. Transcript should appear as you speak

#### Step 7: Test Scam Detection
1. Speak scam phrases: "Congratulations, you have won a lottery"
2. Wait 2-3 seconds
3. Scam alert should appear: "SCAM DETECTED!"
4. Transcript should show what you said

#### Step 8: Stop Recording
1. Tap "Stop Recording"
2. Status shows "Recording stopped"
3. End the call

#### Step 9: Test Audio Source Switching
1. Make another call
2. Start recording with MIC source
3. Monitor audio amplitude
4. Stop recording
5. Tap "Switch" to change to VOICE_RECOGNITION
6. Start recording again
7. Compare audio amplitude
8. Use whichever gives better results

## Expected Results

### Successful Test Indicators

#### Audio Capture Working
- ✅ **Audio Amplitude:** Non-zero value (500-5000+)
- ✅ **Transcript:** Real-time text matching what you say
- ✅ **Scam Detection:** Alerts trigger on scam phrases
- ✅ **Speakerphone Detection:** Accurate on/off state

#### Logcat Output
```
I/AudioCaptureModule: Audio capture started with source: 1
I/AudioCaptureModule: Audio level: avg=1234.5, bytes=800
I/AudioCaptureModule: Speakerphone state changed: true
```

#### Backend Transcript
```
Real-time transcript should show:
"Congratulations you have won a lottery"
Instead of placeholder text
```

#### Scam Alert
```
Status: SCAM DETECTED!
Alert: "Potential scam detected: lottery prize scam"
```

### Failure Indicators

#### Audio Capture Failed
- ❌ **Audio Amplitude:** 0.0 or very low (< 10)
- ❌ **Transcript:** Empty or silence
- ❌ **Logcat:** "AudioRecord initialization failed"

#### Speakerphone Detection Issues
- ❌ **Speakerphone Status:** Always shows "Disabled"
- ❌ **Prompt Keeps Appearing:** Even after enabling speakerphone

#### Permission Issues
- ❌ **Permission Denied:** RECORD_AUDIO not granted
- ❌ **Grant Button:** Doesn't trigger system dialog

## Troubleshooting

### Issue: Audio Amplitude is 0
**Cause:** AudioRecord not capturing real audio

**Solutions:**
1. Verify speakerphone is actually enabled in dialer
2. Check RECORD_AUDIO permission is granted
3. Try switching audio source (MIC ↔ VOICE_RECRITIOGNITION)
4. Check Logcat for "AudioRecord initialization failed"

### Issue: Transcript is empty
**Cause:** Backend not receiving audio or STT failing

**Solutions:**
1. Check WebSocket connection status
2. Verify backend is running on `localhost:8000`
3. Check backend logs for audio data receipt
4. Verify Groq API key is configured

### Issue: Speakerphone detection not working
**Cause:** AudioManager API not working on some devices

**Solutions:**
1. Check Logcat for "Speakerphone state: false"
2. Manually enable speakerphone before starting capture
3. Proceed with recording even if detection fails

### Issue: Permission denied
**Cause:** User denied RECORD_AUDIO permission

**Solutions:**
1. Go to Settings → Apps → PhaseGuard → Permissions
2. Grant Microphone permission manually
3. Restart app and try again

## Device-Specific Quirks

### Samsung Devices
- **Issue:** MIC source may have heavy noise cancellation
- **Solution:** Try VOICE_RECOGNITION source instead
- **Test:** Switch audio source and compare amplitude

### Pixel Devices
- **Issue:** Some Pixel devices block audio capture
- **Solution:** VOICE_RECOGNITION may work better
- **Test:** Try both sources

### Xiaomi/Redmi
- **Issue:** MIUI may restrict audio capture
- **Solution:** Ensure MIUI optimization disabled for PhaseGuard
- **Test:** Check battery optimization settings

## Honest Limitations

### What This Approach CANNOT Do
- ❌ Capture caller audio WITHOUT speakerphone (physical limitation)
- ❌ Work on devices where speakerphone is broken
- ❌ Capture VoIP calls (WhatsApp, Telegram) - only regular phone calls
- ❌ Bypass Android audio restrictions (no root, no Shizuku)

### What This Approach DOES Do
- ✅ Capture both sides WITH speakerphone enabled
- ✅ Real-time streaming to backend AI
- ✅ Live transcription display
- ✅ Instant scam detection alerts
- ✅ Works on stock Android (no modifications)

## Next Steps

### Immediate (Before Hackathon Demo)
1. Install APK on real Android device
2. Grant RECORD_AUDIO permission
3. Initialize backend connection
4. Make/receive real phone call
5. Enable speakerphone
6. Start recording
7. Speak (transcript appears)
8. Speak scam phrase (alert appears)
9. Verify in Logcat: audio amplitude > 0

### Short Term (After Hackathon)
1. Optimize audio source selection per device
2. Add audio quality indicators
3. Improve speakerphone detection reliability
4. Add fallback to accessibility service if AudioRecord fails
5. Test on multiple device brands

### Long Term
1. Implement OEM built-in recorder detection
2. Add hardware device recommendation
3. Explore device-specific workarounds
4. Partner with VoIP providers for VoIP call support
5. Optimize backend for better accuracy

## Conclusion

### Implementation Status
✅ **Code Implementation:** COMPLETE  
✅ **Flutter Build:** SUCCESSFUL  
⏳ **Device Testing:** PENDING  
⏳ **Real Call Verification:** PENDING  

### What Was Delivered
1. Native Android AudioCaptureModule for in-call audio capture
2. Flutter AudioStreaming service for platform integration
3. Demo UI with speakerphone detection and scam alerts
4. Real-time streaming to backend AI
5. Successful APK build

### What Needs Testing
1. Real Android device testing
2. Real phone call testing
3. Audio quality verification
4. Scam detection accuracy
5. Device-specific behavior

### Files Modified
- `apps/flutter/android/app/src/main/kotlin/com/phaseguard/phaseguard/AudioCaptureModule.kt` (created)
- `apps/flutter/android/app/src/main/kotlin/com/phaseguard/phaseguard/MainActivity.kt` (modified)
- `apps/flutter/lib/services/audio_streaming.dart` (modified)
- `apps/flutter/lib/screens/scam_detection_demo.dart` (modified)
- `apps/flutter/lib/services/realtime_scam_detection.dart` (modified)
- `apps/flutter/pubspec.yaml` (modified)

### Files Disabled (Out of Scope)
- RecorderService.kt.disabled
- RecordingPriorityManager.kt.disabled
- ShizukuAudioCapture.kt.disabled
- ShizukuUserServiceManager.kt.disabled
- WrappedShellContext.kt.disabled
- IRecorderService.aidl.disabled
- AudioRecorderJob.kt.disabled
- HiddenApiBootstrap.kt.disabled
- ServiceContext.kt.disabled

---

**Status:** Implementation complete, build successful, device testing pending.  
**Next Action:** Install APK on real Android device and test with real phone call.
