import 'dart:async';

import 'package:flutter/services.dart';

/// Shizuku Audio Capture (Advanced/Experimental)
/// 
/// Uses Shizuku to run commands with shell UID 2000 privileges.
/// This can potentially access system-level audio paths not available to normal apps.
/// 
/// CRITICAL NOTES:
/// - REQUIRES Shizuku to be installed on the device
/// - REQUIRES wireless debugging to be enabled
/// - REQUIRES user to grant Shizuku permission to this app
/// - Complex setup process for users
/// - Device compatibility varies
/// - Marked as EXPERIMENTAL - may not work on all devices
class ShizukuCapture {
  static const MethodChannel _channel = MethodChannel('phaseguard/shizuku_audio');
  
  bool _isCapturing = false;
  bool _shizukuInstalled = false;
  bool _shizukuAvailable = false;
  bool _permissionGranted = false;
  bool _usingFallback = false;
  int _sampleRate = 16000;
  
  final StreamController<Map<String, dynamic>> _eventController = StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<List<int>> _audioController = StreamController<List<int>>.broadcast();
  
  Stream<Map<String, dynamic>> get eventStream => _eventController.stream;
  Stream<List<int>> get audioStream => _audioController.stream;
  
  bool get isCapturing => _isCapturing;
  bool get shizukuInstalled => _shizukuInstalled;
  bool get shizukuAvailable => _shizukuAvailable;
  bool get permissionGranted => _permissionGranted;
  bool get usingFallback => _usingFallback;
  int get sampleRate => _sampleRate;
  
  /// Check if Shizuku is installed and available
  Future<Map<String, dynamic>> getDeviceInfo() async {
    try {
      final result = await _channel.invokeMethod('getShizukuDeviceInfo');
      _shizukuInstalled = result['shizukuInstalled'] == true;
      _shizukuAvailable = result['shizukuAvailable'] == true;
      _permissionGranted = result['permissionGranted'] == true;
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'shizukuInstalled': false,
        'shizukuAvailable': false,
        'permissionGranted': false,
        'sdkVersion': 0,
        'androidVersion': 'Unknown',
        'error': e.toString(),
      };
    }
  }
  
  /// Request Shizuku permission
  Future<Map<String, dynamic>> requestPermission() async {
    try {
      final result = await _channel.invokeMethod('requestShizukuPermission');
      _permissionGranted = result['granted'] == true;
      _shizukuInstalled = result['installed'] == true;
      return Map<String, dynamic>.from(result);
    } catch (e) {
      return {
        'granted': false,
        'installed': false,
        'message': 'Error: $e',
      };
    }
  }
  
  /// Start Shizuku audio capture
  Future<bool> startCapture({int sampleRate = 16000}) async {
    try {
      _sampleRate = sampleRate;
      final result = await _channel.invokeMethod('startShizukuCapture', {
        'sampleRate': sampleRate,
      });
      
      if (result == true) {
        _isCapturing = true;
        startListening();
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
  
  /// Stop Shizuku audio capture
  Future<bool> stopCapture() async {
    try {
      final result = await _channel.invokeMethod('stopShizukuCapture');
      _isCapturing = false;
      _usingFallback = false;
      stopListening();
      return result == true;
    } catch (e) {
      return false;
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
  
  Future<dynamic> _handleMethodCall(MethodCall call) async {
    switch (call.method) {
      case 'shizukuCaptureStarted':
        _isCapturing = true;
        _sampleRate = call.arguments['sampleRate'] ?? 16000;
        _usingFallback = call.arguments['fallback'] == true;
        _eventController.add({
          'type': 'shizukuCaptureStarted',
          'sampleRate': _sampleRate,
          'fallback': _usingFallback,
        });
        break;
      case 'shizukuCaptureStopped':
        _isCapturing = false;
        _usingFallback = false;
        _eventController.add({
          'type': 'shizukuCaptureStopped',
        });
        break;
      case 'shizukuCaptureFailed':
        _isCapturing = false;
        _eventController.add({
          'type': 'shizukuCaptureFailed',
          'error': call.arguments['error'],
        });
        break;
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