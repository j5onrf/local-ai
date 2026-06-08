# Local-AI Tablet Voice Bridge

<img alt="301q02301q02301" src="https://github.com/user-attachments/assets/a5476624-3323-438f-b44a-7935e1efb4f2" />

---

A zero-daemon, model-free voice-to-text pipeline that integrates any tablet (or phone) with your local-ai agent. It uses the browser-native HTML5 MediaRecorder API on the tablet to record audio, uploads it over local Wi-Fi, and transcribes it using your Gemini key (0% idle PC CPU, 0MB local models).

---

## 1. Save and Configure the Script

Save your voice-query Python script to:
`$HOME/.config/local-ai/voice/voice-query`

Make the script executable:
```bash
chmod +x $HOME/.config/local-ai/voice/voice-query
```

---

## 2. Register the Shortcut

Add this line to Section 4 of your `~/.config/local-ai/local-ai-agent/ai-context.txt`:

```text
# --- Local-Ai Tablet Voice Bridge ---
$HOME/.config/local-ai/voice/voice-query ---> voice, voice query, voice bridge
```

---

## 3. Run and Connect

Ensure your API key is exported:
```bash
export GEMINI_API_KEY="AIzaSyYourGeminiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"
```

Start the bridge on your PC:
```bash
voice
```

Open your tablet's web browser and navigate to the secure HTTPS URL printed in your terminal:
```text
https://[Your-PC-IP]:9999
```

Bypass the browser's self-signed warning (Advanced -> Proceed). Grant microphone permissions when prompted. Hold the button to speak, and release to execute.
```
