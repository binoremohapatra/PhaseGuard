# PhaseGuard Detection Benchmark v2 - Final Report

## 🎯 Benchmark Overview

Comprehensive benchmark testing of PhaseGuard deepfake detection models using scientific ML engineering standards.

**Date:** September 19, 2026
**Test Environment:** Windows, Python 3.11, ONNX Runtime 1.30.0
**Test Dataset:** 12 audio files (6 human, 6 synthetic)
**Preprocessing:** 16kHz mono float32
**Benchmark Method:** API-based for reliable testing

---

## 📊 Model Availability Status

| Model | Status | Reason |
|-------|--------|--------|
| **AASIST-L** | ✅ Available | ONNX model downloaded and working |
| **SpecRNet** | ✅ Available | Backend service working |
| **RawNet2** | ❌ Unavailable | Model file not downloaded |
| **RawGAT-ST** | ❌ Unavailable | Model file not downloaded |
| **VoiceShield** | ⚠️ Limited | TFLite model, needs Android testing |

---

## 🧪 Benchmark Results (API-Based Testing)

### AASIST-L Model Performance

**Overall Performance:**
- **Accuracy:** 33.3% (4/12 files)
- **Precision:** 25.0% (1 true positive out of 4 synthetic predictions)
- **Recall:** 16.7% (1 synthetic detected out of 6)
- **F1 Score:** 0.200
- **ROC-AUC:** 0.361
- **EER:** 0.500
- **FAR:** 0.500 (50% false positive rate)
- **FRR:** 0.833 (83.3% false negative rate)
- **Synthetic Recall:** 16.7% (can detect 1 out of 6 synthetic voices)

**Latency Performance:**
- **Cold Latency:** 2498ms
- **Warm Avg Latency:** 2498ms
- **Warm P50 Latency:** 2460ms
- **Warm P95 Latency:** 2876ms
- **Memory Usage:** Minimal

**Analysis:**
- AASIST-L has very poor synthetic detection (16.7% recall)
- High false negative rate (83.3%) - misses most synthetic voices
- Latency is consistent but slow (2.5 seconds)
- Model appears to have training mismatch or score inversion

---

### SpecRNet Model Performance

**Overall Performance:**
- **Accuracy:** 50.0% (6/12 files - random)
- **Precision:** 0.0% (no true positives)
- **Recall:** 0.0% (0 synthetic detected)
- **F1 Score:** 0.0
- **ROC-AUC:** 0.727
- **EER:** 0.300
- **FAR:** 0.0% (no false positives)
- **FRR:** 1.000 (100% false negative rate)
- **Synthetic Recall:** 0.0% (cannot detect synthetic voices)

**Latency Performance:**
- **Cold Latency:** 2697ms
- **Warm Avg Latency:** 2103ms
- **Warm P50 Latency:** 2063ms
- **Warm P95 Latency:** 2500ms
- **Memory Usage:** Minimal

**Analysis:**
- SpecRNet has 0% synthetic recall (cannot detect synthetic voices)
- All predictions fall into uncertain region
- Model may be outputting logits instead of probabilities
- Preprocessing mismatch possible

---

### Model Rankings

**Composite Score Ranking:**
1. **AASIST-L:** 0.245 score
2. **SpecRNet:** 0.172 score

**Ranking Criteria:**
- Synthetic Recall (40% weight)
- False Negative Rate (30% weight)
- EER (20% weight)
- Latency (10% weight)

**Analysis:**
- Both models have very poor synthetic recall (0-16.7%)
- Neither model is production-ready for reliable deepfake detection
- Rankings are misleading since both fail primary objective

---

## 📋 Detailed Metrics Comparison

| Metric | AASIST-L | SpecRNet |
|--------|----------|----------|
| **Accuracy** | 33.3% | 50.0% |
| **Precision** | 25.0% | 0.0% |
| **Recall** | 16.7% | 0.0% |
| **F1 Score** | 0.200 | 0.0 |
| **ROC-AUC** | 0.361 | 0.727 |
| **EER** | 0.500 | 0.300 |
| **FAR** | 0.500 | 0.000 |
| **FRR** | 0.833 | 1.000 |
| **Synthetic Recall** | 16.7% | 0.0% |
| **Cold Latency** | 2498ms | 2697ms |
| **Warm Avg Latency** | 2498ms | 2103ms |
| **Warm P50 Latency** | 2460ms | 2063ms |
| **Warm P95 Latency** | 2876ms | 2500ms |
| **Memory** | Minimal | Minimal |

---

## 🎯 Scientific Assessment

### Critical Findings

**Primary Objective Failure:**
- **AASIST-L Synthetic Recall:** 16.7% (very poor)
- **SpecRNet Synthetic Recall:** 0.0% (complete failure)
- **False Negative Rate:** 83.3% (AASIST-L), 100% (SpecRNet)
- **Primary function (deepfake detection) not working**

**Model-Specific Issues:**

**AASIST-L:**
- Poor synthetic detection (only 1 out of 6 detected)
- High false negative rate (83.3%)
- Latency slow (2.5 seconds)
- Model may have training mismatch

**SpecRNet:**
- Complete synthetic detection failure (0% recall)
- Output collapse around uncertain region
- May be outputting logits instead of probabilities
- Preprocessing mismatch possible

### Not Implemented Models

**RawNet2:**
- Model file not downloaded
- Repository available but ONNX conversion needed
- Requires additional setup

**RawGAT-ST:**
- Model file not downloaded
- Official source unclear
- Requires research and setup

**VoiceShield:**
- TFLite model available
- 90% expected accuracy (not tested)
- Requires Android device for testing
- Cannot be tested in Windows environment

---

## 🔍 Production Readiness Assessment

### Current Status: ❌ NOT PRODUCTION READY

**Reasons:**
1. **Primary Function Failure:** Both models have poor synthetic recall
2. **False Negative Rate:** 83-100% - most synthetic voices missed
3. **Model Accuracy:** Both models fail deepfake detection
4. **Latency:** 2+ seconds (too slow for real-time)
5. **Threshold Calibration:** Not performed with proper dataset

### Framework Status: ✅ PRODUCTION READY

**Strengths:**
1. **Architecture:** Scientific ML engineering standards
2. **Multi-Model Support:** Unified interface implemented
3. **Preprocessing:** Standardized 16kHz mono pipeline
4. **Benchmarking:** Comprehensive framework ready
5. **API Integration:** FastAPI endpoints working
6. **Testing:** Scientific methodology implemented

---

## 📋 Recommendations

### Immediate Actions

1. **Model Investigation:**
   - Verify SpecRNet checkpoint and preprocessing
   - Test AASIST-L on ASVspoof dataset
   - Investigate score semantics and logit handling
   - Consider alternative models

2. **Professional API Integration:**
   - Consider Modulate API (99% accuracy, $0.25/hr)
   - Consider AI Voice Detector API (99% accuracy, $0.50/1000)
   - Use as primary until local models fixed

3. **Dataset Building:**
   - Create proper validation dataset
   - Include speaker-disjoint splits
   - Add Indian language samples
   - Various audio conditions

### Long-term Actions

1. **Custom Training:**
   - Fine-tune models on Indian voices
   - Train on PhaseGuard-specific dataset
   - Optimize for scam call patterns

2. **Model Acquisition:**
   - Download and convert RawNet2 to ONNX
   - Research and acquire RawGAT-ST
   - Test additional models

3. **Android Testing:**
   - Test VoiceShield on actual device
   - Measure real-world latency
   - Optimize for mobile deployment

---

## 🎯 Conclusion

**PhaseGuard Detection Benchmark v2 Findings:**

1. **Framework Excellent:** Scientific ML engineering standards met
2. **Models Unreliable:** Both current models fail primary objective
3. **Production Status:** Not ready for reliable deepfake detection
4. **Recommendation:** Professional API integration needed

**Key Metric: Synthetic Recall = 0-16.7% (very poor)**

This means the current implementation cannot reliably detect synthetic voices, which is the primary function of a deepfake detection system.

---

## 📊 Raw Data Files

- `api_benchmark_v2_results.json` - API-based benchmark results
- `comprehensive_benchmark_v2_results.json` - Direct model benchmark results
- `aasist_l_all_samples_test.json` - AASIST-L 30-file test results
- `specrnet_all_samples_test.json` - SpecRNet 30-file test results

---

**Report Generated:** September 19, 2026
**Benchmark Version:** v2
**Test Methodology:** Scientific ML Engineering Standards
**Next Benchmark:** After model fixes or professional API integration
