import 'dart:typed_data';
import 'dart:math';
import 'package:fftea/fftea.dart';

class VoiceDeepfakeDetector {
  final int sampleRate;
  
  // History buffers for tracking temporal anomalies
  final List<double> _tremorHistory = [];
  final List<double> _phaseHistory = [];
  final List<double> _centroidHistory = [];
  final int _maxHistoryLength = 10;
  
  VoiceDeepfakeDetector({this.sampleRate = 16000});

  /// Analyzes an audio buffer to detect synthetic speech
  Map<String, dynamic> analyzeAudioBuffer(Int16List pcmData) {
    if (pcmData.isEmpty) {
      return {'is_synthetic': false, 'confidence': 0.0, 'reason': 'Empty buffer'};
    }

    try {
      // Convert Int16List to Float64List for FFT
      Float64List floatData = Float64List(pcmData.length);
      for (int i = 0; i < pcmData.length; i++) {
        floatData[i] = pcmData[i] / 32768.0;
      }

      int n = 1;
      while (n < floatData.length) n *= 2;
      
      Float64List paddedData = Float64List(n);
      paddedData.setAll(0, floatData);
      
      final fft = FFT(n);
      final freqDomain = fft.realFft(paddedData);

      // --- Enhanced DSP Analysis ---
      double lowFreqEnergy = 0.0;
      double totalEnergy = 0.0;
      double weightedFreqSum = 0.0;
      double phaseDispersion = 0.0;
      int phaseCount = 0;
      
      for (int i = 1; i < freqDomain.length; i++) {
        double realPart = freqDomain[i].x;
        double imagPart = freqDomain[i].y;
        double magnitude = sqrt(realPart * realPart + imagPart * imagPart);
        totalEnergy += magnitude;
        
        double freq = i * sampleRate / n;
        weightedFreqSum += freq * magnitude;
        
        if (freq >= 8.0 && freq <= 12.0) {
          lowFreqEnergy += magnitude;
        }
        
        // Phase dispersion (only for significant frequencies to avoid noise bias)
        if (magnitude > 0.01) {
          double prevReal = freqDomain[i-1].x;
          double prevImag = freqDomain[i-1].y;
          double prevPhase = atan2(prevImag, prevReal);
          
          double currPhase = atan2(imagPart, realPart);
          
          phaseDispersion += (currPhase - prevPhase).abs();
          phaseCount++;
        }
      }
      
      // Calculate instantaneous metrics
      double tremorScore = totalEnergy > 0 ? (lowFreqEnergy / totalEnergy) : 0;
      double avgPhaseDispersion = phaseCount > 0 ? (phaseDispersion / phaseCount) : 0;
      double spectralCentroid = totalEnergy > 0 ? (weightedFreqSum / totalEnergy) : 0;
      
      // Update temporal history
      _tremorHistory.add(tremorScore);
      _phaseHistory.add(avgPhaseDispersion);
      _centroidHistory.add(spectralCentroid);
      
      if (_tremorHistory.length > _maxHistoryLength) _tremorHistory.removeAt(0);
      if (_phaseHistory.length > _maxHistoryLength) _phaseHistory.removeAt(0);
      if (_centroidHistory.length > _maxHistoryLength) _centroidHistory.removeAt(0);

      // Average over time for stability
      double smoothedTremor = _tremorHistory.reduce((a, b) => a + b) / _tremorHistory.length;
      double smoothedPhase = _phaseHistory.reduce((a, b) => a + b) / _phaseHistory.length;

      // --- Scoring ---
      bool isSynthetic = false;
      double confidence = 0.0;
      String reason = "Human-like voice detected";

      // 1. Check for unnatural phase smoothness (Vocoder artifact)
      if (_phaseHistory.length >= 5 && smoothedPhase < 1.0) {
        isSynthetic = true;
        confidence = 0.90;
        reason = "Highly unnatural phase dispersion (Vocoder artifact detected)";
      } 
      // 2. Check for missing micro-tremors (TTS artifact)
      // ElevenLabs often falls around 0.00005-0.00008, while humans are usually > 0.00015
      else if (_tremorHistory.length >= 5 && smoothedTremor < 0.0001) {
        isSynthetic = true;
        confidence = 0.85;
        reason = "Missing neuromuscular micro-tremors (Advanced TTS artifact)";
      }
      // 3. Check spectral centroid anomalies (often low in muffled Deepfakes)
      else if (spectralCentroid > 0 && spectralCentroid < 500) {
        isSynthetic = true;
        confidence = 0.70;
        reason = "Abnormal spectral centroid (Muffled audio artifact)";
      }

      return {
        'is_synthetic': isSynthetic,
        'confidence': confidence,
        'reason': reason,
        'metrics': {
          'tremor_score': smoothedTremor,
          'phase_dispersion': smoothedPhase,
          'spectral_centroid': spectralCentroid
        }
      };
      
    } catch (e) {
      print("Error in voice DSP analysis: \$e");
      return {'is_synthetic': false, 'confidence': 0.0, 'reason': 'Error analyzing audio'};
    }
  }
}
