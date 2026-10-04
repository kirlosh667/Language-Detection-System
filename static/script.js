(() => {
  const textInput = document.getElementById("text-input");
  const detectTextBtn = document.getElementById("detect-text-btn");
  const clearTextBtn = document.getElementById("clear-text-btn");
  const textResult = document.getElementById("text-result");

  const recordBtn = document.getElementById("record-btn");
  const stopBtn = document.getElementById("stop-btn");
  const detectSpeechBtn = document.getElementById("detect-speech-btn");
  const recStatus = document.getElementById("rec-status");
  const recStatusText = document.getElementById("rec-status-text");
  const recTimer = document.getElementById("rec-timer");
  const audioPlayback = document.getElementById("audio-playback");
  const speechResult = document.getElementById("speech-result");

  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];
  let recordedBlob = null;
  let timerId = null;
  let seconds = 0;

  function formatTime(totalSeconds) {
    const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const s = String(totalSeconds % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  function startTimer() {
    seconds = 0;
    recTimer.textContent = "00:00";
    timerId = setInterval(() => {
      seconds += 1;
      recTimer.textContent = formatTime(seconds);
    }, 1000);
  }

  function stopTimer() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function setRecordingUI(isRecording) {
    recStatus.classList.toggle("recording", isRecording);
    recStatusText.textContent = isRecording ? "Recording…" : "Ready to record";
    recordBtn.disabled = isRecording;
    stopBtn.disabled = !isRecording;
  }

  function renderLoading(el, message) {
    el.hidden = false;
    el.className = "result";
    el.innerHTML = `<div class="loading"><span class="spinner" aria-hidden="true"></span>${message}</div>`;
  }

  function renderError(el, message) {
    el.hidden = false;
    el.className = "result error";
    el.innerHTML = `<h3>Error</h3><p class="message">${escapeHtml(message)}</p>`;
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderDetection(el, data, { showTranscript = false } = {}) {
    if (!data.success) {
      renderError(el, data.error || "Detection failed.");
      return;
    }

    const supportedBadge = data.supported
      ? `<span style="color:var(--ok)">Supported</span>`
      : `<span style="color:var(--warn)">Unsupported</span>`;

    const conf = Number(data.confidence || 0);
    const candidates = Array.isArray(data.candidates) ? data.candidates : [];

    let html = `
      <h3>Detection result</h3>
      <div class="result-grid">
        <div class="result-item">
          <span class="label">Language</span>
          <span class="value">${escapeHtml(data.language)} (${escapeHtml(data.language_code)})</span>
        </div>
        <div class="result-item">
          <span class="label">Confidence</span>
          <span class="value">${conf.toFixed(2)}%</span>
        </div>
        <div class="result-item">
          <span class="label">Lab status</span>
          <span class="value">${supportedBadge}</span>
        </div>
      </div>
      <div class="confidence-bar" aria-hidden="true">
        <div class="track"><div class="fill" style="width:${Math.min(conf, 100)}%"></div></div>
      </div>
    `;

    if (showTranscript && data.transcript) {
      html += `
        <div class="transcript">
          <strong>Transcript</strong>
          ${escapeHtml(data.transcript)}
        </div>
      `;
    }

    if (data.speech_language_hint && data.speech_language_hint.language) {
      html += `
        <p class="message">
          Speech model language hint:
          ${escapeHtml(data.speech_language_hint.language)}
          (${escapeHtml(data.speech_language_hint.language_code)})
        </p>
      `;
    }

    if (candidates.length > 1) {
      html += `<ul class="candidates"><li><strong>Top candidates</strong></li>`;
      candidates.forEach((c) => {
        html += `<li>${escapeHtml(c.language)} — ${Number(c.confidence).toFixed(2)}%</li>`;
      });
      html += `</ul>`;
    }

    if (data.message) {
      html += `<p class="message">${escapeHtml(data.message)}</p>`;
    }

    el.hidden = false;
    el.className = data.supported ? "result ok" : "result warn";
    el.innerHTML = html;
  }

  async function detectText() {
    const text = textInput.value.trim();
    if (!text) {
      renderError(textResult, "Please enter some text to detect the language.");
      return;
    }

    renderLoading(textResult, "Detecting language…");
    detectTextBtn.disabled = true;

    try {
      const res = await fetch("/api/detect-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      renderDetection(textResult, data);
    } catch (err) {
      renderError(textResult, "Network error while detecting language.");
    } finally {
      detectTextBtn.disabled = false;
    }
  }

  document.querySelectorAll(".example-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      textInput.value = btn.dataset.text || "";
      textInput.focus();
      detectText();
    });
  });

  detectTextBtn.addEventListener("click", detectText);

  clearTextBtn.addEventListener("click", () => {
    textInput.value = "";
    textResult.hidden = true;
    textResult.innerHTML = "";
    textInput.focus();
  });

  function pickMimeType() {
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
    ];
    for (const t of types) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) {
        return t;
      }
    }
    return "";
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      renderError(speechResult, "This browser does not support microphone recording.");
      return;
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      renderError(
        speechResult,
        "Microphone access denied. Allow the mic in your browser settings and try again."
      );
      return;
    }

    audioChunks = [];
    recordedBlob = null;
    detectSpeechBtn.disabled = true;
    audioPlayback.hidden = true;
    audioPlayback.removeAttribute("src");

    const mimeType = pickMimeType();
    try {
      mediaRecorder = mimeType
        ? new MediaRecorder(mediaStream, { mimeType })
        : new MediaRecorder(mediaStream);
    } catch (err) {
      renderError(speechResult, "Could not start the audio recorder in this browser.");
      mediaStream.getTracks().forEach((t) => t.stop());
      return;
    }

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const type = mediaRecorder.mimeType || mimeType || "audio/webm";
      recordedBlob = new Blob(audioChunks, { type });
      const url = URL.createObjectURL(recordedBlob);
      audioPlayback.src = url;
      audioPlayback.hidden = false;
      detectSpeechBtn.disabled = false;
      recStatusText.textContent = "Recording saved — ready to detect";

      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
        mediaStream = null;
      }
    };

    mediaRecorder.start();
    setRecordingUI(true);
    startTimer();
    speechResult.hidden = true;
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    stopTimer();
    setRecordingUI(false);
  }

  async function detectSpeech() {
    if (!recordedBlob) {
      renderError(speechResult, "Record speech first, then click Detect from speech.");
      return;
    }

    renderLoading(
      speechResult,
      "Transcribing speech and detecting language… (first run may download the Whisper model)"
    );
    detectSpeechBtn.disabled = true;
    recordBtn.disabled = true;

    const form = new FormData();
    const extension = recordedBlob.type.includes("mp4")
      ? "mp4"
      : recordedBlob.type.includes("ogg")
        ? "ogg"
        : "webm";
    form.append("audio", recordedBlob, `recording.${extension}`);

    try {
      const res = await fetch("/api/detect-speech", {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      renderDetection(speechResult, data, { showTranscript: true });
    } catch (err) {
      renderError(speechResult, "Network error while processing speech.");
    } finally {
      detectSpeechBtn.disabled = !recordedBlob;
      recordBtn.disabled = false;
    }
  }

  recordBtn.addEventListener("click", startRecording);
  stopBtn.addEventListener("click", stopRecording);
  detectSpeechBtn.addEventListener("click", detectSpeech);

  textInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      detectText();
    }
  });
})();
