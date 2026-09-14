package com.phaseguard.phaseguard

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.nio.ByteBuffer

class MainActivity : FlutterActivity() {
    private val TAG = "ScreenAudioCapture"
    private val CHANNEL = "phaseguard/screen_audio"
    private val BLUETOOTH_CHANNEL = "phaseguard/bluetooth_sco"
    
    private var mediaProjectionManager: MediaProjectionManager? = null
    private var mediaProjection: MediaProjection? = null
    private var audioRecord: AudioRecord? = null
    private var isCapturing = false
    private var sampleRate = 16000
    private var methodChannel: MethodChannel? = null
    private var bluetoothMethodChannel: MethodChannel? = null
    
    private val audioBuffer = ByteBuffer.allocateDirect(4096)
    private val handler = Handler(Looper.getMainLooper())
    
    private var bluetoothScoCapture: BluetoothScoCapture? = null
    private var shizukuAudioCapture: ShizukuAudioCapture? = null
    
    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Set flutter messenger for Accessibility Service
        CallAccessibilityService.setFlutterMessenger(flutterEngine.dartExecutor.binaryMessenger)
        
        // Initialize Bluetooth SCO capture
        bluetoothScoCapture = BluetoothScoCapture()
        bluetoothScoCapture?.initialize(this, flutterEngine.dartExecutor.binaryMessenger!!)
        
        // Initialize Shizuku audio capture
        shizukuAudioCapture = ShizukuAudioCapture()
        shizukuAudioCapture?.initialize(flutterEngine.dartExecutor.binaryMessenger!!, this)
        
        methodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        methodChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "requestPermissionAndStart" -> {
                    val requestedSampleRate = call.argument<Int>("sampleRate") ?: 16000
                    requestPermissionAndStart(requestedSampleRate, result)
                }
                "stopCapture" -> {
                    stopCapture(result)
                }
                "isAvailable" -> {
                    isAvailable(result)
                }
                "getDeviceInfo" -> {
                    getDeviceInfo(result)
                }
                "isAccessibilityServiceEnabled" -> {
                    isAccessibilityServiceEnabled(result)
                }
                "enableAccessibilityService" -> {
                    enableAccessibilityService(result)
                }
                "getAccessibilityServiceState" -> {
                    getAccessibilityServiceState(result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
        
        // Bluetooth SCO method channel
        bluetoothMethodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, BLUETOOTH_CHANNEL)
        bluetoothMethodChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "startScoCapture" -> {
                    val requestedSampleRate = call.argument<Int>("sampleRate") ?: 16000
                    bluetoothScoCapture?.startScoCapture(requestedSampleRate, result)
                }
                "stopScoCapture" -> {
                    bluetoothScoCapture?.stopScoCapture(result)
                }
                "getScoDeviceInfo" -> {
                    bluetoothScoCapture?.getDeviceInfo(result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
        
        // Shizuku method channel
        val shizukuChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/shizuku_audio")
        shizukuChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "requestShizukuPermission" -> {
                    shizukuAudioCapture?.requestShizukuPermission(result)
                }
                "startShizukuCapture" -> {
                    val requestedSampleRate = call.argument<Int>("sampleRate") ?: 16000
                    shizukuAudioCapture?.startAudioCapture(requestedSampleRate, result)
                }
                "stopShizukuCapture" -> {
                    shizukuAudioCapture?.stopAudioCapture(result)
                }
                "getShizukuDeviceInfo" -> {
                    shizukuAudioCapture?.getDeviceInfo(result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }
    
    private fun requestPermissionAndStart(sampleRate: Int, result: MethodChannel.Result) {
        if (isCapturing) {
            result.success(true)
            return
        }
        
        mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        
        val intent = mediaProjectionManager?.createScreenCaptureIntent()
        
        try {
            startActivityForResult(intent, SCREEN_CAPTURE_REQUEST_CODE)
            this.sampleRate = sampleRate
            // Store the result callback to call after permission is granted
            pendingResult = result
        } catch (e: Exception) {
            Log.e(TAG, "Error requesting screen capture: ${e.message}")
            result.success(false)
        }
    }
    
    private var pendingResult: MethodChannel.Result? = null
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        
        if (requestCode == SCREEN_CAPTURE_REQUEST_CODE) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                val result = pendingResult
                pendingResult = null
                
                try {
                    mediaProjection = mediaProjectionManager?.getMediaProjection(resultCode, data)
                    
                    if (mediaProjection != null) {
                        startAudioCapture()
                        result?.success(true)
                    } else {
                        result?.success(false)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error getting media projection: ${e.message}")
                    result?.success(false)
                }
            } else {
                val result = pendingResult
                pendingResult = null
                result?.success(false)
            }
        }
    }
    
    private fun startAudioCapture() {
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
            
            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord initialization failed")
                methodChannel?.invokeMethod("onCaptureError", mapOf("error" to "AudioRecord initialization failed"))
                return
            }
            
            audioRecord?.startRecording()
            isCapturing = true
            
            // Start audio capture thread
            Thread {
                captureAudio(bufferSize)
            }.start()
            
            Log.i(TAG, "Audio capture started successfully")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error starting audio capture: ${e.message}")
            methodChannel?.invokeMethod("onCaptureError", mapOf("error" to e.message))
            isCapturing = false
        }
    }
    
    private fun captureAudio(bufferSize: Int) {
        val buffer = ByteArray(bufferSize)
        
        while (isCapturing) {
            try {
                val bytesRead = audioRecord?.read(buffer, 0, bufferSize) ?: 0
                
                if (bytesRead > 0) {
                    // Send audio data to Flutter
                    val audioData = buffer.copyOfRange(0, bytesRead)
                    methodChannel?.invokeMethod("onAudioData", mapOf("data" to audioData.toList()))
                }
                
                // Small delay to prevent CPU overload
                Thread.sleep(10)
                
            } catch (e: Exception) {
                Log.e(TAG, "Error capturing audio: ${e.message}")
                break
            }
        }
    }
    
    private fun stopCapture(result: MethodChannel.Result) {
        try {
            isCapturing = false
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
            mediaProjection?.stop()
            mediaProjection = null
            
            methodChannel?.invokeMethod("onCaptureStopped", null)
            result.success(true)
            
            Log.i(TAG, "Audio capture stopped")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping capture: ${e.message}")
            result.success(false)
        }
    }
    
    private fun isAvailable(result: MethodChannel.Result) {
        // Screen audio capture is available on most Android 5.0+ devices
        val available = Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP
        result.success(available)
    }
    
    private fun getDeviceInfo(result: MethodChannel.Result) {
        val info = mapOf(
            "available" to (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP),
            "sdk_int" to Build.VERSION.SDK_INT,
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL,
            "android_version" to Build.VERSION.RELEASE
        )
        result.success(info)
    }
    
    private fun isAccessibilityServiceEnabled(result: MethodChannel.Result) {
        val service = CallAccessibilityService.getInstance()
        result.success(service != null)
    }
    
    private fun enableAccessibilityService(result: MethodChannel.Result) {
        try {
            val intent = Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS)
            startActivity(intent)
            result.success(true)
        } catch (e: Exception) {
            Log.e(TAG, "Error opening accessibility settings: ${e.message}")
            result.success(false)
        }
    }
    
    private fun getAccessibilityServiceState(result: MethodChannel.Result) {
        val service = CallAccessibilityService.getInstance()
        val state = mapOf(
            "enabled" to (service != null),
            "callState" to service?.getCallState(),
            "phoneNumber" to service?.getPhoneNumber(),
            "isCapturing" to service?.isCapturingAudio()
        )
        result.success(state)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        stopCapture(object : MethodChannel.Result {
            override fun success(result: Any?) {}
            override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {}
            override fun notImplemented() {}
        })
        bluetoothScoCapture?.cleanup()
        shizukuAudioCapture?.cleanup()
    }
    
    companion object {
        private const val SCREEN_CAPTURE_REQUEST_CODE = 1001
    }
}
