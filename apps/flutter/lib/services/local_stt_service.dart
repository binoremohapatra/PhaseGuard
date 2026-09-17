import 'dart:async';
import 'package:speech_to_text/speech_to_text.dart';

class LocalSttService {
  final SpeechToText _speechToText = SpeechToText();
  bool _isInitialized = false;
  
  final StreamController<String> _transcriptController = StreamController<String>.broadcast();
  Stream<String> get transcriptStream => _transcriptController.stream;

  bool get isListening => _speechToText.isListening;

  Future<bool> initialize() async {
    if (_isInitialized) return true;
    
    try {
      _isInitialized = await _speechToText.initialize(
        onError: (errorNotification) {
          print('LocalSTT Error: ${errorNotification.errorMsg}');
        },
        onStatus: (status) {
          print('LocalSTT Status: $status');
          // Auto-restart listening if it stops but we want it to keep going
          // Handling continuous listening can be tricky depending on OS limits
        },
      );
      return _isInitialized;
    } catch (e) {
      print('LocalSTT Init Exception: $e');
      return false;
    }
  }

  Future<void> startListening() async {
    if (!_isInitialized) {
      final success = await initialize();
      if (!success) return;
    }

    if (_speechToText.isListening) return;

    try {
      await _speechToText.listen(
        onResult: (result) {
          if (result.recognizedWords.isNotEmpty) {
            _transcriptController.add(result.recognizedWords);
          }
        },
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 3),
        partialResults: true,
        localeId: 'en_IN', // Assume Indian English for now
        cancelOnError: true,
        listenMode: ListenMode.dictation,
      );
    } catch (e) {
      print('LocalSTT Listen Exception: $e');
    }
  }

  Future<void> stopListening() async {
    if (_speechToText.isListening) {
      await _speechToText.stop();
    }
  }

  void dispose() {
    stopListening();
    _transcriptController.close();
  }
}
