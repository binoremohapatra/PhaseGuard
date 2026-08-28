package com.voxshield.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/**
 * WsMessages.kt — Kotlin data class equivalents of the browser-side protocol.ts
 * WebSocket message types used by the PhaseGuard/VoxShield backend pipeline.
 *
 * These mirror the binary-frame + JSON-envelope protocol already built for the
 * browser-based AudioWorklet frontend. The only difference on Android is that
 * audio SOURCE changes from AudioWorklet → AudioRecord; all message shapes are
 * identical so the backend requires zero changes.
 *
 * Message flow:
 *   Android → Backend : raw binary ByteString frames (PCM16LE, 16kHz mono, 640-byte chunks = 20ms)
 *   Backend → Android : JSON text frames matching the sealed class hierarchy below
 *
 * Moshi @JsonClass(generateAdapter = true) is used for zero-reflection codegen.
 * Add kapt/ksp for moshi-kotlin-codegen if reflection-free mode is preferred;
 * currently uses moshi-kotlin (reflection-based) for simplicity.
 */

// ─── Incoming message type discriminator ───────────────────────────────────────

/**
 * Raw envelope parsed before dispatching to typed sub-classes.
 */
@JsonClass(generateAdapter = true)
data class WsEnvelope(
    @Json(name = "type") val type: String,
    // Raw JSON object; re-parsed based on `type`
    @Json(name = "payload") val payload: Map<String, Any?>? = null
)

// ─── Typed backend → Android messages ─────────────────────────────────────────

sealed class BackendMessage {

    /**
     * PDI (Phone Deception Index) update — primary fraud probability signal.
     * Backend emits this ~every 2–5 seconds as more audio is analyzed.
     *
     * [pdiScore]  0.0 = definitely safe, 1.0 = definitely fraud
     * [verdict]   Human-readable category: "safe" | "suspicious" | "scam"
     * [confidence] Model confidence in this verdict (0.0–1.0)
     */
    @JsonClass(generateAdapter = true)
    data class PdiUpdate(
        @Json(name = "call_id")    val callId: String,
        @Json(name = "pdi_score")  val pdiScore: Float,
        @Json(name = "verdict")    val verdict: String,        // "safe" | "suspicious" | "scam"
        @Json(name = "confidence") val confidence: Float,
        @Json(name = "timestamp")  val timestamp: Long
    ) : BackendMessage()

    /**
     * Real-time fact-check result for a specific claim detected in speech.
     * Backend emits this when the STT pipeline detects a verifiable claim
     * (e.g., "your account has been locked", "IRS is calling").
     *
     * [claim]      The detected claim text
     * [result]     Verdict: "true" | "false" | "unverifiable"
     * [confidence] Confidence in the fact-check result
     */
    @JsonClass(generateAdapter = true)
    data class FactCheckUpdate(
        @Json(name = "call_id")    val callId: String,
        @Json(name = "claim")      val claim: String,
        @Json(name = "result")     val result: String,         // "true" | "false" | "unverifiable"
        @Json(name = "confidence") val confidence: Float,
        @Json(name = "timestamp")  val timestamp: Long
    ) : BackendMessage()

    /**
     * Incremental STT transcript chunk.
     * [isFinal] false = interim result, true = committed word sequence.
     */
    @JsonClass(generateAdapter = true)
    data class TranscriptChunk(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "text")      val text: String,
        @Json(name = "is_final")  val isFinal: Boolean,
        @Json(name = "timestamp") val timestamp: Long
    ) : BackendMessage()

    /**
     * Session lifecycle status from backend.
     * [status] "active" | "ended" | "error" | "reconnecting"
     */
    @JsonClass(generateAdapter = true)
    data class SessionStatus(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "status")    val status: String,
        @Json(name = "message")   val message: String? = null,
        @Json(name = "timestamp") val timestamp: Long
    ) : BackendMessage()

    /**
     * Scam alert — high-confidence detection that warrants immediate user notification.
     * Backend emits this when pdi_score crosses a configured threshold.
     */
    @JsonClass(generateAdapter = true)
    data class ScamAlert(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "pdi_score") val pdiScore: Float,
        @Json(name = "reason")    val reason: String,          // Human-readable alert reason
        @Json(name = "timestamp") val timestamp: Long
    ) : BackendMessage()

    /** Fallback for unrecognised message types — preserves forward-compatibility. */
    data class Unknown(val rawType: String) : BackendMessage()
}

// ─── Verdict helpers ───────────────────────────────────────────────────────────

enum class PdiVerdict(val label: String, val emoji: String) {
    SAFE("Safe", "✅"),
    SUSPICIOUS("Suspicious", "⚠️"),
    SCAM("Scam Detected", "🚨"),
    UNKNOWN("Analyzing…", "🔍");

    companion object {
        fun from(raw: String?) = when (raw?.lowercase()) {
            "safe"       -> SAFE
            "suspicious" -> SUSPICIOUS
            "scam"       -> SCAM
            else         -> UNKNOWN
        }
    }
}
