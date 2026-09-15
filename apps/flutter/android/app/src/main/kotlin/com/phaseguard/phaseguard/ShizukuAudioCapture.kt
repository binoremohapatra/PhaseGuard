package com.phaseguard.phaseguard

import android.content.Context
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import io.flutter.plugin.common.MethodChannel
import rikka.shizuku.Shizuku
import kotlin.system.exitProcess

/**
 * Shizuku Audio Capture (Advanced/Experimental)
 * 
 * Uses Shizuku to run commands with shell UID 2000 privileges.
 * This can potentially access system-level audio paths not available to normal apps.
 * 
 * CRITICAL NOTES:
 * - REQUIRES Shizuku to be installed on the device
 * - REQUIRES wireless debugging to be enabled
 * - REQUIRES user to grant Shizuku permission to this app
 * - Complex setup process for users
 * - Device compatibility varies
 * - Marked as EXPERIMENTAL - may not work on all devices
 * 
 * SETUP INSTRUCTIONS FOR USERS:
 * 1. Install Shizuku from F-Droid or GitHub
 * 2. Enable wireless debugging on device
 * 3. Connect device via ADB or wireless debugging
 * 4. Start Shizuku app
 * 5. Grant PhaseGuard permission in Shizuku
 * 6. This app can then use shell UID for audio capture
 */
class ShizukuAudioCapture {
    private val TAG = "ShizukuAudioCapture"
    private val CHANNEL = "phaseguard/shizuku_audio"
    
    private var audioRecord: AudioRecord? = null
    private var isCapturing = false
    private var sampleRate = 16000
    private var shizukuAvailable = false
    private var shizukuPermissionGranted = false
    private var context: Context? = null
    
    private val handler = Handler(Looper.getMainLooper())
    private var methodChannel: MethodChannel? = null
    
    // Shizuku detection (will be checked at runtime)
    private var shizukuInstalled = false
    
    fun initialize(messenger: io.flutter.plugin.common.BinaryMessenger, appContext: Context) {
        context = appContext
        methodChannel = MethodChannel(messenger, CHANNEL)
        checkShizukuAvailability()
        Log.i(TAG, "Shizuku audio capture initialized")
    }
    
    fun setMethodCallHandler(handler: MethodChannel.MethodCallHandler) {
        methodChannel?.setMethodCallHandler(handler)
    }
    
    /**
     * Check if Shizuku is installed and available
     */
    private fun checkShizukuAvailability() {
        try {
            shizukuInstalled = Shizuku.pingBinder()
            shizukuAvailable = shizukuInstalled && !Shizuku.isPreV11()
            shizukuPermissionGranted = shizukuInstalled && Shizuku.checkSelfPermission() == android.content.pm.PackageManager.PERMISSION_GRANTED
            Log.i(TAG, "Shizuku available: $shizukuAvailable, permission: $shizukuPermissionGranted")
        } catch (e: Exception) {
            Log.e(TAG, "Shizuku check error: ${e.message}")
            shizukuAvailable = false
            shizukuInstalled = false
            shizukuPermissionGranted = false
        }
    }
    
    /**
     * Request Shizuku permission
     * This requires user to grant permission via Shizuku app
     */
    fun requestShizukuPermission(result: MethodChannel.Result) {
        checkShizukuAvailability()
        if (!shizukuInstalled) {
            result.success(mapOf("granted" to false, "installed" to false, "message" to "Shizuku not installed or active"))
            return
        }
        if (Shizuku.checkSelfPermission() == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            shizukuPermissionGranted = true
            result.success(mapOf("granted" to true, "installed" to true))
            return
        }
        
        val listener = object : Shizuku.OnRequestPermissionResultListener {
            override fun onRequestPermissionResult(requestCode: Int, grantResult: Int) {
                if (requestCode == 100) {
                    val granted = grantResult == android.content.pm.PackageManager.PERMISSION_GRANTED
                    shizukuPermissionGranted = granted
                    Shizuku.removeRequestPermissionResultListener(this)
                    result.success(mapOf("granted" to granted, "installed" to true))
                }
            }
        }
        Shizuku.addRequestPermissionResultListener(listener)
        try {
            Shizuku.requestPermission(100)
        } catch (e: Exception) {
            Shizuku.removeRequestPermissionResultListener(listener)
            result.success(mapOf("granted" to false, "installed" to true, "message" to e.message))
        }
    }
    
    /**
     * Start audio capture using Shizuku privileges
     * This attempts to use VOICE_CALL audio source which is normally restricted
     */
    fun startAudioCapture(sampleRate: Int, result: MethodChannel.Result) {
        if (isCapturing) {
            result.success(true)
            return
        }
        
        if (!shizukuAvailable) {
            result.success(false)
            return
        }
        
        try {
            this.sampleRate = sampleRate
            
            // Try to use VOICE_CALL audio source (normally restricted)
            // With Shizuku's shell UID, this might work on some devices
            val audioSource = AudioManager.STREAM_VOICE_CALL
            val channelConfig = AudioFormat.CHANNEL_IN_MONO
            val audioFormat = AudioFormat.ENCODING_PCM_16BIT
            
            val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat) * 2
            
            audioRecord = AudioRecord(
                audioSource,
                sampleRate,
                channelConfig,
                audioFormat,
                bufferSize
            )
            
            if (audioRecord?.state == AudioRecord.STATE_INITIALIZED) {
                audioRecord?.startRecording()
                isCapturing = true
                
                // Start audio capture thread
                Thread {
                    captureAudio(bufferSize)
                }.start()
                
                Log.i(TAG, "Shizuku audio capture started")
                notifyFlutter("shizukuCaptureStarted", mapOf("sampleRate" to sampleRate))
                result.success(true)
            } else {
                // Fallback to MIC if VOICE_CALL fails
                Log.w(TAG, "VOICE_CALL source failed, trying MIC fallback")
                startFallbackCapture(sampleRate, result)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error starting Shizuku audio capture: ${e.message}")
            startFallbackCapture(sampleRate, result)
        }
    }
    
    /**
     * Fallback capture using MIC if privileged sources fail
     */
    private fun startFallbackCapture(sampleRate: Int, result: MethodChannel.Result) {
        try {
            val audioSource = AudioManager.STREAM_MUSIC
            val channelConfig = AudioFormat.CHANNEL_IN_MONO
            val audioFormat = AudioFormat.ENCODING_PCM_16BIT
            
            val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat) * 2
            
            audioRecord = AudioRecord(
                audioSource,
                sampleRate,
                channelConfig,
                audioFormat,
                bufferSize
            )
            
            if (audioRecord?.state == AudioRecord.STATE_INITIALIZED) {
                audioRecord?.startRecording()
                isCapturing = true
                
                Thread {
                    captureAudio(bufferSize)
                }.start()
                
                Log.i(TAG, "Shizuku fallback audio capture started")
                notifyFlutter("shizukuCaptureStarted", mapOf(
                    "sampleRate" to sampleRate,
                    "fallback" to true
                ))
                result.success(true)
            } else {
                Log.e(TAG, "Fallback AudioRecord initialization failed")
                notifyFlutter("shizukuCaptureFailed", mapOf("error" to "AudioRecord initialization failed"))
                result.success(false)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in fallback capture: ${e.message}")
            notifyFlutter("shizukuCaptureFailed", mapOf("error" to e.message))
            result.success(false)
        }
    }
    
    private fun captureAudio(bufferSize: Int) {
        val buffer = ByteArray(bufferSize)
        
        while (isCapturing) {
            try {
                val bytesRead = audioRecord?.read(buffer, 0, bufferSize) ?: 0
                
                if (bytesRead > 0) {
                    val audioData = buffer.copyOfRange(0, bytesRead)
                    notifyFlutter("onShizukuAudioData", mapOf("data" to audioData.toList()))
                }
                
                Thread.sleep(10)
                
            } catch (e: Exception) {
                Log.e(TAG, "Error capturing Shizuku audio: ${e.message}")
                break
            }
        }
    }
    
    fun stopAudioCapture(result: MethodChannel.Result) {
        try {
            isCapturing = false
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
            
            Log.i(TAG, "Shizuku audio capture stopped")
            notifyFlutter("shizukuCaptureStopped", null)
            result.success(true)
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping Shizuku capture: ${e.message}")
            result.success(false)
        }
    }
    
    fun getDeviceInfo(result: MethodChannel.Result) {
        val info = mapOf(
            "shizukuInstalled" to shizukuInstalled,
            "shizukuAvailable" to shizukuAvailable,
            "permissionGranted" to shizukuPermissionGranted,
            "sdkVersion" to Build.VERSION.SDK_INT,
            "androidVersion" to Build.VERSION.RELEASE,
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL
        )
        result.success(info)
    }
    
    private fun notifyFlutter(method: String, data: Map<String, Any?>?) {
        handler.post {
            methodChannel?.invokeMethod(method, data)
        }
    }
    
    fun cleanup() {
        stopAudioCapture(object : MethodChannel.Result {
            override fun success(result: Any?) {}
            override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {}
            override fun notImplemented() {}
        })
    }
}