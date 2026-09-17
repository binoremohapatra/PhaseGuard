import 'package:flutter/material.dart';

import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';
import 'stt_test_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: PgColors.screenGradient,
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: const SafeArea(
          child: SingleChildScrollView(
            padding: EdgeInsets.symmetric(horizontal: PgSpace.screenH),
            child: _SettingsContent(),
          ),
        ),
      ),
    );
  }
}

class _SettingsContent extends StatefulWidget {
  const _SettingsContent();

  @override
  State<_SettingsContent> createState() => _SettingsContentState();
}

class _SettingsContentState extends State<_SettingsContent> {
  bool callMonitoring = true;
  bool autoBlock = false;
  bool realTimeAlerts = true;
  bool deepfakeDetection = true;
  bool voiceAuth = true;
  bool factChecking = true;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const SectionTitle('Settings'),
        const SizedBox(height: PgSpace.section),
        _buildSettingsGroup(
          title: 'Protection',
          items: [
            _SettingItem(
              label: 'Call Monitoring',
              value: callMonitoring,
              onChanged: (value) {
                setState(() => callMonitoring = value);
              },
            ),
            _SettingItem(
              label: 'Auto Block',
              value: autoBlock,
              onChanged: (value) {
                setState(() => autoBlock = value);
              },
            ),
            _SettingItem(
              label: 'Real-time Alerts',
              value: realTimeAlerts,
              onChanged: (value) {
                setState(() => realTimeAlerts = value);
              },
            ),
          ],
        ),
        const SizedBox(height: PgSpace.section),
        _buildSettingsGroup(
          title: 'Detection',
          items: [
            _SettingItem(
              label: 'Deepfake Detection',
              value: deepfakeDetection,
              onChanged: (value) {
                setState(() => deepfakeDetection = value);
              },
            ),
            _SettingItem(
              label: 'Voice Authentication',
              value: voiceAuth,
              onChanged: (value) {
                setState(() => voiceAuth = value);
              },
            ),
            _SettingItem(
              label: 'Fact Checking',
              value: factChecking,
              onChanged: (value) {
                setState(() => factChecking = value);
              },
            ),
          ],
        ),
        const SizedBox(height: PgSpace.section),
        _buildSettingsGroup(
          title: 'About',
          items: [
            _SettingItem(
              label: 'App Version',
              value: null,
              subtitle: '1.0.0',
              onChanged: null,
            ),
            _SettingItem(
              label: 'API Endpoint',
              value: null,
              subtitle: 'phaseguard.onrender.com',
              onChanged: null,
            ),
          ],
        ),
        const SizedBox(height: PgSpace.section),
        // ── Developer Tools ──────────────────────────────────────────
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: const Text(
            'Developer Tools',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: PgColors.mediumBlue,
            ),
          ),
        ),
        GlassCard(
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: PgColors.accentBlue.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: PgColors.accentBlue.withOpacity(0.3)),
              ),
              child: const Icon(Icons.mic_rounded, color: PgColors.lightBlue, size: 20),
            ),
            title: const Text(
              'Test Local STT',
              style: TextStyle(color: PgColors.white, fontWeight: FontWeight.bold, fontSize: 13),
            ),
            subtitle: const Text(
              'On-device Speech-to-Text (speech_to_text)',
              style: TextStyle(color: PgColors.mediumBlue, fontSize: 11),
            ),
            trailing: const Icon(Icons.arrow_forward_ios_rounded,
                size: 14, color: PgColors.mediumBlue),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SttTestScreen()),
              );
            },
          ),
        ),
        const SizedBox(height: 100),
      ],
    );
  }

  Widget _buildSettingsGroup({
    required String title,
    required List<_SettingItem> items,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: PgColors.mediumBlue,
            ),
          ),
        ),
        ...items.asMap().entries.map((entry) {
          final isLast = entry.key == items.length - 1;
          return Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : 8),
            child: _buildSettingItem(entry.value),
          );
        }),
      ],
    );
  }

  Widget _buildSettingItem(_SettingItem item) {
    return GlassCard(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.label,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: PgColors.white,
                  ),
                ),
                if (item.subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    item.subtitle!,
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          if (item.value != null) ...[
            const SizedBox(width: 12),
            Switch(
              value: item.value ?? false,
              onChanged: item.onChanged,
              activeThumbImage: null,
              inactiveThumbColor: PgColors.mediumBlue,
            ),
          ],
        ],
      ),
    );
  }
}

class _SettingItem {
  final String label;
  final bool? value;
  final String? subtitle;
  final Function(bool)? onChanged;

  _SettingItem({
    required this.label,
    required this.value,
    this.subtitle,
    required this.onChanged,
  });
}
