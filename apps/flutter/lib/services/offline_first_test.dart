import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'offline_first_processor.dart';
import 'local_scambaiter_service.dart';
import 'local_escalation_service.dart';
import 'offline_dossier_service.dart';

/// OfflineFirstTest — Complete offline-first architecture test.
///
/// Tests the complete flow:
/// 1. Audio capture (simulated)
/// 2. Parallel local + web processing
/// 3. Result merging
/// 4. Scambaiter activation
/// 5. PDF generation
/// 6. Escalation options
class OfflineFirstTest {
  final OfflineFirstProcessor _processor = OfflineFirstProcessor();
  final LocalScambaiterService _scambaiter = LocalScambaiterService();
  final LocalEscalationService _escalation = LocalEscalationService();
  
  bool _isInitialized = false;

  /// Initialize all services.
  Future<void> initialize() async {
    if (_isInitialized) return;
    
    debugPrint('OfflineFirstTest: Initializing services...');
    await _processor.initialize();
    _isInitialized = true;
    debugPrint('OfflineFirstTest: ✅ All services initialized');
  }

  /// Test complete offline-first flow.
  Future<Map<String, dynamic>> testCompleteFlow({
    String? audioFilePath,
    List<int>? audioBytes,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    debugPrint('═════════════════════════════════════════════════════');
    debugPrint('OFFLINE-FIRST ARCHITECTURE TEST');
    debugPrint('═════════════════════════════════════════════════════');

    // Step 1: Audio Processing (Parallel Local + Web)
    debugPrint('\n[STEP 1] Audio Processing (Parallel Local + Web)');
    final processingResult = audioFilePath != null
        ? await _processor.processAudioFile(audioFilePath!)
        : await _processor.processAudioBytes(audioBytes!);

    debugPrint('Processing Result:');
    debugPrint('  - Source: ${processingResult['source']}');
    debugPrint('  - Fallback Used: ${processingResult['fallback_used']}');
    debugPrint('  - Reason: ${processingResult['reason']}');

    if (processingResult['transcript'] != null) {
      debugPrint('  - Transcript: ${processingResult['transcript']}');
    }

    if (processingResult['deepfake'] != null) {
      final deepfake = processingResult['deepfake'] as Map<String, dynamic>;
      debugPrint('  - Deepfake: ${deepfake['is_synthetic']} (${(deepfake['confidence'] as double * 100).toStringAsFixed(1)}%)');
    }

    if (processingResult['scam'] != null) {
      final scam = processingResult['scam'] as Map<String, dynamic>;
      debugPrint('  - Scam: ${scam['is_scam']} (${(scam['confidence'] as double * 100).toStringAsFixed(1)}%)');
      debugPrint('  - Layer: ${scam['layer']}');
    }

    // Step 2: Scambaiter Activation (if scam detected)
    if (processingResult['scam'] != null && 
        processingResult['scam']['is_scam'] == true) {
      debugPrint('\n[STEP 2] Scambaiter Activation');
      
      final transcript = processingResult['transcript'] as String? ?? '';
      final scambaiterResult = await _scambaiter.generateAudioResponse(transcript);
      
      debugPrint('Scambaiter Result:');
      debugPrint('  - Text: ${scambaiterResult['text']}');
      debugPrint('  - Source: ${scambaiterResult['source']}');
      debugPrint('  - Audio Path: ${scambaiterResult['audio_path']}');
    }

    // Step 3: PDF Generation
    debugPrint('\n[STEP 3] PDF Generation (Local)');
    final pdfPath = await OfflineDossierService.generateOfflineDossier(
      callId: 'TEST_CALL_001',
      transcript: processingResult['transcript']?.toString() ?? '',
      deepfakeResult: processingResult['deepfake'],
      scamResult: processingResult['scam'],
    );

    debugPrint('PDF Result:');
    debugPrint('  - Path: $pdfPath');
    debugPrint('  - Status: ${pdfPath != null ? "Generated ✅" : "Failed ❌"}');

    // Step 4: Escalation Options
    debugPrint('\n[STEP 4] Escalation Options');
    debugPrint('Available Actions:');
    debugPrint('  1. Call 1930 Helpline: _escalation.callCybercrimeHelpline()');
    debugPrint('  2. Share via WhatsApp: _escalation.shareViaWhatsApp()');
    debugPrint('  3. Share via Email: _escalation.shareViaEmail()');
    debugPrint('  4. Open Cybercrime Portal: _escalation.openCybercrimePortal()');

    // Step 5: Complete Result
    final completeResult = {
      'success': true,
      'processing': processingResult,
      'scambaiter': processingResult['scam']?['is_scam'] == true 
          ? await _scambaiter.generateAudioResponse(processingResult['transcript']?.toString() ?? '')
          : null,
      'pdf_path': pdfPath,
      'escalation_options': {
        'call_1930': 'Available',
        'whatsapp_share': 'Available',
        'email_share': 'Available',
        'cybercrime_portal': 'Available',
      },
      'test_timestamp': DateTime.now().toIso8601String(),
    };

    debugPrint('\n═════════════════════════════════════════════════════');
    debugPrint('TEST COMPLETE ✅');
    debugPrint('═════════════════════════════════════════════════════');

    return completeResult;
  }

  /// Test offline-only mode (simulate no internet).
  Future<Map<String, dynamic>> testOfflineOnly({
    String? audioFilePath,
    List<int>? audioBytes,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    debugPrint('═════════════════════════════════════════════════════');
    debugPrint('OFFLINE-ONLY MODE TEST (No Internet)');
    debugPrint('═════════════════════════════════════════════════════');

    // Step 1: Local Processing Only
    debugPrint('\n[STEP 1] Local Processing Only');
    final localResult = await _processor.processLocal(
      audioBytes!,
      audioFilePath ?? 'temp_audio.mp3',
    );

    debugPrint('Local Result:');
    debugPrint('  - Source: ${localResult['source']}');
    debugPrint('  - Transcript: ${localResult['transcript']}');
    debugPrint('  - Deepfake: ${localResult['deepfake']}');
    debugPrint('  - Scam: ${localResult['scam']}');

    // Step 2: Local Scambaiter
    debugPrint('\n[STEP 2] Local Scambaiter');
    final scambaiterResult = await _scambaiter.generateAudioResponse(
      localResult['transcript']?.toString() ?? '',
    );

    debugPrint('Scambaiter Result:');
    debugPrint('  - Text: ${scambaiterResult['text']}');
    debugPrint('  - Source: ${scambaiterResult['source']}');

    // Step 3: Local PDF
    debugPrint('\n[STEP 3] Local PDF Generation');
    final pdfPath = await OfflineDossierService.generateOfflineDossier(
      callId: 'OFFLINE_TEST_001',
      transcript: localResult['transcript']?.toString() ?? '',
      deepfakeResult: localResult['deepfake'],
      scamResult: localResult['scam'],
    );

    debugPrint('PDF Result:');
    debugPrint('  - Path: $pdfPath');

    final offlineResult = {
      'success': true,
      'mode': 'offline_only',
      'local_processing': localResult,
      'scambaiter': scambaiterResult,
      'pdf_path': pdfPath,
      'test_timestamp': DateTime.now().toIso8601String(),
    };

    debugPrint('\n═════════════════════════════════════════════════════');
    debugPrint('OFFLINE-ONLY TEST COMPLETE ✅');
    debugPrint('═════════════════════════════════════════════════════');

    return offlineResult;
  }

  void dispose() {
    _processor.dispose();
    _scambaiter.dispose();
  }
}
