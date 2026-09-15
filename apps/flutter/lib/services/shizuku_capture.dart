import 'dart:async';

import 'package:flutter/services.dart';

/// UI State Machine for Shizuku
enum ShizukuState {
  notInstalled,
  notRunning,
  permissionNeeded,
  granted,
  active,
  captureFailing,
}

/// Shizuku Audio Capture - Voice Communication Capture Attempt
///
/// This attempts to capture voice call audio using Shizuku's elevated privileges
/// to access the hidden voiceCommunicationCaptureAllowed() method.
///
/// CRITICAL: This is experimental and ROM-dependent. It may not work on all devices.
/// Samsung/MIUI/OxygenOS are known to restrict audio routing more aggressively.
///
/// HARD TRUTH: If this implementation exists but produces silent buffers during a real call,
/// it is a FAILURE, not a "partial success." Only verified audible output counts as working.
///
/// UI State Machine:
/// - NOT_INSTALLED: Shizuku not installed on device
/// - NOT_RUNNING: Shizuku installed but not running
/// - PERMISSION_NEEDED: Shizuku running but permission not granted
/// - GRANTED: All permissions granted, ready to capture
/// - ACTIVE: Capture is running
/// - CAPTURE_FAILING: Capture running but producing silent buffers
class ShizukuCapture {
  static const MethodChannel _channel = MethodChannel('phaseguard/shizuku_audio');
  
  ShizukuState _currentState = ShizukuState.notInstalled;
  bool _isCapturing = false;
  int _sampleRate = 16000;
  
  // Device info
  String _manufacturer = '';
  String _model = '';
  String _androidVersion = '';
  int _sdkVersion = 0;
  
  // Audio stats for real test verification
  int _totalBytes = 0;
  int _nonZeroBytes = 0;
  double _nonZeroPercentage = 0.0;
  
  final StreamController<Map<String, dynamic>> _eventController = StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<List<int>> _audioController = StreamController<List<int>>.broadcast();
  
  Stream<Map<String, dynamic>> get eventStream => _eventController.stream;
  Stream<List<int>> get audioStream => _audioController.stream;
  
  ShizukuState get currentState => _currentState;
  bool get isCapturing => _isCapturing;
  int get sampleRate => _sampleRate;
  String get manufacturer => _manufacturer;
  String get model => _model;
  String get androidVersion => _androidVersion;
  int get sdkVersion => _sdkVersion;
  int get totalBytes => _totalBytes;
  int get nonZeroBytes => _nonZeroBytes;
  double get nonZeroPercentage => _nonZeroPercentage;
  
  /// Get current Shizuku state
  Future<Map<String, dynamic>> getShizukuState() async {
    try {
      final result = await _channel.invokeMethod('getShizukuState');
      _updateStateFromResult(result);
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'state': ShizukuState.notInstalled.name,
        'installed': false,
        'running': false,
        'permissionGranted': false,
        'error': e.toString(),
      };
    }
  }
  
  /// Request Shizuku permission
  Future<Map<String, dynamic>> requestPermission() async {
    try {
      final result = await _channel.invokeMethod('requestShizukuPermission');
      _updateStateFromResult(result);
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'granted': false,
        'state': ShizukuState.permissionNeeded.name,
        'message': 'Error: $e',
      };
    }
  }
  
  /// Start elevated capture attempt
  /// Requires MediaProjection permission result
  Future<Map<String, dynamic>> startElevatedCapture({
    required int resultCode,
    required Map<String, dynamic> data,
    int sampleRate = 16000,
  }) async {
    try {
      _sampleRate = sampleRate;
      _totalBytes = 0;
      _nonZeroBytes = 0;
      _nonZeroPercentage = 0.0;
      
      final result = await _channel.invokeMethod('startElevatedCapture', {
        'resultCode': resultCode,
        'data': data,
        'sampleRate': sampleRate,
      });
      
      if (result['success'] == true) {
        _isCapturing = true;
        _currentState = ShizukuState.active;
        startListening();
      }
      
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'success': false,
        'message': 'Error: $e',
      };
    }
  }
  
  /// Stop elevated capture
  Future<Map<String, dynamic>> stopElevatedCapture() async {
    try {
      final result = await _channel.invokeMethod('stopElevatedCapture');
      _isCapturing = false;
      stopListening();
      
      // Update stats from result
      if (result['totalBytes'] != null) {
        _totalBytes = result['totalBytes'];
        _nonZeroBytes = result['nonZeroBytes'];
        _nonZeroPercentage = result['nonZeroPercentage'] ?? 0.0;
        
        if (_nonZeroPercentage < 1.0) {
          _currentState = ShizukuState.captureFailing;
        } else {
          _currentState = ShizukuState.granted;
        }
      }
      
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'success': false,
        'message': 'Error: $e',
      };
    }
  }
  
  /// Run self-test to classify device capability
  Future<Map<String, dynamic>> runSelfTest() async {
    try {
      final result = await _channel.invokeMethod('runSelfTest');
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'classification': 'SHIZUKU_UNAVAILABLE',
        'message': 'Error: $e',
      };
    }
  }
  
  /// Start listening to Shizuku events
  void startListening() {
    _channel.setMethodCallHandler(_handleMethodCall);
  }
  
  /// Stop listening to Shizuku events
  void stopListening() {
    _channel.setMethodCallHandler(null);
  }
  
  void _updateStateFromResult(Map<String, dynamic> result) {
    final stateName = result['state'] as String?;
    if (stateName != null) {
      _currentState = ShizukuState.values.firstWhere(
        (e) => e.name == stateName,
        orElse: () => ShizukuState.notInstalled,
      );
    }
    
    _manufacturer = result['manufacturer'] ?? '';
    _model = result['model'] ?? '';
    _androidVersion = result['androidVersion'] ?? '';
    _sdkVersion = result['sdkVersion'] ?? 0;
  }
  
  Future<dynamic> _handleMethodCall(MethodCall call) async {
    switch (call.method) {
      case 'onShizukuAudioData':
        final List<int> audioData = List<int>.from(call.arguments['data']);
        _audioController.add(audioData);
        break;
    }
  }
  
  void dispose() {
    _eventController.close();
    _audioController.close();
    stopListening();
  }
}