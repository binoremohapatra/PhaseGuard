# Best Deepfake Detection Model - Recommendation Prompt

## 🎯 Prompt for AI/Research Assistant

**Copy this prompt and ask AI/research assistant:**

---

```
I am building PhaseGuard, an India-focused anti-scam/security application with Flutter/Android frontend and FastAPI backend. I need a deepfake audio detection model for real-time scam call detection.

## Current Requirements:
- **Use Case:** Real-time scam call detection in India
- **Platform:** Android mobile + Web backend
- **Input:** Audio from phone calls (3-6 seconds)
- **Output:** Deepfake detection (real vs synthetic)
- **Latency:** Must be fast (<100ms for web, <2s for mobile)
- **Accuracy:** Target 90%+ for production
- **Budget:** Prefer free/low-cost options
- **Privacy:** Local detection preferred when possible

## Current Models Tested:
1. **SpecRNet:** 33-67% accuracy, model limitation issue
2. **VoiceShield TFLite:** 90% expected (not tested due to Windows TFLite issue)
3. **DSP Features:** 33-67% accuracy, threshold dependent

## Technical Constraints:
- **Mobile:** TFLite preferred for Android
- **Web:** CPU-optimized models (no GPU requirement)
- **Input:** 16kHz mono audio
- **Languages:** Hindi + English
- **Training Data:** Indian voices preferred

## Available Options (from research):
1. **Modulate API:** 99% accuracy, $0.25/hr, web-only
2. **AI Voice Detector:** 99% accuracy, $0.50/1000 requests
3. **AuriginAPI:** 98%+ accuracy, <50ms latency
4. **RawNetLite:** Lightweight, TFLite ready
5. **Custom Training:** Own dataset training

## Questions:
1. Which model would be best for real-time scam call detection in India?
2. What are the trade-offs between accuracy, speed, and cost?
3. Should I use web API or local model for this use case?
4. Which model has been tested on Indian voice samples?
5. What is the current state-of-the-art for lightweight audio deepfake detection?
6. Are there any open-source models with 90%+ accuracy that work on CPU?
7. Should I invest in custom training or use existing models?
8. What preprocessing pipeline would you recommend for Indian languages?

Please provide specific model recommendations with pros/cons, expected accuracy, and implementation complexity.
```

---

## 🎯 Additional Context Questions

**If needed, also ask these follow-up questions:**

### **For Open-Source Models:**
```
Which open-source audio deepfake detection models have:
- TFLite/Mobile compatibility
- CPU-optimized inference
- 90%+ accuracy on real datasets
- Support for Indian languages
- Active maintenance and documentation
```

### **For Commercial APIs:**
```
Which commercial deepfake detection APIs offer:
- Real-time audio streaming
- Competitive pricing for startups
- Indian language support
- Fast latency (<100ms)
- Good documentation and support
```

### **For Hybrid Approach:**
```
How should I design a hybrid system:
- Local model for privacy + offline
- Web API for accuracy + speed
- Race condition for fastest result
- Fallback mechanisms
- Cost optimization
```

---

## 📋 Key Considerations for Recommendation

**Make sure the recommendation addresses:**
1. **Accuracy:** Real-world performance on scam call audio
2. **Speed:** Real-time latency requirements
3. **Cost:** Startup-friendly pricing
4. **Implementation:** Technical complexity
5. **Maintenance:** Long-term sustainability
6. **Privacy:** User data protection
7. **Localization:** Indian language support
8. **Reliability:** Consistent performance

---

## 🎯 Use This Prompt For:

1. **ChatGPT/Claude:** General model recommendations
2. **Hugging Face:** Find specific models on platform
3. **Research Papers:** Latest state-of-the-art models
4. **GitHub Issues:** Community recommendations
5. **Tech Communities:** Reddit/StackOverflow
6. **AI/ML Forums:** Expert opinions

---

## 💡 Expected Output Format

**Good recommendation should include:**
- **Model Name:** Specific model(s) to test
- **Accuracy:** Expected performance metrics
- **Latency:** Processing time expectations
- **Cost:** Pricing details
- **Implementation:** Complexity level
- **Pros/Cons:** Clear trade-offs
- **Testing Strategy:** How to validate performance
- **Alternatives:** Backup options

---

## 🚀 Next Steps After Recommendation

1. **Test top 2-3 recommended models**
2. **Compare against current baseline**
3. **Measure real-world performance**
4. **Evaluate cost vs accuracy trade-offs**
5. **Choose best model for production**
