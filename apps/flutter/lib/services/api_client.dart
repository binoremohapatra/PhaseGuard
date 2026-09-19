import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/protocol.dart';

/// Same production host the React Native client uses.

/// Same production host the React Native client uses.
class ApiClient {
  ApiClient({this.baseUrl = 'https://phaseguard.onrender.com'});

  final String baseUrl;

  Map<String, String> _headers({String? token}) => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  /// Health check to keep the backend alive and check connectivity
  Future<bool> healthCheck() async {
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/health'),
        headers: _headers(),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => http.Response('Timeout', 408),
      );
      return res.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<CallInitResult> initCall() async {
    final res = await http.post(
      Uri.parse('$baseUrl/call/init'),
      headers: _headers(),
      body: jsonEncode({'ingestion_mode': 'browser_mic'}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException('Call init failed (${res.statusCode})');
    }
    return CallInitResult.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<EscalationDraft> draftEscalation({
    required String callId,
    required String token,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/call/$callId/escalate/draft'),
      headers: _headers(token: token),
      body: jsonEncode({'format': 'webhook'}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Draft escalation failed');
    }
    return EscalationDraft.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> confirmEscalation({
    required String callId,
    required String token,
    required String draftId,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/call/$callId/escalate/confirm'),
      headers: _headers(token: token),
      body: jsonEncode({'draft_id': draftId}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Confirm escalation failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<CallStatus> getCallStatus({
    required String callId,
    required String token,
  }) async {
    final res = await http.get(
      Uri.parse('$baseUrl/call/$callId/status'),
      headers: _headers(token: token),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Status fetch failed');
    }
    return CallStatus.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// Rewrite init `ws_url` (often an internal host) onto the public WSS origin.
  String websocketUrl(CallInitResult init) {
    return '$baseUrl/ws/call/${init.callId}?token=${Uri.encodeQueryComponent(init.token)}'
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
  }

  /// Upload a video frame for forensic analysis
  Future<Map<String, dynamic>> uploadFrame({
    required String callId,
    required String token,
    required List<int> frameBytes,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/call/$callId/frame'),
      headers: _headers(token: token),
      body: frameBytes,
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Frame upload failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Activate AI scambaiter for the call
  Future<Map<String, dynamic>> activateScambaiter({
    required String callId,
    required String token,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/call/$callId/scambait'),
      headers: _headers(token: token),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Scambaiter activation failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Download forensic PDF dossier for a call
  Future<List<int>> getDossier({
    required String callId,
    required String token,
  }) async {
    final res = await http.get(
      Uri.parse('$baseUrl/call/$callId/dossier'),
      headers: _headers(token: token),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Dossier download failed');
    }
    return res.bodyBytes;
  }

  /// Get call history with optional limit
  Future<List<Map<String, dynamic>>> getCallHistory({
    required String token,
    int limit = 50,
  }) async {
    final res = await http.get(
      Uri.parse('$baseUrl/calls/history?limit=$limit'),
      headers: _headers(token: token),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Call history fetch failed');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final data = body['data'];
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  /// Continue monitoring a call
  Future<Map<String, dynamic>> continueMonitoring({
    required String callId,
    required String token,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/calls/$callId/monitor'),
      headers: _headers(token: token),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Continue monitoring failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Block and report a call (when endpoint is available)
  /// Currently not on API, but leaving stub for future use
  Future<Map<String, dynamic>> blockAndReport({
    required String callId,
    required String token,
    required String reason,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/calls/$callId/block-report'),
      headers: _headers(token: token),
      body: jsonEncode({'reason': reason}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Block and report failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ── Voice/TTS API Methods ─────────────────────────────────────────────────────

  /// Enroll a voice sample for cloning
  Future<Map<String, dynamic>> enrollVoice({
    required String displayName,
    required List<int> audioBytes,
    String fileName = 'voice_sample.wav',
    bool enhanceQuality = true,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/v1/voice/enroll'));
    request.files.add(http.MultipartFile.fromBytes(
      'audio',
      audioBytes,
      filename: fileName,
    ));
    request.fields['display_name'] = displayName;
    request.fields['enhance_quality'] = enhanceQuality.toString();

    final res = await request.send();
    final body = await res.stream.bytesToString();

    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detailFromJson(body) ?? 'Voice enrollment failed');
    }
    return jsonDecode(body) as Map<String, dynamic>;
  }

  /// Synthesize text to speech
  Future<List<int>> synthesize({
    required String text,
    String? voiceId,
    String format = 'mp3',
    String provider = 'auto',
  }) async {
    final body = <String, dynamic>{
      'text': text,
      'format': format,
      'provider': provider,
    };
    if (voiceId != null) {
      body['voice_id'] = voiceId;
    }

    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/voice/tts'),
      headers: _headers(),
      body: jsonEncode(body),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'TTS synthesis failed');
    }
    return res.bodyBytes;
  }

  /// Stream text to speech
  Future<http.StreamedResponse> streamVoice({
    required String text,
    String? voiceId,
    String format = 'mp3',
    String provider = 'auto',
  }) async {
    final body = <String, dynamic>{
      'text': text,
      'format': format,
      'provider': provider,
    };
    if (voiceId != null) {
      body['voice_id'] = voiceId;
    }

    final request = http.Request('POST', Uri.parse('$baseUrl/api/v1/voice/stream'))
      ..headers.addAll(_headers())
      ..body = jsonEncode(body);

    final res = await request.send();
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException('Voice streaming failed: ${res.statusCode}');
    }
    return res;
  }

  /// List enrolled voice profiles
  Future<List<Map<String, dynamic>>> listVoices() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/voice/voices'),
      headers: _headers(),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'List voices failed');
    }
    final body = jsonDecode(res.body) as List;
    return body.cast<Map<String, dynamic>>();
  }

  /// Delete a voice profile
  Future<Map<String, dynamic>> deleteVoice({
    required String voiceId,
  }) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/api/v1/voice/voices/$voiceId'),
      headers: _headers(),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Delete voice failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Check voice service health
  Future<Map<String, dynamic>> voiceHealthCheck() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/voice/health'),
      headers: _headers(),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Voice health check failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ── Multi-Detector Fallback API Methods ───────────────────────────────────────

  /// Detect if audio is synthetic/real using multi-detector fallback
  /// Fallback chain: Vocalyx → final-voice-deepfake → VoiceGuard Pro → VoiceShield Local
  Future<Map<String, dynamic>> detectAudio({
    required List<int> audioBytes,
    String fileName = 'audio.wav',
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/api/v1/multi-detector/detect'),
    );
    request.files.add(http.MultipartFile.fromBytes(
      'file',
      audioBytes,
      filename: fileName,
    ));

    final res = await request.send();
    final body = await res.stream.bytesToString();

    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detailFromJson(body) ?? 'Multi-detector detection failed');
    }
    return jsonDecode(body) as Map<String, dynamic>;
  }

  /// Detect if audio is synthetic/real from bytes directly
  Future<Map<String, dynamic>> detectAudioBytes({
    required List<int> audioBytes,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/multi-detector/detect/bytes'),
      headers: _headers(),
      body: audioBytes,
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Multi-detector detection from bytes failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Get availability status of all detectors
  Future<Map<String, dynamic>> getDetectorStatus() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/multi-detector/status'),
      headers: _headers(),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Detector status check failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Get information about available detectors
  Future<Map<String, dynamic>> getDetectorInfo() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/multi-detector/info'),
      headers: _headers(),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(_detail(res) ?? 'Detector info fetch failed');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  String? _detail(http.Response res) {
    try {
      final body = jsonDecode(res.body);
      if (body is Map && body['detail'] != null) {
        return body['detail'].toString();
      }
    } catch (_) {}
    return null;
  }

  String? _detailFromJson(String body) {
    try {
      final json = jsonDecode(body);
      if (json is Map && json['detail'] != null) {
        return json['detail'].toString();
      }
    } catch (_) {}
    return null;
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
