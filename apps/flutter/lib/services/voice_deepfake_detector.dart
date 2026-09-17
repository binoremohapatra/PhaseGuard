import 'dart:typed_data';
import 'dart:math';
import 'package:fftea/fftea.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

class VoiceDeepfakeDetector {
  final int sampleRate;
  Interpreter? _interpreter;
  bool _isInitialized = false;

  VoiceDeepfakeDetector({this.sampleRate = 16000});

  Future<void> init() async {
    if (_isInitialized) return;
    try {
      _interpreter = await Interpreter.fromAsset('assets/models/deepfake_detector.tflite');
      _isInitialized = true;
      print("Deepfake TFLite 2D CNN model loaded successfully.");
    } catch (e) {
      print("Failed to load Deepfake TFLite model: $e");
    }
  }

  /// Analyzes an audio buffer using Spectrogram extraction + 2D CNN
  Map<String, dynamic> analyzeAudioBuffer(Int16List pcmData) {
    if (!_isInitialized || _interpreter == null) {
      init();
      return {'is_synthetic': false, 'confidence': 0.0, 'reason': 'Model loading...'};
    }

    if (pcmData.isEmpty) {
      return {'is_synthetic': false, 'confidence': 0.0, 'reason': 'Empty buffer'};
    }

    try {
      int targetSamples = 16000;
      Float64List audio = Float64List(targetSamples);
      for (int i = 0; i < targetSamples; i++) {
        audio[i] = i < pcmData.length ? pcmData[i] / 32768.0 : 0.0;
      }

      int nFft = 256;
      int hopLength = 128;
      int numFrames = 124; // (16000 - 256) / 128 + 1
      int numBins = 129;   // 256 / 2 + 1

      // 1. Calculate STFT (Spectrogram)
      final fft = FFT(nFft);
      List<List<double>> spectrogram = List.generate(numFrames, (_) => List.filled(numBins, 0.0));
      
      double maxDb = -double.infinity;
      double minDb = double.infinity;

      for (int f = 0; f < numFrames; f++) {
        int start = f * hopLength;
        Float64List frame = Float64List(nFft);
        for (int i = 0; i < nFft; i++) {
          frame[i] = audio[start + i];
        }

        final freqDomain = fft.realFft(frame);
        
        for (int b = 0; b < numBins; b++) {
          double real = freqDomain[b].x;
          double imag = freqDomain[b].y;
          double mag = sqrt(real * real + imag * imag);
          
          // Convert to Decibels
          double db = 20 * (log(mag + 1e-10) / ln10);
          spectrogram[f][b] = db;
          
          if (db > maxDb) maxDb = db;
          if (db < minDb) minDb = db;
        }
      }

      // 2. Normalize to [0, 1]
      double range = maxDb - minDb;
      if (range < 1e-6) range = 1e-6;

      // 3. Flatten for TFLite [1, 124, 129, 1]
      Float32List flatInput = Float32List(numFrames * numBins);
      int idx = 0;
      for (int f = 0; f < numFrames; f++) {
        for (int b = 0; b < numBins; b++) {
          flatInput[idx++] = ((spectrogram[f][b] - minDb) / range);
        }
      }

      var input = flatInput.reshape([1, numFrames, numBins, 1]);
      var output = List.filled(1, List.filled(1, 0.0)).reshape([1, 1]);

      // 4. Run Neural Network Inference
      _interpreter!.run(input, output);
      double nnConfidence = output[0][0];

      // 5. Calculate DSP Heuristics (Coding Solution)
      int zeroFrames = 0;
      List<int> dominantBins = [];
      double silenceThreshold = 0.05; // -26dB equivalent roughly

      for (int f = 0; f < numFrames; f++) {
        double frameEnergy = 0.0;
        double maxMag = -1.0;
        int maxBin = 0;
        for (int b = 0; b < numBins; b++) {
          double val = (spectrogram[f][b] - minDb) / range;
          frameEnergy += val;
          if (val > maxMag) {
            maxMag = val;
            maxBin = b;
          }
        }
        if (frameEnergy / numBins < silenceThreshold) {
          zeroFrames++;
        } else {
          dominantBins.add(maxBin);
        }
      }

      double silenceRatio = zeroFrames / numFrames;
      
      // Calculate Pitch Variance (Jitter)
      double variance = 0.0;
      if (dominantBins.isNotEmpty) {
        double meanBin = dominantBins.reduce((a, b) => a + b) / dominantBins.length;
        double sumSq = 0.0;
        for (int b in dominantBins) {
          sumSq += (b - meanBin) * (b - meanBin);
        }
        variance = sumSq / dominantBins.length;
      }

      // Combine AI & DSP Logic
      // 1. Unnatural Pitch Stability (Robots don't have vocal cord micro-tremors)
      bool hasUnnaturalPitch = variance > 0.0 && variance < 8.0; 
      // 2. Unnatural Absolute Silence (Robots don't breathe)
      bool hasAbsoluteSilence = silenceRatio > 0.3;

      double finalConfidence = nnConfidence;
      if (nnConfidence > 0.35 && (hasUnnaturalPitch || hasAbsoluteSilence)) {
        finalConfidence = min(1.0, nnConfidence + 0.4); // Boost to Deepfake!
      } else if (variance > 25.0) {
        finalConfidence = max(0.0, nnConfidence - 0.3); // High natural jitter -> Human!
      }

      bool isSynthetic = finalConfidence >= 0.5;
      
      String reason = isSynthetic 
          ? "AI detected via Neural Network & DSP Acoustic Anomalies"
          : "Natural human vocal micro-tremors detected";

      return {
        'is_synthetic': isSynthetic,
        'confidence': finalConfidence,
        'reason': reason,
        'metrics': {
          'ai_score': nnConfidence,
          'pitch_variance': variance,
          'silence_ratio': silenceRatio
        }
      };
      
    } catch (e) {
      print("Error in Spectrogram TFLite inference: $e");
      return {'is_synthetic': false, 'confidence': 0.0, 'reason': 'Error analyzing audio'};
    }
  }
}
