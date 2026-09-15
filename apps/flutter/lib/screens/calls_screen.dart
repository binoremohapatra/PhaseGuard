import 'package:flutter/material.dart';

import '../services/accessibility_capture.dart';
import '../services/bluetooth_sco_capture.dart';
import '../services/call_socket.dart';
import '../services/shizuku_capture.dart';
import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';

class CallsScreen extends StatefulWidget {
  const CallsScreen({super.key});

  @override
  State<CallsScreen> createState() => _CallsScreenState();
}

class _CallsScreenState extends State<CallsScreen> {
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
            child: _CallsListView(),
          ),
        ),
      ),
    );
  }
}

class _CallsListView extends StatefulWidget {
  const _CallsListView();

  @override
  State<_CallsListView> createState() => _CallsListViewState();
}

class _CallsListViewState extends State<_CallsListView> {
  late List<CallRecord> calls;
  final CallSocket _callSocket = CallSocket();
  final AccessibilityCapture _accessibilityCapture = AccessibilityCapture();
  final BluetoothScoCapture _bluetoothScoCapture = BluetoothScoCapture();
  final ShizukuCapture _shizukuCapture = ShizukuCapture();
  bool _screenAudioEnabled = false;
  bool _screenAudioAvailable = false;
  bool _accessibilityEnabled = false;
  bool _bluetoothScoEnabled = false;
  bool _bluetoothHeadsetConnected = false;
  bool _shizukuEnabled = false;
  bool _shizukuInstalled = false;
  String _deviceInfo = 'Checking...';
  String _accessibilityStatus = 'Checking...';
  String _bluetoothStatus = 'Checking...';
  String _shizukuStatus = 'Checking...';

  @override
  void initState() {
    super.initState();
    calls = [
      CallRecord(
        id: '1',
        caller: 'Unknown Number +91-XXXX123456',
        time: '2 hours ago',
        duration: '2:34',
        riskLevel: 'high',
        status: 'blocked',
      ),
      CallRecord(
        id: '2',
        caller: 'Bank Customer Service',
        time: '5 hours ago',
        duration: '5:12',
        riskLevel: 'low',
        status: 'safe',
      ),
      CallRecord(
        id: '3',
        caller: 'Government Portal',
        time: '1 day ago',
        duration: '3:45',
        riskLevel: 'high',
        status: 'monitored',
      ),
    ];
    
    _checkScreenAudioAvailability();
    _checkAccessibilityService();
    _checkBluetoothSco();
    _checkShizuku();
    _accessibilityCapture.startListening();
    _bluetoothScoCapture.startListening();
    _shizukuCapture.startListening();
  }
  
  @override
  void dispose() {
    _accessibilityCapture.dispose();
    _bluetoothScoCapture.dispose();
    _shizukuCapture.dispose();
    super.dispose();
  }
  
  Future<void> _checkScreenAudioAvailability() async {
    try {
      final available = await _callSocket.getScreenAudioDeviceInfo();
      setState(() {
        _screenAudioAvailable = available['available'] == true;
        _deviceInfo = _screenAudioAvailable 
            ? '${available['manufacturer']} ${available['model']} (Android ${available['android_version']})'
            : 'Not available on this device';
      });
    } catch (e) {
      setState(() {
        _screenAudioAvailable = false;
        _deviceInfo = 'Error: $e';
      });
    }
  }
  
  Future<void> _checkAccessibilityService() async {
    try {
      final enabled = await _accessibilityCapture.isServiceEnabled();
      await _accessibilityCapture.getServiceState();
      setState(() {
        _accessibilityEnabled = enabled;
        _accessibilityStatus = enabled 
            ? 'Active (Call: ${_accessibilityCapture.callStateLabel})'
            : 'Not enabled';
      });
    } catch (e) {
      setState(() {
        _accessibilityEnabled = false;
        _accessibilityStatus = 'Error: $e';
      });
    }
  }
  
  Future<void> _checkBluetoothSco() async {
    try {
      final info = await _bluetoothScoCapture.getDeviceInfo();
      setState(() {
        _bluetoothHeadsetConnected = info['headsetConnected'] == true;
        _bluetoothStatus = _bluetoothHeadsetConnected 
            ? 'Connected: ${info['deviceName'] ?? 'Unknown'}'
            : 'No headset connected';
      });
    } catch (e) {
      setState(() {
        _bluetoothHeadsetConnected = false;
        _bluetoothStatus = 'Error: $e';
      });
    }
  }
  
  Future<void> _checkShizuku() async {
    try {
      final info = await _shizukuCapture.getDeviceInfo();
      setState(() {
        _shizukuInstalled = info['shizukuInstalled'] == true;
        _shizukuStatus = _shizukuInstalled 
            ? 'Installed (Experimental)'
            : 'Not installed';
      });
    } catch (e) {
      setState(() {
        _shizukuInstalled = false;
        _shizukuStatus = 'Error: $e';
      });
    }
  }
  
  Future<void> _toggleScreenAudio() async {
    if (_screenAudioEnabled) {
      await _callSocket.stopScreenAudioCapture();
      setState(() {
        _screenAudioEnabled = false;
      });
    } else {
      final success = await _callSocket.enableScreenAudioCapture(sampleRate: 16000);
      setState(() {
        _screenAudioEnabled = success;
      });
    }
  }
  
  Future<void> _enableAccessibilityService() async {
    final success = await _accessibilityCapture.enableService();
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enable PhaseGuard in Accessibility Settings'),
          duration: Duration(seconds: 3),
        ),
      );
    }
  }
  
  Future<void> _toggleBluetoothSco() async {
    if (_bluetoothScoEnabled) {
      await _bluetoothScoCapture.stopCapture();
      setState(() {
        _bluetoothScoEnabled = false;
      });
    } else {
      final success = await _bluetoothScoCapture.startCapture(sampleRate: 16000);
      setState(() {
        _bluetoothScoEnabled = success;
      });
    }
  }
  
  Future<void> _toggleShizuku() async {
    if (_shizukuEnabled) {
      await _shizukuCapture.stopCapture();
      setState(() {
        _shizukuEnabled = false;
      });
    } else {
      final success = await _shizukuCapture.startCapture(sampleRate: 16000);
      setState(() {
        _shizukuEnabled = success;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const SectionTitle('Call History'),
        const SizedBox(height: PgSpace.section),
        
        // Screen Audio Control
        if (_screenAudioAvailable) _buildScreenAudioControl(),
        if (!_screenAudioAvailable) _buildAudioNotAvailable(),
        
        const SizedBox(height: PgSpace.section),
        
        // Accessibility Service Control
        _buildAccessibilityServiceControl(),
        
        const SizedBox(height: PgSpace.section),
        
        // Bluetooth SCO Control
        _buildBluetoothScoControl(),
        
        const SizedBox(height: PgSpace.section),
        
        // Shizuku Control (Experimental)
        _buildShizukuControl(),
        
        const SizedBox(height: PgSpace.section),
        ...calls.map((call) => _buildCallItem(call)),
        const SizedBox(height: 100),
      ],
    );
  }
  
  Widget _buildScreenAudioControl() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Screen Audio Capture',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: PgColors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _deviceInfo,
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                  ),
                ],
              ),
              Switch(
                value: _screenAudioEnabled,
                onChanged: (value) => _toggleScreenAudio(),
                activeTrackColor: PgColors.accentBlue,
                activeThumbColor: PgColors.white,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _screenAudioEnabled 
                ? 'Capturing system audio (including calls)'
                : 'Enable to capture call audio for scam detection',
            style: const TextStyle(
              fontSize: 11,
              color: PgColors.lightBlue,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildAudioNotAvailable() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.info_outline,
                color: PgColors.warn,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Screen audio capture not available on this device',
                  style: const TextStyle(
                    fontSize: 12,
                    color: PgColors.lightBlue,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Fallback: Enable speakerphone during calls for audio capture',
            style: const TextStyle(
              fontSize: 11,
              color: PgColors.mediumBlue,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildAccessibilityServiceControl() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Accessibility Service',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: PgColors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _accessibilityStatus,
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                  ),
                ],
              ),
              if (!_accessibilityEnabled)
                ElevatedButton(
                  onPressed: _enableAccessibilityService,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: PgColors.accentBlue,
                    foregroundColor: PgColors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    minimumSize: Size.zero,
                  ),
                  child: const Text(
                    'Enable',
                    style: TextStyle(fontSize: 11),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _accessibilityEnabled 
                ? 'Call detection and audio capture active'
                : 'Enable to detect calls and attempt audio capture',
            style: const TextStyle(
              fontSize: 11,
              color: PgColors.lightBlue,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildBluetoothScoControl() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bluetooth SCO',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: PgColors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _bluetoothStatus,
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                  ),
                ],
              ),
              if (_bluetoothHeadsetConnected)
                Switch(
                  value: _bluetoothScoEnabled,
                  onChanged: (value) => _toggleBluetoothSco(),
                  activeTrackColor: PgColors.accentBlue,
                  activeThumbColor: PgColors.white,
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _bluetoothHeadsetConnected 
                ? (_bluetoothScoEnabled 
                    ? 'Capturing SCO audio (headset required)'
                    : 'Enable to capture SCO audio')
                : 'Connect Bluetooth headset for SCO audio',
            style: const TextStyle(
              fontSize: 11,
              color: PgColors.lightBlue,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildShizukuControl() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        'Shizuku',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: PgColors.white,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: PgColors.dspAccent.withValues(alpha: 0.2),
                          border: Border.all(color: PgColors.dspAccent, width: 1),
                          borderRadius: BorderRadius.circular(PgRadius.bar),
                        ),
                        child: const Text(
                          'EXPERIMENTAL',
                          style: TextStyle(
                            fontSize: 8,
                            fontWeight: FontWeight.w700,
                            color: PgColors.dspAccent,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _shizukuStatus,
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                  ),
                ],
              ),
              if (_shizukuInstalled)
                Switch(
                  value: _shizukuEnabled,
                  onChanged: (value) => _toggleShizuku(),
                  activeTrackColor: PgColors.dspAccent,
                  activeThumbColor: PgColors.white,
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _shizukuInstalled 
                ? (_shizukuEnabled 
                    ? 'Advanced audio capture via Shizuku'
                    : 'Enable for privileged audio access')
                : 'Install Shizuku for advanced audio capture',
            style: const TextStyle(
              fontSize: 11,
              color: PgColors.lightBlue,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCallItem(CallRecord call) {
    final riskColor = _getRiskColor(call.riskLevel);
    final statusLabel = _getStatusLabel(call.status);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        call.caller,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: PgColors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${call.time} • ${call.duration}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: PgColors.mediumBlue,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: riskColor.withValues(alpha: 0.15),
                    border: Border.all(color: riskColor, width: 1),
                    borderRadius: BorderRadius.circular(PgRadius.bar),
                  ),
                  child: Text(
                    call.riskLevel.toUpperCase(),
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: riskColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: riskColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  statusLabel,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: PgColors.lightBlue,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getRiskColor(String level) {
    switch (level) {
      case 'low':
        return PgColors.safe;
      case 'medium':
        return PgColors.warn;
      case 'high':
        return PgColors.crit;
      default:
        return PgColors.mediumBlue;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'blocked':
        return 'Blocked & Reported';
      case 'safe':
        return 'Safe Call';
      case 'monitored':
        return 'Monitored';
      default:
        return 'Unknown';
    }
  }
}

class CallRecord {
  final String id;
  final String caller;
  final String time;
  final String duration;
  final String riskLevel;
  final String status;

  CallRecord({
    required this.id,
    required this.caller,
    required this.time,
    required this.duration,
    required this.riskLevel,
    required this.status,
  });
}