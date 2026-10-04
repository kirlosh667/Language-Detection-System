# Language Detection Lab

A Flask web application for **text and speech language detection**, designed for a college NLP and speech processing lab.

## Features

- Enter text and detect its language automatically
- Record speech, convert it to text (Whisper), then detect the language
- Supports **English, Tamil, Hindi, Telugu, Malayalam**
- Shows detected language name, code, and confidence score
- Handles unsupported languages with a clear warning
- One-click example sentences for each supported language

## Tech stack

| Part | Library |
|------|---------|
| Web framework | Flask |
| Text language detection | [`langdetect`](https://pypi.org/project/langdetect/) |
| Speech-to-text | [OpenAI Whisper](https://github.com/openai/whisper) (`tiny` model) |

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your PATH (needed for speech)

### Install FFmpeg on Windows

1. Download a build from https://www.gyan.dev/ffmpeg/builds/ (release essentials zip)
2. Extract and add the `bin` folder to your system PATH
3. Confirm with:

```bash
ffmpeg -version
```

## Setup

```bash
cd TSA9
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

> The first speech detection request downloads the Whisper `tiny` model (~75 MB) and may take a minute.

## How to use

### Text

1. Type or paste text, or click an example language button
2. Click **Detect language**
3. View language, confidence, and support status

### Speech

1. Click **Start recording** and allow microphone access
2. Speak a short phrase (2–8 seconds)
3. Click **Stop**, then **Detect from speech**
4. Review the transcript, detected language, and confidence

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Lab UI |
| `POST` | `/api/detect-text` | JSON `{ "text": "..." }` → detection result |
| `POST` | `/api/detect-speech` | multipart `audio` file → transcript + detection |
| `GET` | `/api/examples` | Example texts and supported languages |
| `GET` | `/api/health` | Health / dependency check |

## Project structure

```
TSA9/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    └── index.html
```

## Notes for lab demos

- Short or mixed-script text can lower confidence; use full sentences when possible
- Unsupported languages are still reported when detected, with an explicit unsupported warning
- Speech quality depends on microphone, noise, and clear pronunciation
