import 'package:flutter/material.dart';
import '../services/scam_detector.dart';
import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';

class LocalScamDetectionScreen extends StatefulWidget {
  const LocalScamDetectionScreen({super.key});

  @override
  State<LocalScamDetectionScreen> createState() => _LocalScamDetectionScreenState();
}

class _LocalScamDetectionScreenState extends State<LocalScamDetectionScreen> {
  final TextEditingController _transcriptController = TextEditingController();
  ScamResult? _lastResult;
  bool _isAnalyzing = false;

  void _analyzeTranscript() {
    if (_transcriptController.text.trim().isEmpty) {
      return;
    }

    setState(() {
      _isAnalyzing = true;
    });

    // Simulate brief processing time
    Future.delayed(const Duration(milliseconds: 100), () {
      final result = ScamDetector.detectScam(_transcriptController.text);
      setState(() {
        _lastResult = result;
        _isAnalyzing = false;
      });
    });
  }

  void _testWithExample(String transcript) {
    _transcriptController.text = transcript;
    _analyzeTranscript();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Local Scam Detection'),
        backgroundColor: PgColors.primary,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: PgColors.screenGradient,
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(PgSpace.screenH),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionTitle('Transcript Analysis'),
                const SizedBox(height: PgSpace.m),
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _transcriptController,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          hintText: 'Enter call transcript here...',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: PgSpace.m),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isAnalyzing ? null : _analyzeTranscript,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: PgColors.primary,
                            foregroundColor: Colors.white,
                          ),
                          child: _isAnalyzing
                              ? const CircularProgressIndicator(color: Colors.white)
                              : const Text('Analyze'),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: PgSpace.l),
                const SectionTitle('Quick Test Examples'),
                const SizedBox(height: PgSpace.m),
                _buildExampleButton('RBI Scam',
                    'Hello this is calling from RBI. Your bank account has been linked to illegal transactions. Please transfer your money to our secure account immediately.'),
                _buildExampleButton('Legitimate Bank',
                    'Hello, this is calling from HDFC Bank customer service. We are calling to inform you about your new credit card benefits.'),
                _buildExampleButton('Family Emergency',
                    'Hello beta, this is your uncle speaking. I am in the hospital and need urgent money for surgery.'),
                _buildExampleButton('Insurance Reminder',
                    'Hello, this is from insurance company. Your health insurance premium is due next week. No urgency, you have time.'),
                const SizedBox(height: PgSpace.l),
                if (_lastResult != null) ...[
                  const SectionTitle('Analysis Result'),
                  const SizedBox(height: PgSpace.m),
                  GlassCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildResultRow('Classification',
                            _lastResult!.isScam ? 'SCAM DETECTED' : 'NORMAL',
                            _lastResult!.isScam ? Colors.red : Colors.green),
                        const SizedBox(height: PgSpace.s),
                        _buildResultRow('Category', _lastResult!.category, Colors.grey),
                        const SizedBox(height: PgSpace.s),
                        Text(
                          'Reasoning: ${_lastResult!.reasoning}',
                          style: const TextStyle(fontSize: 14),
                        ),
                        const SizedBox(height: PgSpace.m),
                        const Divider(),
                        const SizedBox(height: PgSpace.m),
                        _buildScoreRow('Scam Score', _lastResult!.scamScore, Colors.red),
                        _buildScoreRow('Legitimate Score', _lastResult!.legitimateScore, Colors.green),
                        _buildScoreRow('Negative Score', _lastResult!.negativeScore, Colors.blue),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: PgSpace.xl),
                const SectionTitle('System Information'),
                const SizedBox(height: PgSpace.m),
                GlassCard(
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '✓ Offline Mode Active',
                        style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: PgSpace.s),
                      Text(
                        '✓ No Internet Required',
                        style: TextStyle(color: Colors.green),
                      ),
                      SizedBox(height: PgSpace.s),
                      Text(
                        '✓ Local Keyword Analysis',
                        style: TextStyle(color: Colors.green),
                      ),
                      SizedBox(height: PgSpace.s),
                      Text(
                        '✓ Instant Detection',
                        style: TextStyle(color: Colors.green),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildExampleButton(String label, String transcript) {
    return Padding(
      padding: const EdgeInsets.only(bottom: PgSpace.s),
      child: SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: () => _testWithExample(transcript),
          style: OutlinedButton.styleFrom(
            foregroundColor: PgColors.primary,
          ),
          child: Text(label),
        ),
      ),
    );
  }

  Widget _buildResultRow(String label, String value, Color color) {
    return Row(
      children: [
        SizedBox(
          width: 120,
          child: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
        const SizedBox(width: PgSpace.s),
        Expanded(
          child: Text(
            value,
            style: TextStyle(color: color, fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }

  Widget _buildScoreRow(String label, int value, Color color) {
    return Row(
      children: [
        SizedBox(
          width: 120,
          child: Text(label),
        ),
        const SizedBox(width: PgSpace.s),
        Text(
          value.toString(),
          style: TextStyle(color: color, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  @override
  void dispose() {
    _transcriptController.dispose();
    super.dispose();
  }
}
