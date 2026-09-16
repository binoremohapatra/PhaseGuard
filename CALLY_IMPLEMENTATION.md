# Cally-like Implementation for PhaseGuard

## Overview

This implementation adds the Cally-like approach for call audio capture using Shizuku's UserService mechanism. This is the most promising method for single-device call audio capture without root access.

## What Was Implemented

### 1. Core Android Components

#### WrappedShellContext.kt
- **Purpose**: Patches ActivityThread to make AudioFlinger believe the app is running as `com.android.shell` (UID 2000)
- **Key Features**:
  - Pretends to be `com.android.shell` system package
  - Patches 4 ActivityThread fields: `sCurrentActivityThread`, `mSystemThread`, `mInitialApplication`, `mBoundApplication`
  - Overrides identity methods: `getPackageName()`, `getOpPackageName()`, `getAttributionSource()`
  - Provides health diagnostics (Full/Degraded/Failed)

#### RecorderService.kt
- **Purpose**: Privileged audio recorder running in Shizuku's shell-UID process
- **Key Features**:
  - Implements AIDL interface `IRecorderService`
  - Supports dual-track recording (VOICE_UPLINK + VOICE_DOWNLINK)
  - Single-stream fallback for incompatible devices
  - Caller verification for security
  - Health monitoring

#### AudioRecorderJob.kt
- **Purpose**: Individual AudioRecord pump for each audio stream
- **Key Features**:
  - Constructs AudioRecord on main Looper (critical for AppOps)
  - Uses WrappedShellContext for identity
  - Real-time audio streaming via ParcelFileDescriptor pipes
  - Error handling and statistics

#### ServiceContext.kt
- **Purpose**: Provides system Context inside Shizuku's app_process
- **Key Features**:
  - Reflection-based ActivityThread access
  - Main Looper marshaling for Binder thread safety
  - Context caching for performance

#### HiddenApiBootstrap.kt
- **Purpose**: Bypasses Android P+ hidden API restrictions
- **Key Features**:
  - Uses HiddenApiBypass library
  - Scoped exemptions for relevant Android prefixes
  - Idempotent operation

#### IRecorderService.aidl
- **Purpose**: AIDL interface for app-to-UserService communication
- **Key Features**:
  - Version tracking for daemon detection
  - Dual-track and single-track recording methods
  - Health diagnostics
  - State management

#### ShizukuUserServiceManager.kt
- **Purpose**: Manages Shizuku UserService lifecycle from app
- **Key Features**:
  - UserService binding and lifecycle
  - 5-step fallback ladder implementation
  - Health monitoring
  - Pipe management for audio streaming

### 2. Flutter Integration Updates

#### shizuku_capture.dart
- **Updated**: Changed from MediaProjection-based to Cally-like approach
- **New Features**:
  - Removed MediaProjection dependency
  - Added bypass health tracking
  - Added fallback step tracking
  - Enhanced event streaming with stream information

#### calls_screen.dart
- **Updated**: UI integration for Cally-like capture
- **New Features**:
  - Direct capture start (no MediaProjection permission)
  - Health status display
  - Fallback step display
  - Updated user guidance

### 3. Build Configuration

#### build.gradle.kts
- **Added**: HiddenApiBypass dependency
- **Purpose**: Required for ActivityThread reflection

## How It Works

### Architecture Flow

```
App Process (UID u0_aXXX)
    ↓ AIDL Binder
Shizuku UserService Process (UID 2000 = shell)
    ↓ WrappedShellContext
ActivityThread Patches
    ↓ AttributionSource
AudioFlinger Permission Check
    ↓ VOICE_* Sources
AudioRecord → Pipe → App Process
```

### 5-Step Fallback Ladder

1. **VOICE_UPLINK** (Remote caller audio)
2. **VOICE_DOWNLINK** (Local mic audio)
3. **VOICE_CALL** (Both streams combined)
4. **MEDIA** (Fallback media source)
5. **MIC** (Last resort microphone)

### Key Technical Insights

1. **Shell Identity**: By pretending to be `com.android.shell`, we gain signature-level permissions (RECORD_AUDIO, CAPTURE_AUDIO_OUTPUT, MODIFY_AUDIO_ROUTING)

2. **ActivityThread Patching**: AudioFlinger checks caller identity through ActivityThread chain. We patch this chain to return our wrapped identity.

3. **Main Looper Construction**: AudioRecord must be constructed on main Looper for AppOps to work correctly in shell-UID process.

4. **AttributionSource**: Modern Android (API 31+) requires AttributionSource.Builder with setContext() to pick up wrapped identity.

## Advantages Over Previous Approach

### Previous (MediaProjection-based)
- ❌ AudioPlaybackCaptureConfiguration doesn't support VOICE_COMMUNICATION
- ❌ Fundamental Android API limitation
- ❌ Produces silent buffers for call audio

### New (Cally-like)
- ✅ Direct AudioRecord with VOICE_* sources
- ✅ Proven to work on real devices (Cally project)
- ✅ Dual-track capture (uplink + downlink)
- ✅ 5-step fallback ladder
- ✅ Health diagnostics
- ✅ No MediaProjection permission needed

## Testing Requirements

### Prerequisites
1. Android device with Shizuku installed
2. Shizuku permission granted to PhaseGuard
3. Real phone call (not simulated)

### Testing Steps
1. Install Shizuku from F-Droid or GitHub
2. Enable wireless debugging
3. Start Shizuku app
4. Grant Shizuku permission to PhaseGuard
5. Enable Shizuku Audio in PhaseGuard
6. Make/receive a real phone call
7. Monitor:
   - Bypass health (should be "Full" or "Degraded")
   - Fallback step (ideally step 1 for dual-track)
   - Non-zero percentage (should be >1% for real audio)

### Expected Results
- **Full Health**: All 4 ActivityThread patches applied
- **Dual Recording**: Both uplink and downlink streams active
- **Real Audio**: Non-zero percentage >1% during call
- **Fallback**: If dual fails, should fall back to single stream

## Limitations and Risks

### Limitations
- ROM-dependent (Samsung/MIUI may still block)
- Requires Shizuku setup (user education needed)
- May need device-specific testing
- Hidden API bypass may break in future Android versions

### Risks
- Reflection-based (fragile to Android updates)
- System identity spoofing (security consideration)
- Shell UID privileges (potential abuse if compromised)

## Future Improvements

1. **Certificate Pinning**: Add signing certificate verification in RecorderService
2. **Device Compatibility**: Build device-specific compatibility matrix
3. **Audio Quality**: Add format conversion and quality settings
4. **Error Recovery**: Enhanced fallback and recovery mechanisms
5. **User Education**: Better onboarding for Shizuku setup

## References

- **Cally Project**: https://github.com/LyoSU/cally
- **Shizuku**: https://github.com/RikkaApps/Shizuku
- **HiddenApiBypass**: https://github.com/LSPosed/AndroidHiddenApiBypass

## Credits

This implementation is based on the Cally project by LyoSU, which pioneered the WrappedShellContext technique for shell-UID call audio capture.
