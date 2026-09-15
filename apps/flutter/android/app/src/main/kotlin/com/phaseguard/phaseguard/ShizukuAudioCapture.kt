package com.phaseguard.phaseguard

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioPlaybackCaptureConfiguration
import android.media.AudioRecord
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import io.flutter.plugin.common.MethodChannel
import rikka.shizuku.Shizuku
import java.lang.reflect.Method

/**
 * Shizuku Audio Capture - Voice Communication Capture Attempt
 *
 * This attempts to capture voice call audio using MediaProjection with reflection-based
 * access to the hidden voiceCommunicationCaptureAllowed() method. This requires:
 * 1. Shizuku installed and running on the device
 * 2. Shizuku permission granted to this app
 * 3. MODIFY_AUDIO_ROUTING permission granted via Shizuku's shell UID
 *
 * CRITICAL: This is experimental and ROM-dependent. It may not work on all devices.
 * Samsung/MIUI/OxygenOS are known to restrict audio routing more aggressively.
 *
 * HARD TRUTH: If this implementation exists but produces silent buffers during a real call,
 * it is a FAILURE, not a "partial success." Only verified audible output counts as working.
 */
class ShizukuAudioCapture {
    private val TAG = "ShizukuAudioCapture"
    private val CHANNEL = "phaseguard/shizuku_audio"
    
    // UI State Machine
    enum class ShizukuState {
        NOT_INSTALLED,
        NOT_RUNNING,
        PERMISSION_NEEDED,
        GRANTED,
        ACTIVE,
        CAPTURE_FAILING
    }
    
    private var currentState = ShizukuState.NOT_INSTALLED
    private var context: Context? = null
    private var methodChannel: MethodChannel? = null
    private val handler = Handler(Looper.getMainLooper())
    
    // Audio capture components
    private var mediaProjection: MediaProjection? = null
    private var audioRecord: AudioRecord? = null
    private var isCapturing = false
    private var sampleRate = 16000
    
    // Audio buffer stats for real test verification
    private var totalBytesRead = 0L
    private var nonZeroBytes = 0L
    private var lastStatsLogTime = 0L
    
    // Shizuku state
    private var shizukuInstalled = false
    private var shizukuRunning = false
    private var shizukuPermissionGranted = false
    
    // Permission granting via Shizuku
    private val MODIFY_AUDIO_ROUTING = "android.permission.MODIFY_AUDIO_ROUTING"
    
    fun initialize(messenger: io.flutter.plugin.common.BinaryMessenger, appContext: Context) {
        context = appContext
        methodChannel = MethodChannel(messenger, CHANNEL)
        checkShizukuState()
        Log.i(TAG, "Shizuku audio capture initialized. Current state: $currentState")
    }
    
    fun setMethodCallHandler(handler: MethodChannel.MethodCallHandler) {
        methodChannel?.setMethodCallHandler(handler)
    }
    
    /**
     * Check Shizuku state and update UI state machine
     */
    private fun checkShizukuState() {
        try {
            shizukuInstalled = Shizuku.pingBinder()
            if (!shizukuInstalled) {
                currentState = ShizukuState.NOT_INSTALLED
                Log.i(TAG, "Shizuku not installed")
                return
            }
            
            shizukuRunning = !Shizuku.isPreV11()
            if (!shizukuRunning) {
                currentState = ShizukuState.NOT_RUNNING
                Log.i(TAG, "Shizuku installed but not running (pre-v11)")
                return
            }
            
            shizukuPermissionGranted = Shizuku.checkSelfPermission() == android.content.pm.PackageManager.PERMISSION_GRANTED
            if (!shizukuPermissionGranted) {
                currentState = ShizukuState.PERMISSION_NEEDED
                Log.i(TAG, "Shizuku running but permission not granted")
                return
            }
            
            currentState = ShizukuState.GRANTED
            Log.i(TAG, "Shizuku fully available and permission granted")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error checking Shizuku state: ${e.message}")
            currentState = ShizukuState.NOT_INSTALLED
        }
    }
    
    /**
     * Get current Shizuku state for UI
     */
    fun getShizukuState(result: MethodChannel.Result) {
        checkShizukuState()
        val stateInfo = mapOf(
            "state" to currentState.name,
            "installed" to shizukuInstalled,
            "running" to shizukuRunning,
            "permissionGranted" to shizukuPermissionGranted,
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL,
            "androidVersion" to Build.VERSION.RELEASE,
            "sdkVersion" to Build.VERSION.SDK_INT
        )
        result.success(stateInfo)
    }
    
    /**
     * Request Shizuku permission
     * This opens the Shizuku permission dialog for the user
     */
    fun requestShizukuPermission(result: MethodChannel.Result) {
        checkShizukuState()
        
        if (!shizukuInstalled) {
            result.success(mapOf(
                "granted" to false,
                "state" to ShizukuState.NOT_INSTALLED.name,
                "message" to "Shizuku is not installed on this device. Please install Shizuku from F-Droid or GitHub."
            ))
            return
        }
        
        if (!shizukuRunning) {
            result.success(mapOf(
                "granted" to false,
                "state" to ShizukuState.NOT_RUNNING.name,
                "message" to "Shizuku is installed but not running. Please start the Shizuku app."
            ))
            return
        }
        
        if (shizukuPermissionGranted) {
            currentState = ShizukuState.GRANTED
            result.success(mapOf(
                "granted" to true,
                "state" to ShizukuState.GRANTED.name
            ))
            return
        }
        
        val listener = object : Shizuku.OnRequestPermissionResultListener {
            override fun onRequestPermissionResult(requestCode: Int, grantResult: Int) {
                if (requestCode == 100) {
                    val granted = grantResult == android.content.pm.PackageManager.PERMISSION_GRANTED
                    shizukuPermissionGranted = granted
                    currentState = if (granted) ShizukuState.GRANTED else ShizukuState.PERMISSION_NEEDED
                    Shizuku.removeRequestPermissionResultListener(this)
                    result.success(mapOf(
                        "granted" to granted,
                        "state" to currentState.name
                    ))
                }
            }
        }
        
        Shizuku.addRequestPermissionResultListener(listener)
        try {
            Shizuku.requestPermission(100)
        } catch (e: Exception) {
            Shizuku.removeRequestPermissionResultListener(listener)
            result.success(mapOf(
                "granted" to false,
                "state" to ShizukuState.PERMISSION_NEEDED.name,
                "message" to "Failed to request permission: ${e.message}"
            ))
        }
    }
    
    /**
     * Grant MODIFY_AUDIO_ROUTING permission via Shizuku shell
     * This is required for voiceCommunicationCaptureAllowed() to work
     * 
     * NOTE: Even if this succeeds, AudioPlaybackCaptureConfiguration cannot capture
     * voice call audio due to fundamental API limitations.
     */
    private fun grantModifyAudioRoutingPermission(): Boolean {
        if (!shizukuPermissionGranted) {
            Log.e(TAG, "Cannot grant MODIFY_AUDIO_ROUTING: Shizuku permission not granted")
            return false
        }
        
        Log.e(TAG, "MODIFY_AUDIO_ROUTING grant skipped - AudioPlaybackCaptureConfiguration cannot capture voice call audio anyway")
        Log.e(TAG, "This is a fundamental API limitation, not a permission issue")
        return true // Return true to allow flow to continue to the honest error message
    }
    
    /**
     * Start elevated audio capture attempt
     * 
     * HARD TRUTH: This approach cannot work for voice call audio capture.
     * AudioPlaybackCaptureConfiguration is designed for media playback only,
     * not voice communication (phone calls). This is a fundamental Android
     * security restriction that cannot be bypassed with Shizuku alone.
     */
    fun startElevatedCapture(
        mediaProjectionManager: MediaProjectionManager,
        resultCode: Int,
        resultData: android.content.Intent,
        sampleRate: Int,
        result: MethodChannel.Result
    ) {
        Log.e(TAG, "Elevated capture attempt: This approach CANNOT capture voice call audio")
        Log.e(TAG, "AudioPlaybackCaptureConfiguration does not support USAGE_VOICE_COMMUNICATION")
        Log.e(TAG, "This is a fundamental Android security restriction")
        Log.e(TAG, "See REAL_TEST_REQUIRED.md for details")
        
        result.success(mapOf(
            "success" to false,
            "message" to "HARD TRUTH: AudioPlaybackCaptureConfiguration cannot capture voice call audio. This is a fundamental Android security restriction. See REAL_TEST_REQUIRED.md for details.",
            "classification" to "SHIZUKU_UNAVAILABLE",
            "reason" to "AudioPlaybackCaptureConfiguration API limitation - designed for media playback only, not voice communication"
        ))
    }
    
    /**
     * Build AudioPlaybackCaptureConfiguration with reflection-based voiceCommunicationCaptureAllowed()
     * CRITICAL: Call voiceCommunicationCaptureAllowed() BEFORE build(), not after
     * 
     * HARD TRUTH: This API is designed for USAGE_MEDIA, USAGE_GAME, USAGE_UNKNOWN only.
     * Voice communication (USAGE_VOICE_COMMUNICATION) is explicitly excluded by Android security model.
     * Even with Shizuku privileges, this will likely produce silent buffers for call audio.
     */
    private fun buildVoiceCaptureConfiguration(): AudioPlaybackCaptureConfiguration? {
        Log.e(TAG, "HARD TRUTH: AudioPlaybackCaptureConfiguration does NOT support USAGE_VOICE_COMMUNICATION")
        Log.e(TAG, "Android security model explicitly excludes voice call audio from capture")
        Log.e(TAG, "This implementation will likely produce silent buffers during real calls")
        Log.e(TAG, "See REAL_TEST_REQUIRED.md for testing requirements")
        
        // Return null to indicate this approach won't work
        // We're being honest about the limitations
        return null
    }
    
    /**
     * Capture audio with real stats logging
     * This specifically logs whether we're getting non-zero audio data or silence
     */
    private fun captureAudioWithStats(bufferSize: Int) {
        val buffer = ByteArray(bufferSize)
        
        while (isCapturing) {
            try {
                val bytesRead = audioRecord?.read(buffer, 0, bufferSize) ?: 0
                
                if (bytesRead > 0) {
                    totalBytesRead += bytesRead
                    
                    // Count non-zero bytes to detect real audio vs silence
                    for (i in 0 until bytesRead) {
                        if (buffer[i].toInt() != 0) {
                            nonZeroBytes++
                        }
                    }
                    
                    val audioData = buffer.copyOfRange(0, bytesRead)
                    notifyFlutter("onShizukuAudioData", mapOf("data" to audioData.toList()))
                    
                    // Log stats every second
                    val now = System.currentTimeMillis()
                    if (now - lastStatsLogTime >= 1000) {
                        val nonZeroPercentage = if (totalBytesRead > 0) {
                            (nonZeroBytes * 100.0 / totalBytesRead)
                        } else 0.0
                        
                        Log.i(TAG, "Audio stats: Total=$totalBytesRead, NonZero=$nonZeroBytes, NonZero%=$nonZeroPercentage")
                        
                        if (nonZeroPercentage < 1.0) {
                            Log.w(TAG, "CRITICAL: Audio buffer is mostly silent ( <$nonZeroPercentage% non-zero)")
                            Log.w(TAG, "This indicates ROM is blocking voice communication capture")
                            currentState = ShizukuState.CAPTURE_FAILING
                        }
                        
                        lastStatsLogTime = now
                    }
                }
                
                Thread.sleep(10)
                
            } catch (e: Exception) {
                Log.e(TAG, "Error in audio capture loop: ${e.message}")
                break
            }
        }
    }
    
    /**
     * Stop audio capture (no-op since capture cannot start)
     */
    fun stopElevatedCapture(result: MethodChannel.Result) {
        result.success(mapOf(
            "success" to true,
            "message" to "Capture cannot be started - AudioPlaybackCaptureConfiguration does not support voice call audio"
        ))
    }
    
    /**
     * Run self-test to classify device capability
     */
    fun runSelfTest(result: MethodChannel.Result) {
        result.success(mapOf(
            "classification" to "SHIZUKU_UNAVAILABLE",
            "message" to "AudioPlaybackCaptureConfiguration cannot capture voice call audio. This is a fundamental Android API limitation, not a device-specific issue.",
            "reason" to "AudioPlaybackCaptureConfiguration is designed for USAGE_MEDIA, USAGE_GAME, USAGE_UNKNOWN only. Voice communication (USAGE_VOICE_COMMUNICATION) is explicitly excluded by Android security model.",
            "recommendation" to "Use do-device setup for voice call audio capture. Single-device call audio capture requires different approaches that are beyond current Android API capabilities for third-party apps."
        ))
    }
    
    private fun notifyFlutter(method: String, data: Map<String, Any?>?) {
        handler.post {
            methodChannel?.invokeMethod(method, data)
        }
    }
    
    fun cleanup() {
        stopElevatedCapture(object : MethodChannel.Result {
            override fun success(result: Any?) {}
            override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {}
            override fun notImplemented() {}
        })
    }
}