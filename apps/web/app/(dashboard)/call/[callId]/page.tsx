'use client';
import React, { useEffect, useState, useRef } from 'react';
import PhaseOrbitCanvas from '../../../../components/hud/PhaseOrbitCanvas';
import StressMeter from '../../../../components/hud/StressMeter';
import AlertBanner from '../../../../components/hud/AlertBanner';
import EscalationModal from '../../../../components/hud/EscalationModal';
import { WsClient } from '../../../../lib/audio/ws-client';
import { AlertStatus, WsMessage } from '../../../../lib/types/protocol';

export default function CallDashboard({ params }: { params: Promise<{ callId: string }> | { callId: string } }) {
  // Next.js 15 requires unwrapping params if it's a promise
  const resolvedParams = params instanceof Promise ? React.use(params as Promise<{ callId: string }>) : params as { callId: string };
  const callId = resolvedParams.callId;

  const [status, setStatus] = useState<'connected' | 'disconnected' | 'error' | 'idle'>('idle');
  const [pdiScore, setPdiScore] = useState(0);
  const [tremorEnergy, setTremorEnergy] = useState(0);
  const [alertState, setAlertState] = useState<AlertStatus>('idle');
  const [alertMessage, setAlertMessage] = useState<string>('');
  const [isMicActive, setIsMicActive] = useState(false);
  const [authToken, setAuthToken] = useState<string>('');
  const [scambaiterActive, setScambaiterActive] = useState(false);
  const [scambaiterStatus, setScambaiterStatus] = useState<string>('');
  const [escalationModalOpen, setEscalationModalOpen] = useState(false);
  const [videoFrameCount, setVideoFrameCount] = useState(0);
  const [isScreenCaptureActive, setIsScreenCaptureActive] = useState(false);
  // DSP enabled/disabled — off by default (real-world validation showed unreliable standalone results)
  const [isDspEnabled, setIsDspEnabled] = useState(false);

  const wsClientRef = useRef<WsClient | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const screenCaptureIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const playScambaiterAudio = async (buffer: ArrayBuffer) => {
    const audioCtx = audioContextRef.current;
    if (!audioCtx) {
      console.warn("AudioContext not initialized, cannot play scambaiter audio");
      return;
    }

    try {
      // Use decodeAudioData which safely handles MP3 bytes from gTTS as well as PCM/WAV
      // This is crucial because if pydub isn't installed on the backend, it sends raw MP3.
      const audioBuffer = await audioCtx.decodeAudioData(buffer.slice(0));
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtx.destination);
      source.start();
    } catch (err) {
      console.error("Failed to decode scambaiter audio data:", err);
    }
  };

  useEffect(() => {
    async function initializeCall() {
      let token = new URLSearchParams(window.location.search).get('token');

      if (!token) {
        // Automatically fetch a token for this callId if missing
        try {
          const res = await fetch('http://localhost:8000/call/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ call_id: callId })
          });
          const data = await res.json();
          token = data.token;
          if (!token) throw new Error('Failed to fetch token');
          // Update URL without reloading
          window.history.replaceState({}, '', `?token=${token}`);
        } catch (err) {
          console.error('No token provided and failed to fetch one', err);
          return;
        }
      }
      setAuthToken(token);

      const client = new WsClient(
        callId,
        token,
        (msg: WsMessage) => {
          if (msg.type === 'pdi_update') {
            setPdiScore(msg.pdi_score);
          } else if (msg.type === 'tremor_update') {
            setTremorEnergy(msg.tremor_energy);
          } else if (msg.type === 'factcheck_update' || msg.type === 'ensemble_update') {
            // Backend sends uppercase status (CRITICAL, SAFE, UNCERTAIN);
            // AlertBanner matches lowercase. Normalize here.
            const rawStatus = (msg as any).status || (msg as any).label || 'idle';
            setAlertState((rawStatus as string).toLowerCase() as AlertStatus);
            if ((msg as any).message) {
              setAlertMessage((msg as any).message);
            }
          } else if (msg.type === 'mode_update') {
            if (msg.mode === 'limited') {
              setAlertState('limited');
              setAlertMessage('Network unavailable. Using local DSP checks only.');
            } else if (msg.mode === 'full') {
              setAlertState('safe');
              setAlertMessage('Network restored. Full verification active.');
            }
          } else if (msg.type === 'config_info') {
            // Backend sends one-time config flags on connection
            setIsDspEnabled(msg.dsp_enabled);
          } else if (msg.type === 'video_frame_captured') {
            // Backend captured a video evidence frame on CRITICAL verdict
            setVideoFrameCount((c) => c + 1);
          }
        },
        (newStatus) => setStatus(newStatus),
        (buffer: ArrayBuffer) => {
          playScambaiterAudio(buffer);
        }
      );

      wsClientRef.current = client;
      client.connect();
    }

    initializeCall();

    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
      stopMic();
      stopScreenCapture();
    };
  }, [callId]);

  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;
      
      await audioCtx.audioWorklet.addModule('/worklets/pcm-processor.js');
      
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = new AudioWorkletNode(audioCtx, 'pcm-processor');
      
      processor.port.onmessage = (e) => {
        if (wsClientRef.current) {
          wsClientRef.current.sendAudio(e.data);
        }
      };
      
      source.connect(processor);
      processor.connect(audioCtx.destination);
      
      setIsMicActive(true);
    } catch (err) {
      console.error('Mic access denied or failed', err);
    }
  };

  const stopMic = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsMicActive(false);
  };

  const startScreenCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setIsScreenCaptureActive(true);

      // Extract and upload frame every 5 seconds
      screenCaptureIntervalRef.current = setInterval(() => {
        captureAndUploadFrame();
      }, 5000);

      // Handle user stopping share via browser native UI
      stream.getVideoTracks()[0].onended = () => {
        stopScreenCapture();
      };
    } catch (err) {
      console.error('Screen capture failed or denied', err);
    }
  };

  const stopScreenCapture = () => {
    if (screenCaptureIntervalRef.current) {
      clearInterval(screenCaptureIntervalRef.current);
      screenCaptureIntervalRef.current = null;
    }
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsScreenCaptureActive(false);
  };

  const captureAndUploadFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !authToken) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Set canvas to actual video dimensions
    if (video.videoWidth === 0 || video.videoHeight === 0) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');
      
      try {
        await fetch(`http://localhost:8000/call/${callId}/frame`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${authToken}`
          },
          body: formData
        });
      } catch (err) {
        console.error('Frame upload failed', err);
      }
    }, 'image/jpeg', 0.8);
  };

  const deployScambaiter = async () => {
    if (!authToken) return;
    try {
      setScambaiterStatus('Activating...');
      const res = await fetch(`http://localhost:8000/call/${callId}/scambait`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        setScambaiterActive(true);
        setScambaiterStatus('SCAMBAITER ACTIVE — AI engaged');
      } else {
        const err = await res.json();
        setScambaiterStatus(`Error: ${err.detail || res.statusText}`);
      }
    } catch (e) {
      setScambaiterStatus(`Network error: ${e}`);
    }
  };

  const downloadDossier = () => {
    if (!authToken) return;
    const url = `http://localhost:8000/call/${callId}/dossier`;
    // Open in new tab with Authorization header via a fetch-triggered blob download
    fetch(url, { headers: { Authorization: `Bearer ${authToken}` } })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `phaseguard-${callId}.pdf`;
        a.click();
      })
      .catch(e => console.error('Dossier download failed', e));
  };

  return (
    <div className="min-h-screen bg-black text-white p-8 font-sans">
      <header className="mb-8 flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">PhaseGuard OS</h1>
          <p className="text-gray-400 font-mono mt-1">Interception Stream: {callId}</p>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="font-mono uppercase text-sm text-gray-300">WS: {status}</span>
            </div>
            {isScreenCaptureActive && (
              <div className="flex items-center gap-2">
                <span className="animate-pulse text-xs">🔴</span>
                <span className="font-mono uppercase text-xs text-red-400 font-bold tracking-wider border border-red-500/30 bg-red-900/20 px-2 py-0.5 rounded">Screen protection active</span>
              </div>
            )}
          </div>
          <button 
            onClick={isScreenCaptureActive ? stopScreenCapture : startScreenCapture}
            className={`px-4 py-2 rounded-lg font-bold transition-colors ${
              isScreenCaptureActive ? 'bg-red-600/80 hover:bg-red-700/80 text-white text-sm' : 'bg-purple-600/80 hover:bg-purple-700/80 text-white text-sm'
            }`}
          >
            {isScreenCaptureActive ? 'Stop Protection' : 'Start Screen Protection'}
          </button>
          <button 
            onClick={isMicActive ? stopMic : startMic}
            className={`px-6 py-2 rounded-lg font-bold transition-colors ${
              isMicActive ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isMicActive ? 'Stop Interception' : 'Start Interception'}
          </button>
        </div>
      </header>

      {/* Hidden elements for screen capture frame extraction */}
      <video ref={videoRef} className="hidden" muted playsInline />
      <canvas ref={canvasRef} className="hidden" />

      <main className="flex flex-col gap-8">
        {/* ── PRIMARY SECTION: Alert Banner ── */}
        <AlertBanner status={alertState} message={alertMessage} />

        {/* Action buttons — shown when CRITICAL verdict reached */}
        {alertState === 'critical' && (
          <div className="flex gap-4 flex-wrap">
            {!scambaiterActive ? (
              <button
                id="btn-deploy-scambaiter"
                onClick={deployScambaiter}
                className="px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-lg transition-colors animate-pulse"
              >
                🤖 Deploy Scambaiter
              </button>
            ) : (
              <div className="px-6 py-3 bg-orange-900 text-orange-300 font-bold rounded-lg">
                {scambaiterStatus}
              </div>
            )}
            <button
              id="btn-download-dossier"
              onClick={downloadDossier}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-colors"
            >
              📄 Download PDF Dossier
            </button>
            <button
              id="btn-escalate-cybercrime"
              onClick={() => setEscalationModalOpen(true)}
              className="px-6 py-3 text-white font-bold rounded-lg transition-all transform hover:scale-105 active:scale-95 relative overflow-hidden"
              style={{
                background: 'linear-gradient(135deg, #c0392b, #922b21)',
                boxShadow: '0 0 24px rgba(192,57,43,0.5)',
              }}
            >
              🚨 Escalate to Cybercrime
              {videoFrameCount > 0 && (
                <span
                  className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 rounded-full text-white text-xs flex items-center justify-center font-bold"
                  title={`${videoFrameCount} video frame(s) captured`}
                >
                  {videoFrameCount}
                </span>
              )}
            </button>
          </div>
        )}

        {/* Always show dossier download if we have a token */}
        {alertState !== 'critical' && alertState !== 'idle' && authToken && (
          <div className="flex gap-4">
            <button
              id="btn-download-dossier-secondary"
              onClick={downloadDossier}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm font-mono rounded-lg transition-colors"
            >
              📄 Download Dossier
            </button>
          </div>
        )}

        {/* ── HERO SECTION: Live Fact-Check Transcript (Primary Detection Engine) ── */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-inner">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
            <h3 className="text-gray-200 font-mono text-sm tracking-wider uppercase font-semibold">
              Real-Time Fact-Checker &amp; Claim Analysis
            </h3>
            {/* "Primary Detection Engine" badge — mirrors legacy/frontend/index.html .primary-badge */}
            <span className="text-xs font-semibold tracking-widest uppercase bg-blue-900/60 text-blue-300 border border-blue-700 px-3 py-1 rounded-full">
              Primary Detection Engine
            </span>
          </div>
          <div className="min-h-[200px] space-y-4 font-mono text-sm text-gray-300">
            <p className="italic text-gray-500">Waiting for speech...</p>
            {/* Transcript chunks would go here */}
          </div>
        </section>

        {/* ── EXPERIMENTAL SECTION: DSP Voice Deepfake Engine (collapsible) ── */}
        {/* Mirrors legacy/frontend/index.html <details class="dsp-panel experimental-panel"> */}
        <details className="group bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <summary className="flex items-center justify-between p-5 cursor-pointer select-none hover:bg-gray-800/50 transition-colors list-none">
            <h3 className="text-gray-300 font-mono text-sm tracking-wider uppercase font-semibold">
              ⚙ Voice Deepfake Engine (Bispectrum + Tremor)
            </h3>
            <div className="flex items-center gap-3">
              {/* Experimental badge — mirrors legacy/frontend/index.html .experimental-badge */}
              <span
                className="text-xs font-semibold tracking-wide bg-amber-900/50 text-amber-400 border border-amber-700/60 px-3 py-1 rounded-full"
                title="Real-world validation showed overlapping results vs gTTS. Not reliable as standalone. Use as supplementary signal only."
              >
                ⚠ Experimental — Under Development
              </span>
              {/* Collapse/expand chevron */}
              <span className="text-gray-500 font-mono text-xs group-open:rotate-180 transition-transform duration-200 inline-block">
                ▼
              </span>
            </div>
          </summary>

          <div className="p-5 border-t border-gray-800">
            {/* DSP-disabled notice — shown when isDspEnabled=false, hidden when enabled */}
            {!isDspEnabled && (
              <div className="mb-5 p-4 bg-gray-800/60 border border-gray-700 rounded-lg font-mono text-sm text-gray-400 leading-relaxed">
                DSP voice detection is <strong className="text-gray-200">disabled</strong> in this build.{' '}
                Set{' '}
                <code className="bg-gray-700 text-amber-400 px-1.5 py-0.5 rounded text-xs">
                  DSP_VOICE_DETECTION_ENABLED=true
                </code>{' '}
                in your <code className="bg-gray-700 text-amber-400 px-1.5 py-0.5 rounded text-xs">.env</code> to enable for research.
              </div>
            )}

            {/* DSP gauges — PhaseOrbitCanvas + StressMeter */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-[400px]">
              <PhaseOrbitCanvas pdiScore={pdiScore} isDspEnabled={isDspEnabled} />
              <StressMeter tremorEnergy={tremorEnergy} isDspEnabled={isDspEnabled} />
            </div>
          </div>
        </details>
      </main>

      {/* Escalation Modal — portal-like, rendered at root so it overlays everything */}
      {escalationModalOpen && authToken && (
        <EscalationModal
          callId={callId}
          authToken={authToken}
          onClose={() => setEscalationModalOpen(false)}
        />
      )}
    </div>
  );
}


