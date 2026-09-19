package com.phaseguard.phaseguard

import android.content.Intent
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var tracker: PhoneCallTracker? = null
    private var speakerphoneService: SpeakerphoneAudioService? = null
    private var callAudioEventSink: EventChannel.EventSink? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // ── Phone state events ──────────────────────────────────────────────────
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/phone_state")
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    PhoneCallEmitter.sink = events
                }
                override fun onCancel(arguments: Any?) {
                    PhoneCallEmitter.sink = null
                }
            })

        // ── Phone control methods ───────────────────────────────────────────────
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "phaseguard/phone_control")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "startMonitor" -> {
                        startMonitor()
                        result.success(true)
                    }
                    "stopMonitor" -> {
                        stopMonitor()
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            }

        // ── Call audio capture stream (speakerphone fallback) ────────────────────
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "com.phaseguard/call_audio")
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    callAudioEventSink = events
                    // Start speakerphone service
                    val intent = Intent(this@MainActivity, SpeakerphoneAudioService::class.java)
                    startService(intent)
                    speakerphoneService = SpeakerphoneAudioService.getInstance()
                    speakerphoneService?.setAudioCallback { chunk ->
                        try {
                            val encoded = android.util.Base64.encodeToString(chunk, android.util.Base64.NO_WRAP)
                            callAudioEventSink?.success(encoded)
                        } catch (e: Exception) {
                            android.util.Log.e("MainActivity", "Failed to send audio chunk", e)
                        }
                    }
                }
                override fun onCancel(arguments: Any?) {
                    callAudioEventSink = null
                    speakerphoneService?.stopCapture()
                }
            })

        // ── Audio control: start/stop call capture + speakerphone toggle ────────
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.phaseguard/audio")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "startCallCapture" -> {
                        if (speakerphoneService == null) {
                            speakerphoneService = SpeakerphoneAudioService.getInstance()
                        }
                        val started = speakerphoneService?.startCapture() ?: false
                        result.success(started)
                    }
                    "stopCallCapture" -> {
                        speakerphoneService?.stopCapture()
                        result.success(true)
                    }
                    "isCallCaptureActive" -> {
                        result.success(speakerphoneService?.isCapturing() ?: false)
                    }
                    "setSpeakerphone" -> {
                        val on = call.argument<Boolean>("on") ?: false
                        try {
                            val am = getSystemService(AUDIO_SERVICE) as android.media.AudioManager
                            am.isSpeakerphoneOn = on
                            result.success(true)
                        } catch (e: Exception) {
                            result.error("AUDIO_ERROR", e.message, null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onDestroy() {
        speakerphoneService?.stopCapture()
        stopService(Intent(this, SpeakerphoneAudioService::class.java))
        super.onDestroy()
    }

    private fun emitFromIntent(intent: Intent?) {
        val state = intent?.getStringExtra(CallMonitorService.EXTRA_STATE) ?: return
        val number = intent.getStringExtra(CallMonitorService.EXTRA_NUMBER)
        PhoneCallEmitter.emit(state, number)
    }

    private fun startMonitor() {
        if (tracker == null) {
            tracker = PhoneCallTracker(this).also { it.start() }
        }
        val service = Intent(this, CallMonitorService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(service)
        } else {
            startService(service)
        }
    }

    private fun stopMonitor() {
        tracker?.stop()
        tracker = null
        stopService(Intent(this, CallMonitorService::class.java))
    }
}
