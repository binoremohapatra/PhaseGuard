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
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.EventChannel
import kotlinx.coroutines.launch
import java.nio.ByteBuffer

class MainActivity : FlutterActivity() {
    private val TAG = "ScreenAudioCapture"
    private val CHANNEL = "phaseguard/screen_audio"
    private val BLUETOOTH_CHANNEL = "phaseguard/bluetooth_sco"
    
    private var mediaProjectionManager: MediaProjectionManager? = null
    private var sampleRate = 16000
    private var methodChannel: MethodChannel? = null
    private var bluetoothMethodChannel: MethodChannel? = null
    
    private var isCapturing = false
    
    private var bluetoothScoCapture: BluetoothScoCapture? = null
    // Shizuku capture disabled - not in scope for current implementation
    // private var shizukuAudioCapture: ShizukuAudioCapture? = null
    // private var recordingPriorityManager: RecordingPriorityManager? = null
    private var audioCaptureModule: AudioCaptureModule? = null
    
    // Coroutine scope for async operations
    private val coroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Set flutter messenger for Accessibility Service
        CallAccessibilityService.setFlutterMessenger(flutterEngine.dartExecutor.binaryMessenger)
        
        // Initialize Bluetooth SCO capture
        bluetoothScoCapture = BluetoothScoCapture()
        bluetoothScoCapture?.initialize(this, flutterEngine.dartExecutor.binaryMessenger!!)

        // Shizuku audio capture disabled - not in scope for current implementation
        // shizukuAudioCapture = ShizukuAudioCapture()
        // shizukuAudioCapture?.initialize(flutterEngine.dartExecutor.binaryMessenger!!, this)

        // Recording Priority Manager disabled - not in scope for current implementation
        // recordingPriorityManager = RecordingPriorityManager(this)
        // recordingPriorityManager?.initialize(flutterEngine.dartExecutor.binaryMessenger)

        // Initialize Audio Capture Module for in-call recording
        audioCaptureModule = AudioCaptureModule()
        val audioCaptureMethodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/audio_capture")
        val audioCaptureEventChannel = EventChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/audio_capture_events")
        audioCaptureModule?.initialize(this, audioCaptureMethodChannel, audioCaptureEventChannel)
        
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
        
        ScreenCaptureService.onAudioDataListener = { data ->
            runOnUiThread {
                methodChannel?.invokeMethod("onAudioData", mapOf("data" to data.toList()))
            }
        }
        
        ScreenCaptureService.onCaptureErrorListener = { error ->
            runOnUiThread {
                methodChannel?.invokeMethod("onCaptureError", mapOf("error" to error))
                isCapturing = false
            }
        }
        
        ScreenCaptureService.onCaptureStoppedListener = {
            runOnUiThread {
                methodChannel?.invokeMethod("onCaptureStopped", null)
                isCapturing = false
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

        // Shizuku method channel disabled - not in scope for current implementation
        /*
        val shizukuChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/shizuku_audio")
        shizukuChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "getShizukuState" -> {
                    shizukuAudioCapture?.getShizukuState(result)
                }
                "requestShizukuPermission" -> {
                    shizukuAudioCapture?.requestShizukuPermission(result)
                }
                "startElevatedCapture" -> {
                    val sampleRate = call.argument<Int>("sampleRate") ?: 16000
                    shizukuAudioCapture?.startElevatedCapture(
                        null,
                        Activity.RESULT_CANCELED,
                        null,
                        sampleRate,
                        result
                    )
                }
                "stopElevatedCapture" -> {
                    shizukuAudioCapture?.stopElevatedCapture(result)
                }
                "runSelfTest" -> {
                    shizukuAudioCapture?.runSelfTest(result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
        */

        // Recording Priority Manager method channel disabled - not in scope for current implementation
        /*
        val priorityChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/priority_recording")
        priorityChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "startPriorityRecording" -> {
                    val sampleRate = call.argument<Int>("sampleRate") ?: 16000
                    coroutineScope.launch {
                        val recordingResult = recordingPriorityManager?.startRecording(sampleRate)
                        result.success(mapOf(
                            "success" to recordingResult?.success,
                            "method" to recordingResult?.method?.name,
                            "message" to recordingResult?.message,
                            "health" to recordingResult?.health,
                            "speakerphoneEnabled" to recordingResult?.speakerphoneEnabled,
                            "hardwareRecommended" to recordingResult?.hardwareRecommended,
                            "hardwareOptions" to recordingResult?.hardwareOptions
                        ))
                    }
                }
                "stopPriorityRecording" -> {
                    coroutineScope.launch {
                        val recordingResult = recordingPriorityManager?.stopRecording()
                        result.success(mapOf(
                            "success" to recordingResult?.success,
                            "method" to recordingResult?.method?.name,
                            "message" to recordingResult?.message
                        ))
                    }
                }
                "getRecordingStatus" -> {
                    val status = recordingPriorityManager?.getRecordingStatus()
                    result.success(status)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
        */
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
            val result = pendingResult
            pendingResult = null
            
            if (resultCode == Activity.RESULT_OK && data != null) {
                try {
                    val intent = Intent(this, ScreenCaptureService::class.java).apply {
                        putExtra("RESULT_CODE", resultCode)
                        putExtra("DATA_INTENT", data)
                        putExtra("SAMPLE_RATE", sampleRate)
                    }
                    
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(intent)
                    } else {
                        startService(intent)
                    }
                    
                    isCapturing = true
                    result?.success(true)
                } catch (e: Exception) {
                    Log.e(TAG, "Error starting ScreenCaptureService: ${e.message}")
                    result?.success(false)
                }
            } else {
                result?.success(false)
            }
        }
    }
    
    private fun stopCapture(result: MethodChannel.Result) {
        try {
            val intent = Intent(this, ScreenCaptureService::class.java).apply {
                action = "STOP"
            }
            startService(intent)
            result.success(true)
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
        // Shizuku audio capture disabled - not in scope for current implementation
        // shizukuAudioCapture?.cleanup()
        audioCaptureModule?.cleanup()
    }
    
    companion object {
        private const val SCREEN_CAPTURE_REQUEST_CODE = 1001
    }
}
