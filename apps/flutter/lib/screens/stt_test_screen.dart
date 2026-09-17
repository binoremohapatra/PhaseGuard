import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/local_stt_service.dart';
import '../theme/tokens.dart';
import '../widgets/glass_card.dart';

/// SttTestScreen — Tests the on-device Local STT (Speech-to-Text) service.
///
/// Lets you tap a button, speak, and see the live transcript in real time.
/// Shows model status, available locales, and partial + final results.
class SttTestScreen extends StatefulWidget {
  const SttTestScreen({super.key});

  @override
  State<SttTestScreen> createState() => _SttTestScreenState();
}

class _SttTestScreenState extends State<SttTestScreen>
    with SingleTickerProviderStateMixin {
  final LocalSttService _stt = LocalSttService();

  bool _isInitialized = false;
  bool _isListening = false;
  String _statusMessage = 'Initializing...';
  String _liveTranscript = '';
  final List<String> _transcriptHistory = [];
  List<String> _availableLocales = [];
  String _selectedLocale = 'hi_IN';
  StreamSubscription<String>? _transcriptSub;

  // For the pulsing mic animation
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );
    _initStt();
  }

  Future<void> _initStt() async {
    setState(() => _statusMessage = 'Initializing STT engine...');

    final ok = await _stt.initialize();

    if (ok) {
      final locales = await _stt.getAvailableLocales();
      setState(() {
        _isInitialized = true;
        _statusMessage = '✅ STT Ready — tap mic to test';
        _availableLocales = locales.map((l) => l.localeId).toList();
        // Default to Hindi if available, else first
        if (!_availableLocales.contains(_selectedLocale) &&
            _availableLocales.isNotEmpty) {
          _selectedLocale = _availableLocales.first;
        }
      });
    } else {
      setState(() {
        _isInitialized = false;
        _statusMessage = '❌ STT not available on this device';
      });
    }
  }

  Future<void> _toggleListening() async {
    if (_isListening) {
      await _stt.stopListening();
      _pulseController.stop();
      _pulseController.reset();
      setState(() => _isListening = false);

      // Save to history if there's something
      if (_liveTranscript.trim().isNotEmpty) {
        setState(() {
          _transcriptHistory.insert(0, _liveTranscript.trim());
          _liveTranscript = '';
        });
      }
    } else {
      setState(() {
        _liveTranscript = '';
        _isListening = true;
        _statusMessage = '🎙️ Listening... (speak now)';
      });

      _pulseController.repeat(reverse: true);

      _transcriptSub?.cancel();
      _transcriptSub = _stt.transcriptStream.listen((text) {
        if (mounted) {
          setState(() => _liveTranscript = text);
        }
      });

      await _stt.startListening(localeId: _selectedLocale);
    }
  }

  @override
  void dispose() {
    _transcriptSub?.cancel();
    _stt.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PgColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: PgColors.bgSecondary,
        title: const Text(
          '🎙️ Local STT Test',
          style: TextStyle(
            color: PgColors.lightBlue,
            fontWeight: FontWeight.bold,
          ),
        ),
        iconTheme: const IconThemeData(color: PgColors.lightBlue),
        elevation: 0,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [PgColors.bgPrimary, PgColors.screenBottom],
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
                // ── Status Banner ──────────────────────────────────────────
                _buildStatusBanner().animate().fadeIn(duration: 400.ms),

                const SizedBox(height: PgSpace.l),

                // ── Locale Selector ────────────────────────────────────────
                if (_isInitialized && _availableLocales.isNotEmpty) ...[
                  _buildLocaleSelector()
                      .animate()
                      .fadeIn(duration: 400.ms, delay: 100.ms),
                  const SizedBox(height: PgSpace.l),
                ],

                // ── Big Mic Button ─────────────────────────────────────────
                _buildMicButton().animate().scale(
                      duration: 500.ms,
                      delay: 200.ms,
                      curve: Curves.elasticOut,
                    ),

                const SizedBox(height: PgSpace.l),

                // ── Live Transcript Box ────────────────────────────────────
                _buildLiveTranscriptBox()
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 300.ms),

                const SizedBox(height: PgSpace.l),

                // ── History ────────────────────────────────────────────────
                if (_transcriptHistory.isNotEmpty) ...[
                  const _SectionLabel('📝 Transcript History'),
                  const SizedBox(height: PgSpace.s),
                  ..._transcriptHistory
                      .asMap()
                      .entries
                      .map(
                        (e) => _buildHistoryItem(e.key + 1, e.value)
                            .animate()
                            .fadeIn(duration: 300.ms),
                      ),
                ],

                const SizedBox(height: 80),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBanner() {
    final isOk = _isInitialized;
    return GlassCard(
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: isOk ? PgColors.safe : PgColors.crit,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: isOk ? PgColors.safeGlow : PgColors.criticalGlow,
                  blurRadius: 8,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
          const SizedBox(width: PgSpace.m),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'speech_to_text (on-device)',
                  style: TextStyle(
                    color: PgColors.mediumBlue,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  _statusMessage,
                  style: TextStyle(
                    color: isOk ? PgColors.safe : PgColors.crit,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          if (!_isInitialized)
            TextButton(
              onPressed: _initStt,
              child: const Text('Retry',
                  style: TextStyle(color: PgColors.accentBlue)),
            ),
        ],
      ),
    );
  }

  Widget _buildLocaleSelector() {
    return GlassCard(
      child: Row(
        children: [
          const Text(
            'Language:',
            style: TextStyle(
              color: PgColors.lightBlue,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(width: PgSpace.m),
          Expanded(
            child: DropdownButton<String>(
              value: _availableLocales.contains(_selectedLocale)
                  ? _selectedLocale
                  : (_availableLocales.isNotEmpty
                      ? _availableLocales.first
                      : null),
              dropdownColor: PgColors.bgSecondary,
              isExpanded: true,
              underline: const SizedBox.shrink(),
              style: const TextStyle(color: PgColors.lightBlue),
              items: _availableLocales
                  .map(
                    (l) => DropdownMenuItem(
                      value: l,
                      child: Text(
                        l,
                        style: const TextStyle(
                            color: PgColors.lightBlue, fontSize: 13),
                      ),
                    ),
                  )
                  .toList(),
              onChanged: _isListening
                  ? null
                  : (v) => setState(() => _selectedLocale = v ?? _selectedLocale),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMicButton() {
    return Center(
      child: GestureDetector(
        onTap: _isInitialized ? _toggleListening : null,
        child: AnimatedBuilder(
          animation: _pulseController,
          builder: (context, child) {
            final scale = _isListening
                ? 1.0 + (_pulseController.value * 0.12)
                : 1.0;
            final glowRadius = _isListening
                ? 20.0 + (_pulseController.value * 30.0)
                : 0.0;
            return Transform.scale(
              scale: scale,
              child: Container(
                width: 110,
                height: 110,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isListening
                      ? PgColors.crit.withOpacity(0.15)
                      : PgColors.accentBlue.withOpacity(0.15),
                  border: Border.all(
                    color: _isListening ? PgColors.crit : PgColors.accentBlue,
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _isListening
                          ? PgColors.crit.withOpacity(0.4)
                          : PgColors.accentBlue.withOpacity(0.3),
                      blurRadius: glowRadius,
                      spreadRadius: _isListening ? 4 : 0,
                    ),
                  ],
                ),
                child: Icon(
                  _isListening ? Icons.stop_rounded : Icons.mic_rounded,
                  size: 48,
                  color: _isListening ? PgColors.crit : PgColors.lightBlue,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildLiveTranscriptBox() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                '🔤 Live Transcript',
                style: TextStyle(
                  color: PgColors.mediumBlue,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
              const Spacer(),
              if (_liveTranscript.isNotEmpty)
                GestureDetector(
                  onTap: () => setState(() => _liveTranscript = ''),
                  child: const Icon(Icons.clear, size: 16, color: PgColors.mediumBlue),
                ),
            ],
          ),
          const SizedBox(height: PgSpace.s),
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(minHeight: 100),
            padding: const EdgeInsets.all(PgSpace.m),
            decoration: BoxDecoration(
              color: PgColors.bgSecondary.withOpacity(0.6),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _isListening
                    ? PgColors.crit.withOpacity(0.4)
                    : PgColors.glassBorder,
              ),
            ),
            child: _liveTranscript.isEmpty
                ? Text(
                    _isListening
                        ? 'Bolo... (Listening...)'
                        : 'Transcript will appear here...',
                    style: const TextStyle(
                      color: PgColors.mediumBlue,
                      fontStyle: FontStyle.italic,
                      fontSize: 14,
                    ),
                  )
                : Text(
                    _liveTranscript,
                    style: const TextStyle(
                      color: PgColors.white,
                      fontSize: 15,
                      height: 1.5,
                    ),
                  ),
          ),
          if (_isListening) ...[
            const SizedBox(height: PgSpace.s),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: PgColors.crit,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  'Recording in $_selectedLocale...',
                  style: const TextStyle(
                    fontSize: 11,
                    color: PgColors.crit,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHistoryItem(int index, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: PgSpace.s),
      child: GlassCard(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: PgColors.accentBlue.withOpacity(0.2),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Center(
                child: Text(
                  '$index',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: PgColors.accentBlue,
                  ),
                ),
              ),
            ),
            const SizedBox(width: PgSpace.s),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(
                  color: PgColors.lightBlue,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: PgColors.mediumBlue,
        fontWeight: FontWeight.bold,
        fontSize: 14,
        letterSpacing: 0.5,
      ),
    );
  }
}
