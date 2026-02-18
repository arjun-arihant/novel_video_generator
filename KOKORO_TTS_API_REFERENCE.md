# Kokoro TTS — API Reference

> **Service**: Kokoro-82M Neural Text-to-Speech  
> **Base URL**: `http://localhost:8000`  
> **Protocol**: REST (JSON) + SSE for streaming  
> **CORS**: Enabled for all origins  
> **Model**: Kokoro-82M — 82M param neural TTS, 24kHz sample rate

---

## Quick Start

```javascript
// Simplest usage — generate audio from text
const response = await fetch('http://localhost:8000/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'Hello world!',
    voice: 'af_heart',
    speed: 1.0,
    format: 'wav'
  })
});
const audioBlob = await response.blob();
const audioUrl = URL.createObjectURL(audioBlob);
```

```python
# Python equivalent
import requests

response = requests.post('http://localhost:8000/generate', json={
    'text': 'Hello world!',
    'voice': 'af_heart',
    'speed': 1.0,
    'format': 'wav'
})
with open('output.wav', 'wb') as f:
    f.write(response.content)
```

---

## Available Voices

> **Source:** [Official VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) from `hexgrad/Kokoro-82M` on HuggingFace.

Voice IDs follow the pattern `{lang_code}{gender}_{name}` — e.g., `af_heart` = American English (`a`), Female (`f`), "Heart".

**Grading system:**
- **Target Quality** — quality of reference voice audio and text/audio alignment
- **Training Duration** — `HH` = 10–100 hrs, `H` = 1–10 hrs, `MM` = 10–100 min, `M` = 1–10 min
- **Overall Grade** — combined quality assessment (A through F)

**Performance notes:**
- Most voices sound best at **100–200 tokens** out of ~500 max
- Short utterances (<10–20 tokens) may perform worse — bundle short texts together
- Long utterances (>400 tokens) may sound rushed — split into shorter chunks or lower `speed`

---

### 🇺🇸 American English — `lang_code='a'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `af_heart` | F | **A** | ❤️ Warm, conversational, natural breathiness with a welcoming "smile" in tone. Young adult, ~177 WPM. Flagship voice. |
| `af_bella` | F | A- | 🔥 Intimate and natural with a slightly husky texture. Subtle vocal fry, modern personality. ~168 WPM. |
| `af_nicole` | F | B- | 🎧 Whisper-soft, deeply intimate. Ideal for ASMR/relaxation. Very slow (~117 WPM), breathy, comforting. |
| `af_aoede` | F | C+ | Clear and melodic female voice with balanced tone. Good for general narration. |
| `af_kore` | F | C+ | Clean, neutral female voice suitable for assistants and information delivery. |
| `af_sarah` | F | C+ | Clear and friendly, confident educator tone. Great for e-learning and assistants. ~173 WPM. |
| `af_alloy` | F | C | Versatile general-purpose female voice with a balanced, neutral tone. |
| `af_nova` | F | C | Natural and approachable. Good for assistants, guides, and e-learning. ~193 WPM. |
| `af_jessica` | F | D | Bright and energetic young adult. Fast conversational pace (~206 WPM), warm, breathy texture. |
| `af_river` | F | D | Soft and flowing with a gentle, smooth delivery. |
| `af_sky` | F | C- | Polished and approachable, blends professional clarity with warmth. ~183 WPM. |
| `am_fenrir` | M | C+ | Energetic and clear. Ideal for explainers, tech demos, upbeat content. ~173 WPM. |
| `am_michael` | M | C+ | Warm, conversational tone. Well-suited for narration and storytelling. ~157 WPM. |
| `am_puck` | M | C+ | Energetic and youthful. Great for gaming, tech demos, modern apps. ~176 WPM. |
| `am_adam` | M | F+ | Polished and trustworthy, professional clarity with neighborly warmth. Low pitch, ~184 WPM. |
| `am_echo` | M | D | Mid-range male voice with balanced delivery. General-purpose. |
| `am_eric` | M | D | Clear and neutral male voice for straightforward narration. |
| `am_liam` | M | D | Friendly and conversational male voice with approachable tone. |
| `am_onyx` | M | D | Rich and sophisticated, deep male voice with authority. |
| `am_santa` | M | D- | Novelty/character voice with a distinctive older quality. |

### 🇬🇧 British English — `lang_code='b'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `bf_emma` | F | B- | Warm, professional, and friendly British accent. Best for assistants and narration. ~185 WPM. |
| `bf_isabella` | F | C | Warm and articulate with a gentle, breathy quality. Polished yet intimate. ~185 WPM. |
| `bf_alice` | F | D | Refined and elegant British female voice. |
| `bf_lily` | F | D | Sweet and gentle with a warm, articulate delivery. ~184 WPM. |
| `bm_fable` | M | C | Refined and velvety, natural storytelling cadence. Evokes trust and sophistication. ~194 WPM. |
| `bm_george` | M | C | Classic British accent, mature male voice. Great for e-learning and narration. ~165 WPM. |
| `bm_daniel` | M | D | Crisp and articulate, balances professional polish with approachable warmth. ~194 WPM. |
| `bm_lewis` | M | D+ | Traditional British male voice with a measured, steady delivery. |

### 🇯🇵 Japanese — `lang_code='j'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `jf_alpha` | F | C+ | Primary Japanese female voice with natural intonation. Best quality in Japanese. |
| `jf_gongitsune` | F | C | Female voice trained on the "Gon, the Little Fox" story narration. |
| `jf_tebukuro` | F | C | Female voice trained on the "Buying Mittens" story narration. |
| `jf_nezumi` | F | C- | Female voice from "The Mouse's Marriage" narration. Limited training data. |
| `jm_kumo` | M | C- | Male voice from "The Spider's Thread" narration. Limited training data. |

### 🇨🇳 Mandarin Chinese — `lang_code='z'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `zf_xiaobei` | F | D | Chinese female voice with a standard Mandarin accent. |
| `zf_xiaoni` | F | D | Gentle Chinese female voice. |
| `zf_xiaoxiao` | F | D | Bright and youthful Chinese female voice. |
| `zf_xiaoyi` | F | D | Clear Chinese female voice for general use. |
| `zm_yunjian` | M | D | Strong Chinese male voice. |
| `zm_yunxi` | M | D | Youthful Chinese male voice. |
| `zm_yunxia` | M | D | Standard Mandarin male voice. |
| `zm_yunyang` | M | D | Professional Chinese male voice for news/narration. |

### 🇪🇸 Spanish — `lang_code='e'`

| Voice ID | Gender | Description |
| -------- | ------ | ----------- |
| `ef_dora` | F | Spanish female voice with natural Castilian pronunciation. |
| `em_alex` | M | Spanish male voice with clear, conversational delivery. |
| `em_santa` | M | Spanish male voice with a distinctive character quality. |

### 🇫🇷 French — `lang_code='f'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `ff_siwis` | F | B- | French female voice from the SIWIS dataset. Clear and natural French pronunciation. |

### 🇮🇳 Hindi — `lang_code='h'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `hf_alpha` | F | C | Primary Hindi female voice with natural Hindi intonation. |
| `hf_beta` | F | C | Alternative Hindi female voice. |
| `hm_omega` | M | C | Hindi male voice with clear pronunciation. |
| `hm_psi` | M | C | Alternative Hindi male voice. |

### 🇮🇹 Italian — `lang_code='i'`

| Voice ID | Gender | Grade | Description |
| -------- | ------ | ----- | ----------- |
| `if_sara` | F | C | Italian female voice with natural Italian intonation and pacing. |
| `im_nicola` | M | C | Italian male voice with clear, conversational delivery. |

### 🇧🇷 Brazilian Portuguese — `lang_code='p'`

| Voice ID | Gender | Description |
| -------- | ------ | ----------- |
| `pf_dora` | F | Brazilian Portuguese female voice. |
| `pm_alex` | M | Brazilian Portuguese male voice. |
| `pm_santa` | M | Brazilian Portuguese male voice with character quality. |

### Recommended Voices

For best results, prefer voices with higher overall grades:

| Use Case                | Recommended Voice | Grade | Notes                      |
| ----------------------- | ----------------- | ----- | -------------------------- |
| **Best overall**        | `af_heart`        | A     | Top-rated, flagship voice  |
| **Best female alt**     | `af_bella`        | A-    | Rich, warm tone            |
| **Best British female** | `bf_emma`          | B-    | Most training data in UK   |
| **Best male**           | `am_fenrir`       | C+    | Best-graded male voice     |
| **French**              | `ff_siwis`        | B-    | Only French voice          |
| **Best female w/ headphones** | `af_nicole` | B-    | 🎧 headphone-optimized    |

---

## Endpoints

### `GET /health`

Health check and model info.

**Response:**
```json
{
  "status": "ok",
  "model": "Kokoro-82M",
  "version": "2.0.0",
  "loaded_languages": ["a"],
  "total_builtin_voices": 54,
  "custom_voices": 0,
  "supported_formats": ["wav", "mp3", "ogg", "flac"],
  "max_text_length": 10000
}
```

---

### `GET /voices`

List available voices. Optionally filter by language.

**Query Parameters:**

| Param  | Type   | Required | Description                       |
| ------ | ------ | -------- | --------------------------------- |
| `lang` | string | No       | Language code to filter (`a`, `b`, `j`, etc.) |

**Response:**
```json
{
  "languages": {
    "a": {
      "name": "American English",
      "flag": "🇺🇸",
      "voices": [
        { "id": "af_heart", "name": "Heart", "gender": "female" },
        { "id": "am_adam", "name": "Adam", "gender": "male" }
      ]
    }
  },
  "custom_voices": [
    { "id": "custom_myvoice", "name": "myvoice", "gender": "unknown", "custom": true }
  ]
}
```

---

### `POST /generate`

Synthesize speech from text. Returns binary audio data.

**Request Body:**

| Field           | Type   | Default      | Description                                         |
| --------------- | ------ | ------------ | --------------------------------------------------- |
| `text`          | string | *required*   | Text to speak                                       |
| `voice`         | string | `af_heart`   | Voice ID                                            |
| `speed`         | float  | `1.0`        | Speech rate (0.5–2.0)                               |
| `format`        | string | `wav`        | Output format: `wav`, `mp3`, `ogg`, `flac`          |
| `lang`          | string | `null`       | Language code. Auto-detected from voice ID if omitted |
| `split_pattern` | string | `null`       | Regex for text splitting. Default: split on `\n+`   |

**Response:** Binary audio file with appropriate MIME type.

**Example:**
```javascript
const res = await fetch('http://localhost:8000/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Hello world!', voice: 'af_heart', format: 'mp3' })
});
// res.headers['content-type'] → 'audio/mpeg'
const blob = await res.blob();
```

---

### `POST /generate/stream`

**Real-time streaming synthesis via Server-Sent Events (SSE).**

Text is split into sentences and each segment's audio is sent immediately as it's synthesized — not buffered. Ideal for long text where you want audio to start playing within seconds.

**Request Body:** Same as `/generate`.

> **Note:** When streaming, the default `split_pattern` is `[.!?;:。！？；：]+` (sentence-level) for granular delivery.

**SSE Event Format:**

Each event is a `data:` line containing JSON:

#### Chunk Event (one per segment)
```
data: {"type":"chunk","index":0,"graphemes":"Hello world!","phonemes":"həˈloʊ wˈɜːld","audio_base64":"UklGRi4A...","mime_type":"audio/wav","format":"wav"}
```

#### Done Event (signals completion)
```
data: {"type":"done"}
```

#### Error Event
```
data: {"error":"Error description"}
```

**SSE Fields (chunk):**

| Field          | Type   | Description                                |
| -------------- | ------ | ------------------------------------------ |
| `type`         | string | Always `"chunk"`                           |
| `index`        | int    | Segment index (0-based)                    |
| `graphemes`    | string | Original text of this segment              |
| `phonemes`     | string | Phoneme representation                     |
| `audio_base64` | string | Base64-encoded audio for this segment only |
| `mime_type`    | string | MIME type (e.g., `audio/wav`)              |
| `format`       | string | Audio format name                          |

**JavaScript SSE Client Example:**
```javascript
async function streamTTS(text, voice, onChunk, onDone) {
  const res = await fetch('http://localhost:8000/generate/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice, speed: 1.0, format: 'wav' })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      const trimmed = line.replace(/\r/g, '').trim();
      if (!trimmed.startsWith('data: ')) continue;
      const data = JSON.parse(trimmed.slice(6));

      if (data.type === 'chunk') {
        // Decode and play this segment immediately
        const binary = atob(data.audio_base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        onChunk(bytes, data);
      } else if (data.type === 'done') {
        onDone();
        return;
      }
    }
  }
}
```

**Python SSE Client Example:**
```python
import requests
import json
import base64

def stream_tts(text, voice='af_heart'):
    response = requests.post(
        'http://localhost:8000/generate/stream',
        json={'text': text, 'voice': voice, 'speed': 1.0, 'format': 'wav'},
        stream=True
    )

    for line in response.iter_lines():
        line = line.decode('utf-8').strip()
        if not line.startswith('data: '):
            continue
        data = json.loads(line[6:])

        if data.get('type') == 'chunk':
            audio_bytes = base64.b64decode(data['audio_base64'])
            print(f"Segment {data['index']}: {data['graphemes'][:50]}... ({len(audio_bytes)} bytes)")
            # Save or play audio_bytes immediately
            yield audio_bytes

        elif data.get('type') == 'done':
            print("Stream complete")
            return
```

**Web Audio API — Immediate Playback:**
```javascript
// Play each segment immediately as it arrives, with no gaps between segments
const audioCtx = new AudioContext();
let nextStartTime = 0;

async function playChunk(audioBytes) {
  const arrayBuffer = audioBytes.buffer.slice(0);
  const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
  const source = audioCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioCtx.destination);
  const startTime = Math.max(audioCtx.currentTime, nextStartTime);
  source.start(startTime);
  nextStartTime = startTime + audioBuffer.duration;
}

// Pause:  audioCtx.suspend()
// Resume: audioCtx.resume()
// Stop:   audioCtx.close()
```

---

### `POST /generate/phonemes`

Synthesize speech and return audio + phoneme data as JSON (base64-encoded audio).

**Request Body:** Same as `/generate`.

**Response:**
```json
{
  "audio_base64": "UklGRi4AAABXQVZFZm10...",
  "audio_format": "wav",
  "mime_type": "audio/wav",
  "sample_rate": 24000,
  "segments": [
    { "graphemes": "Hello world!", "phonemes": "həˈloʊ wˈɜːld" }
  ]
}
```

**When to use:** Use this endpoint when you need both the audio AND text-to-phoneme mapping (e.g., for subtitle/caption sync, pronunciation display, or debugging).

---

### `POST /phonemes`

Convert text to phonemes **without generating audio**. Fast and lightweight.

**Request Body:**

| Field   | Type   | Default    | Description        |
| ------- | ------ | ---------- | ------------------ |
| `text`  | string | *required* | Text to convert    |
| `lang`  | string | `a`        | Language code       |
| `voice` | string | `af_heart` | Voice ID            |

**Response:**
```json
{
  "segments": [
    { "graphemes": "Hello world!", "phonemes": "həˈloʊ wˈɜːld" }
  ]
}
```

---

### `POST /generate/batch`

Generate multiple audio files at once. Returns a ZIP archive.

**Request Body:**

| Field    | Type   | Default | Description                     |
| -------- | ------ | ------- | ------------------------------- |
| `items`  | array  | *required* | Array of items (max 20)      |
| `format` | string | `wav`   | Audio format for all items      |

Each item in `items`:

| Field   | Type   | Default    | Description       |
| ------- | ------ | ---------- | ----------------- |
| `text`  | string | *required* | Text to speak     |
| `voice` | string | `af_heart` | Voice ID          |
| `speed` | float  | `1.0`      | Speech rate       |
| `lang`  | string | `null`     | Language code     |

**Response:** ZIP file containing `output_000.wav`, `output_001.wav`, etc.

```python
import requests, zipfile, io

res = requests.post('http://localhost:8000/generate/batch', json={
    'items': [
        {'text': 'First sentence.', 'voice': 'af_heart'},
        {'text': 'Second sentence.', 'voice': 'am_adam'},
    ],
    'format': 'wav'
})

with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    for name in zf.namelist():
        print(f"Extracted: {name}")
        zf.extract(name, 'output/')
```

---

### `POST /voices/mix`

Mix 2–5 voices and generate a preview.

**Request Body:**

| Field    | Type     | Default    | Description                |
| -------- | -------- | ---------- | -------------------------- |
| `voices` | string[] | *required* | 2–5 voice IDs to mix      |
| `text`   | string   | test text  | Text for preview           |
| `speed`  | float    | `1.0`      | Speech rate                |
| `format` | string   | `wav`      | Audio format               |
| `lang`   | string   | `null`     | Language (auto-detect)     |

**Response:** Binary audio file.

```javascript
const res = await fetch('http://localhost:8000/voices/mix', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    voices: ['af_heart', 'af_bella'],
    text: 'Testing voice mix.',
    format: 'wav'
  })
});
```

---

### `POST /voices/upload`

Upload a custom `.pt` voice tensor file.

**Request:** `multipart/form-data` with a single `file` field.

**Response:**
```json
{
  "message": "Voice uploaded successfully",
  "voice_id": "custom_myvoice",
  "filename": "myvoice.pt"
}
```

Use the returned `voice_id` (prefixed with `custom_`) in any generation endpoint.

---

## Audio Specifications

| Property     | Value                          |
| ------------ | ------------------------------ |
| Sample Rate  | 24,000 Hz                      |
| Channels     | Mono (1 channel)               |
| Bit Depth    | 16-bit (WAV), varies for others|
| Formats      | `wav`, `mp3`, `ogg`, `flac`    |

---

## Error Handling

All errors return JSON with a `detail` field:

```json
{ "detail": "Text is required" }
```

| Status | Meaning                                    |
| ------ | ------------------------------------------ |
| `400`  | Bad request (empty text, invalid format)   |
| `404`  | Voice or resource not found                |
| `422`  | Validation error (speed out of range, etc) |
| `500`  | Synthesis failure                          |

---

## Integration Checklist

- [ ] Service running at `http://localhost:8000`
- [ ] Verify with `GET /health` → `{"status": "ok"}`
- [ ] Choose a voice from `/voices` or use default `af_heart`
- [ ] For short text (< 1 paragraph): use `POST /generate`
- [ ] For long text (real-time playback): use `POST /generate/stream` with SSE
- [ ] For audio + phoneme data: use `POST /generate/phonemes`
- [ ] For bulk processing: use `POST /generate/batch`
- [ ] Handle errors via `detail` field in JSON responses
