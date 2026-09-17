import 'dart:async';
import 'scam_detector.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class HybridScamDetector {
  static const String _baseUrl = 'http://192.168.1.100:8000'; // Backend URL
  static const int _timeoutMs = 5000; // 5 seconds for web fallback
  
  final ScamDetector _localDetector = ScamDetector();
  
  /// Main detection method - tries local model first, falls back to web
  Future<Map<String, dynamic>> detectScam(String transcript) async {
    // 1. Try local rule-based detection first (fast)
    final localResult = _localDetector.detectScam(transcript);
    
    // 2. If local is confident, return immediately
    if (localResult['isScam'] == true) {
      return {
        ...localResult,
        'source': 'local',
        'confidence': 0.9,
      };
    }
    
    // 3. If local is uncertain, try local model (if available)
    final localModelResult = await _tryLocalModel(transcript);
    if (localModelResult != null) {
      return {
        ...localModelResult,
        'source': 'local_model',
      };
    }
    
    // 4. If local model fails, try web API
    final webResult = await _tryWebApi(transcript);
    if (webResult != null) {
      return {
        ...webResult,
        'source': 'web',
      };
    }
    
    // 5. Fallback to local rules (conservative)
    return {
      ...localResult,
      'source': 'local_fallback',
      'reasoning': '${localResult['reasoning']} (web unavailable)',
    };
  }
  
  /// Try local model inference (placeholder for llama.cpp integration)
  Future<Map<String, dynamic>?> _tryLocalModel(String transcript) async {
    try {
      // TODO: Integrate llama.cpp model here
      // This would use llama_dart or flutter_llama package
      // For now, return null to use web fallback
      
      // Example implementation:
      // final model = LlamaModel.fromFile('assets/models/model.gguf');
      // final result = await model.generate(transcript);
      // return _parseModelResult(result);
      
      return null; // Not implemented yet
    } catch (e) {
      print('Local model error: $e');
      return null;
    }
  }
  
  /// Try web API fallback
  Future<Map<String, dynamic>?> _tryWebApi(String transcript) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/predict'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'transcript': transcript}),
          )
          .timeout(Duration(milliseconds: _timeoutMs));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'is_scam': data['is_scam'] ?? false,
          'category': data['category'] ?? 'UNKNOWN',
          'reasoning': data['reasoning'] ?? 'Web API prediction',
          'confidence': data['confidence'] ?? 0.5,
        };
      }
    } catch (e) {
      print('Web API error: $e');
    }
    return null;
  }
  
  /// Check if internet is available
  Future<bool> _hasInternet() async {
    try {
      final response = await http.get(Uri.parse('https://www.google.com'))
          .timeout(Duration(seconds: 3));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Get detection statistics
  Map<String, int> getStats() {
    return {
      'local_detection': 0,
      'local_model_detection': 0,
      'web_detection': 0,
      'fallback_detection': 0,
    };
  }
}