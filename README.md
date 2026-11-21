# tilawat-videos

Daily Peaceful Tilawat shorts (Sheikh Mishary Alafasy + English translation).

- `auto/build.py` builds one short (audio, word highlight, translation, subscribe card, thumbnail).
- `auto/daily.py` builds the next item of `auto/plan.json`, puts the video on the `media` branch and advances `auto/state.json`.
- Metricool then publishes it to YouTube and TikTok at 06:00 US Eastern for long videos and 08:00 US Eastern for shorts.
