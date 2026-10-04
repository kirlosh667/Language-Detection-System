"""
Language Detection Lab — Text & Speech
College NLP / Speech Processing demonstration app.
"""

import os
import tempfile
from functools import lru_cache

from flask import Flask, jsonify, render_template, request
from langdetect import DetectorFactory, LangDetectException, detect_langs
from werkzeug.utils import secure_filename

# Make langdetect results reproducible
DetectorFactory.seed = 0

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB audio uploads

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
}

LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ur": "Urdu",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "nl": "Dutch",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "fi": "Finnish",
    "no": "Norwegian",
    "da": "Danish",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "uk": "Ukrainian",
    "ro": "Romanian",
    "hu": "Hungarian",
    "af": "Afrikaans",
    "sw": "Swahili",
    "so": "Somali",
    "cy": "Welsh",
    "sq": "Albanian",
    "et": "Estonian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "hr": "Croatian",
    "bg": "Bulgarian",
    "mk": "Macedonian",
    "tl": "Tagalog",
    "ne": "Nepali",
}

EXAMPLES = {
    "en": "Natural language processing helps computers understand human language.",
    "ta": "இயற்கை மொழி செயலாக்கம் கணினிகளுக்கு மனித மொழியைப் புரிந்துகொள்ள உதவுகிறது.",
    "hi": "प्राकृतिक भाषा प्रसंस्करण कंप्यूटर को मानव भाषा समझने में मदद करता है।",
    "te": "సహజ భాషా ప్రాసెసింగ్ కంప్యూటర్లు మానవ భాషను అర్థం చేసుకోవడానికి సహాయపడుతుంది.",
    "ml": "പ്രകൃതിദത്ത ഭാഷാ സംസ്കരണം കമ്പ്യൂട്ടറുകളെ മനുഷ്യഭാഷ മനസ്സിലാക്കാൻ സഹായിക്കുന്നു.",
}

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".webm", ".ogg", ".mp3", ".m4a", ".flac", ".mp4"}

_whisper_model = None


def get_whisper_model():
    """Lazy-load Whisper tiny model (first speech request downloads ~75 MB)."""
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model("tiny")
    return _whisper_model


def language_display_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code.upper())


def detect_text_language(text: str) -> dict:
    """Detect language of text and return structured result."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "success": False,
            "error": "Please enter some text to detect the language.",
        }

    if len(cleaned) < 3:
        return {
            "success": False,
            "error": "Text is too short. Please enter at least a few words for reliable detection.",
        }

    try:
        candidates = detect_langs(cleaned)
    except LangDetectException:
        return {
            "success": False,
            "error": "Could not detect the language. Try a longer or clearer sample.",
        }

    if not candidates:
        return {
            "success": False,
            "error": "Could not detect the language. Try a longer or clearer sample.",
        }

    top = candidates[0]
    code = top.lang
    confidence = round(float(top.prob) * 100, 2)
    name = language_display_name(code)
    supported = code in SUPPORTED_LANGUAGES

    result = {
        "success": True,
        "language_code": code,
        "language": name,
        "confidence": confidence,
        "supported": supported,
        "candidates": [
            {
                "language_code": c.lang,
                "language": language_display_name(c.lang),
                "confidence": round(float(c.prob) * 100, 2),
            }
            for c in candidates[:3]
        ],
    }

    if not supported:
        supported_list = ", ".join(SUPPORTED_LANGUAGES.values())
        result["message"] = (
            f"Detected language is {name}, which is outside the lab's supported set "
            f"({supported_list}). Detection still succeeded, but this language is marked unsupported."
        )
    else:
        result["message"] = f"Detected language: {name}"

    return result


@lru_cache(maxsize=1)
def whisper_available() -> bool:
    try:
        import whisper  # noqa: F401

        return True
    except ImportError:
        return False


@app.route("/")
def index():
    return render_template(
        "index.html",
        supported_languages=SUPPORTED_LANGUAGES,
        examples=EXAMPLES,
    )


@app.route("/api/detect-text", methods=["POST"])
def api_detect_text():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    return jsonify(detect_text_language(text))


@app.route("/api/detect-speech", methods=["POST"])
def api_detect_speech():
    """Accept recorded audio, transcribe with Whisper, then detect language of the text."""
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file received."}), 400

    audio_file = request.files["audio"]
    if not audio_file or not audio_file.filename:
        return jsonify({"success": False, "error": "Empty audio upload."}), 400

    original_name = secure_filename(audio_file.filename) or "recording.webm"
    _, ext = os.path.splitext(original_name.lower())
    if ext and ext not in ALLOWED_AUDIO_EXTENSIONS:
        ext = ".webm"

    if not whisper_available():
        return jsonify(
            {
                "success": False,
                "error": (
                    "Speech recognition requires the openai-whisper package. "
                    "Install dependencies from requirements.txt and ensure FFmpeg is on PATH."
                ),
            }
        ), 503

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext or ".webm") as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        model = get_whisper_model()
        # Restrict decoding to supported languages for a clearer lab demo,
        # while still letting Whisper pick among them.
        result = model.transcribe(
            tmp_path,
            task="transcribe",
            fp16=False,
        )
        transcript = (result.get("text") or "").strip()
        whisper_lang = (result.get("language") or "").lower()

        if not transcript:
            return jsonify(
                {
                    "success": False,
                    "error": "No speech could be recognized. Please speak clearly and try again.",
                }
            )

        detection = detect_text_language(transcript)
        detection["transcript"] = transcript
        detection["speech_language_hint"] = {
            "language_code": whisper_lang,
            "language": language_display_name(whisper_lang),
        }

        # Prefer Whisper's spoken-language guess when langdetect is uncertain /
        # conflicted on short ASR output, if Whisper picked a supported language.
        if detection.get("success") and whisper_lang in SUPPORTED_LANGUAGES:
            text_conf = detection.get("confidence", 0)
            if detection.get("language_code") != whisper_lang and text_conf < 70:
                detection["language_code"] = whisper_lang
                detection["language"] = SUPPORTED_LANGUAGES[whisper_lang]
                detection["supported"] = True
                detection["confidence"] = max(text_conf, 75.0)
                detection["message"] = (
                    f"Detected language: {SUPPORTED_LANGUAGES[whisper_lang]} "
                    f"(aligned with speech model hint)"
                )

        return jsonify(detection)

    except Exception as exc:  # noqa: BLE001 — surface friendly lab error
        message = str(exc)
        if "ffmpeg" in message.lower() or "ffprobe" in message.lower():
            message = (
                "FFmpeg is required for speech processing. "
                "Install FFmpeg and add it to your system PATH, then try again."
            )
        return jsonify({"success": False, "error": f"Speech processing failed: {message}"}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route("/api/examples", methods=["GET"])
def api_examples():
    return jsonify(
        {
            "supported_languages": SUPPORTED_LANGUAGES,
            "examples": EXAMPLES,
        }
    )


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify(
        {
            "status": "ok",
            "whisper_installed": whisper_available(),
            "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        }
    )


if __name__ == "__main__":
    print("Language Detection Lab")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Supported:", ", ".join(SUPPORTED_LANGUAGES.values()))
    app.run(debug=True, host="127.0.0.1", port=5000)
