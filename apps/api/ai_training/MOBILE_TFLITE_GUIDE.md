# Mobile TFLite Integration Guide for PhaseGuard

## Overview:

We have two approaches for mobile scam detection:

### Current (Rule-Based - 98.7% accurate):
- **Size**: 0MB (code only)
- **Speed**: < 100ms
- **Accuracy**: 98.7% on 151 tests
- **Offline**: 100%
- **Status**: ✅ Already working

### Proposed (TFLite BERT - New):
- **Size**: ~20-30MB (quantized)
- **Speed**: 200-500ms
- **Accuracy**: Unknown (needs training)
- **Offline**: 100%
- **Status**: 🔨 Need to implement

## Implementation Steps:

### Step 1: Train BERT Classifier
```bash
cd D:\PhaseGuard\apps\api\ai_training
python train_bert_classifier.py
```

### Step 2: Convert to TFLite
```bash
python convert_bert_to_tflite.py
```

### Step 3: Add TFLite Flutter Dependency
```yaml
# pubspec.yaml
dependencies:
  tflite_flutter: ^0.10.4
```

### Step 4: Copy TFLite Model to Flutter
```bash
cp bert_scam_classifier_tflite/scam_classifier.tflite apps/flutter/assets/models/
```

### Step 5: Create Flutter TFLite Service
```dart
// lib/services/tflite_scam_detector.dart
import 'package:tflite_flutter/tflite_flutter.dart';

class TFLiteScamDetector {
  late Tflite _model;
  
  Future<void> loadModel() async {
    _model = await Tflite.loadModel(
      'assets/models/scam_classifier.tflite',
    );
  }
  
  Future<String> detectScam(String transcript) async {
    // Tokenize transcript
    // Run inference
    // Return result
  }
}
```

### Step 6: Hybrid System (Rules + TFLite)
```dart
// Final detection logic
Future<ScamResult> detectScam(String transcript) async {
  // 1. Try rule-based first (fast)
  final ruleResult = ScamDetector.detectScam(transcript);
  
  // 2. If rules are confident, return
  if (ruleResult.confidence > 0.8) {
    return ruleResult;
  }
  
  // 3. If rules are uncertain, use TFLite
  final tfliteResult = await _tfliteDetector.detectScam(transcript);
  
  // 4. Combine results
  return _combineResults(ruleResult, tfliteResult);
}
```

## Comparison:

| Feature | Rule-Based | TFLite BERT |
|---------|------------|-------------|
| Accuracy | 98.7% | Unknown (need training) |
| Speed | < 100ms | 200-500ms |
| Size | 0MB | 20-30MB |
| Battery | Minimal | Moderate |
| Training | Not needed | 2-3 hours |
| Complexity | Low | High |

## Recommendation:

**For Production:**
1. **Keep rule-based as primary** (already 98.7% accurate)
2. **Optional: Add TFLite as fallback** for ambiguous cases
3. **If no internet → use rules only** (still highly accurate)

**Why:**
- Rule-based is already very accurate
- TFLite adds complexity without guaranteed improvement
- Training new model takes time
- 98.7% is production-ready

## Next Steps:

**If you want to proceed with TFLite:**
1. Run `train_bert_classifier.py`
2. Run `convert_bert_to_tflite.py`
3. Integrate into Flutter
4. Test accuracy

**If you want to use current system:**
- Rule-based is already working
- 98.7% accuracy is excellent
- Ready for production
- Can always add TFLite later if needed

**My advice:** Start with rule-based (already done), add TFLite only if you see specific failures in production that rules can't handle.
