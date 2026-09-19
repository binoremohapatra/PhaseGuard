import 'dart:async';
import 'package:agora_rtc_engine/agora_rtc_engine.dart';
import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

/// InAppCallingService manages Agora RTC Engine in Testing Mode (App ID only)
/// and hooks into MediaEngine to capture raw 16kHz 16-bit mono PCM remote audio,
/// batching it into 100ms chunks (3200 bytes) for PhaseGuard's scam detection pipeline.
class InAppCallingService extends ChangeNotifier {
  static const String configuredAppId = String.fromEnvironment('AGORA_APP_ID', defaultValue: '');

  RtcEngine? _engine;
  bool _isInitialized = false;
  bool _isJoined = false;
  bool _isConnected = false;
  bool _isMuted = false;
  bool _isSpeakerphoneOn = true;
  bool _isCameraOff = false;
  int? _remoteUid;
  int _callDurationSeconds = 0;
  Timer? _durationTimer;

  // 100ms audio frame accumulator: 16000 Hz * 0.1s * 2 bytes = 3200 bytes
  static const int targetChunkBytes = 3200;
  final List<int> _audioAccumulator = [];
  final StreamController<Uint8List> _remoteAudioController = StreamController<Uint8List>.broadcast();

  // Getters
  RtcEngine? get engine => _engine;
  bool get isInitialized => _isInitialized;
  bool get isJoined => _isJoined;
  bool get isConnected => _isConnected;
  bool get isMuted => _isMuted;
  bool get isSpeakerphoneOn => _isSpeakerphoneOn;
  bool get isCameraOff => _isCameraOff;
  int? get remoteUid => _remoteUid;
  int get callDurationSeconds => _callDurationSeconds;
  Stream<Uint8List> get remoteAudioStream => _remoteAudioController.stream;

  Future<void> initialize({String? appId}) async {
    if (_isInitialized) return;

    final targetId = appId ?? configuredAppId;
    if (targetId.isEmpty) {
      debugPrint('[InAppCallingService] Warning: AGORA_APP_ID is empty. Pass via --dart-define=AGORA_APP_ID=...');
    }

    _engine = createAgoraRtcEngine();
    await _engine!.initialize(RtcEngineContext(
      appId: targetId,
      channelProfile: ChannelProfileType.channelProfileCommunication,
    ));

    // Configure raw playback audio frame parameters for 16kHz mono 16-bit PCM
    // 320 samples = 20ms frame at 16kHz
    try {
      await _engine!.setPlaybackAudioFrameParameters(
        sampleRate: 16000,
        channel: 1,
        mode: RawAudioFrameOpModeType.rawAudioFrameOpModeReadOnly,
        samplesPerCall: 320,
      );

      // Register raw audio frame observer on MediaEngine
      final mediaEngine = _engine!.getMediaEngine();
      mediaEngine.registerAudioFrameObserver(
        AudioFrameObserver(
          onPlaybackAudioFrameBeforeMixing: (String channelId, int uid, AudioFrame frame) {
            _handleIncomingAudioFrame(frame);
          },
          onPlaybackAudioFrame: (String channelId, AudioFrame frame) {
            // Fallback if before mixing callback is not triggered
            if (_remoteUid == null || _remoteUid == 0) {
              _handleIncomingAudioFrame(frame);
            }
          },
        ),
      );
      debugPrint('[InAppCallingService] AudioFrameObserver registered at 16kHz mono');
    } catch (e) {
      debugPrint('[InAppCallingService] Error configuring raw audio observer: $e');
    }

    _engine!.registerEventHandler(
      RtcEngineEventHandler(
        onJoinChannelSuccess: (RtcConnection connection, int elapsed) {
          debugPrint('[InAppCallingService] Joined channel: ${connection.channelId}');
          _isJoined = true;
          _engine?.setEnableSpeakerphone(true);
          _engine?.enableLocalAudio(true);
          _engine?.muteLocalAudioStream(false);
          _engine?.adjustRecordingSignalVolume(100);
          _engine?.adjustPlaybackSignalVolume(100);
          notifyListeners();
        },
        onUserJoined: (RtcConnection connection, int remoteUid, int elapsed) {
          debugPrint('[InAppCallingService] Remote user joined: $remoteUid');
          _remoteUid = remoteUid;
          _isConnected = true;
          _startDurationTimer();
          notifyListeners();
        },
        onUserOffline: (RtcConnection connection, int remoteUid, UserOfflineReasonType reason) {
          debugPrint('[InAppCallingService] Remote user offline: $remoteUid ($reason)');
          _remoteUid = null;
          _isConnected = false;
          _stopDurationTimer();
          notifyListeners();
        },
        onLeaveChannel: (RtcConnection connection, RtcStats stats) {
          debugPrint('[InAppCallingService] Left channel');
          _isJoined = false;
          _isConnected = false;
          _remoteUid = null;
          _stopDurationTimer();
          notifyListeners();
        },
        onError: (ErrorCodeType err, String msg) {
          debugPrint('[InAppCallingService] Agora error $err: $msg');
        },
      ),
    );

    _isInitialized = true;
    notifyListeners();
  }

  void _handleIncomingAudioFrame(AudioFrame frame) {
    final buffer = frame.buffer;
    if (buffer == null || buffer.isEmpty) return;

    _audioAccumulator.addAll(buffer);

    // Flush in 100ms chunks (3200 bytes)
    while (_audioAccumulator.length >= targetChunkBytes) {
      final chunk = Uint8List.fromList(_audioAccumulator.sublist(0, targetChunkBytes));
      _audioAccumulator.removeRange(0, targetChunkBytes);
      _remoteAudioController.add(chunk);
    }
  }

  Future<void> joinCall({
    required String channelName,
    required String callType, // 'audio' or 'video'
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    // Request permissions
    final micPerm = await Permission.microphone.request();
    debugPrint('[InAppCallingService] Microphone permission status: $micPerm');
    if (callType == 'video') {
      await Permission.camera.request();
    }

    await _engine!.enableAudio();
    await _engine!.enableLocalAudio(true);
    await _engine!.muteLocalAudioStream(false);
    await _engine!.adjustRecordingSignalVolume(100);
    await _engine!.adjustPlaybackSignalVolume(100);

    try {
      await _engine!.setDefaultAudioRouteToSpeakerphone(true);
      await _engine!.setEnableSpeakerphone(true);
      _isSpeakerphoneOn = true;
    } catch (_) {}

    if (callType == 'video') {
      await _engine!.enableVideo();
      await _engine!.startPreview();
      _isCameraOff = false;
    } else {
      await _engine!.disableVideo();
      _isCameraOff = true;
    }

    _isMuted = false;
    _audioAccumulator.clear();

    // In Agora Testing Mode (App ID only), token is empty string ""
    await _engine!.joinChannel(
      token: '',
      channelId: channelName,
      uid: 0,
      options: ChannelMediaOptions(
        channelProfile: ChannelProfileType.channelProfileCommunication,
        clientRoleType: ClientRoleType.clientRoleBroadcaster,
        publishMicrophoneTrack: true,
        publishCameraTrack: callType == 'video',
        autoSubscribeAudio: true,
        autoSubscribeVideo: callType == 'video',
      ),
    );
  }

  Future<void> toggleMute() async {
    if (_engine == null) return;
    _isMuted = !_isMuted;
    await _engine!.muteLocalAudioStream(_isMuted);
    notifyListeners();
  }

  Future<void> toggleSpeaker() async {
    if (_engine == null) return;
    _isSpeakerphoneOn = !_isSpeakerphoneOn;
    await _engine!.setEnableSpeakerphone(_isSpeakerphoneOn);
    notifyListeners();
  }

  Future<void> toggleCamera() async {
    if (_engine == null) return;
    _isCameraOff = !_isCameraOff;
    await _engine!.muteLocalVideoStream(_isCameraOff);
    notifyListeners();
  }

  Future<void> switchCamera() async {
    if (_engine == null) return;
    await _engine!.switchCamera();
  }

  Future<void> leaveCall() async {
    _stopDurationTimer();
    _audioAccumulator.clear();
    try {
      if (_engine != null) {
        await _engine!.leaveChannel();
        await _engine!.stopPreview();
        await _engine!.disableVideo();
      }
    } catch (e) {
      debugPrint('[InAppCallingService] Error leaving channel: $e');
    } finally {
      _isJoined = false;
      _isConnected = false;
      _remoteUid = null;
      _callDurationSeconds = 0;
      notifyListeners();
    }
  }

  void _startDurationTimer() {
    _durationTimer?.cancel();
    _callDurationSeconds = 0;
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _callDurationSeconds++;
      notifyListeners();
    });
  }

  void _stopDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
  }

  @override
  void dispose() {
    _stopDurationTimer();
    _remoteAudioController.close();
    _engine?.release();
    super.dispose();
  }
}
