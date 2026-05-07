"""
JARVIS Core - AI Brain Module
Handles: Wake word detection, Speech recognition, TTS, Command routing, AI chat
AI Backend: Groq Cloud (ultra-fast, free tier)
"""

import os
import time
import datetime
import threading
import subprocess
import platform
import webbrowser
import random
import queue
import math

# ─── Optional imports with graceful fallback ───────────────────────────────────
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("[WARN] SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[WARN] pyttsx3 not installed. Run: pip install pyttsx3")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WARN] requests not installed. Run: pip install requests")

try:
    import wikipedia
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False
    print("[WARN] wikipedia not installed. Run: pip install wikipedia")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARN] pyautogui not installed. Run: pip install pyautogui pillow")




WAKE_WORD   = "hey jarvis"
USER_NAME   = "Bhavish"             # 👈 Change to your name
DEFAULT_CITY = "Chennai"             # 👈 Change to your city for weather

# ── Groq API (free at https://console.groq.com) ────────────────────────────
GROQ_API_KEY = "GROQ_API_KEY"

GROQ_MODEL = "llama3-8b-8192"

# ── Weather API (free at https://openweathermap.org/api) ───────────────────
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")


# ── Music folder ───────────────────────────────────────────────────────────
MUSIC_FOLDER = os.path.expanduser("~/Music")   # change path if needed

# ── App launcher map (Windows / Mac / Linux) ──────────────────────────────
APP_MAP = {
    "notepad":    {"win": "notepad",                "mac": "open -a TextEdit",             "linux": "gedit"},
    "calculator": {"win": "calc",                   "mac": "open -a Calculator",           "linux": "gnome-calculator"},
    "browser":    {"win": "start msedge",           "mac": "open -a Safari",               "linux": "xdg-open https://google.com"},
    "vscode":     {"win": "code",                   "mac": "open -a 'Visual Studio Code'", "linux": "code"},
    "files":      {"win": "explorer",               "mac": "open .",                       "linux": "nautilus"},
    "terminal":   {"win": "start cmd",              "mac": "open -a Terminal",             "linux": "gnome-terminal"},
    "spotify":    {"win": "spotify",                "mac": "open -a Spotify",              "linux": "spotify"},
    "discord":    {"win": "discord",                "mac": "open -a Discord",              "linux": "discord"},
    "chrome":     {"win": "start chrome",           "mac": "open -a 'Google Chrome'",      "linux": "google-chrome"},
    "whatsapp":   {"win": "start whatsapp",         "mac": "open -a WhatsApp",             "linux": "whatsapp-desktop"},
    "paint":      {"win": "mspaint",                "mac": "open -a Preview",              "linux": "gimp"},
    "word":       {"win": "start winword",          "mac": "open -a 'Microsoft Word'",     "linux": "libreoffice --writer"},
    "excel":      {"win": "start excel",            "mac": "open -a 'Microsoft Excel'",    "linux": "libreoffice --calc"},
    "powerpoint": {"win": "start powerpnt",         "mac": "open -a 'Microsoft PowerPoint'","linux": "libreoffice --impress"},
}

# ══════════════════════════════════════════════════════════════════════════════


class JarvisCore:
    """
    Central AI engine. Dashboard calls its methods and reads its state.
    Uses Groq Cloud as the AI backend for fast, free responses.
    """

    def __init__(self):
        self.is_listening   = False
        self.is_awake       = False
        self.status_message = f"Hey {USER_NAME}! How can I help you today?"
        self.last_response  = ""
        self.mic_amplitude  = 0.0
        self.event_queue    = queue.Queue()
        self._tts_lock      = threading.Lock()

        # ── TTS engine ────────────────────────────────────────────────────────
        self._tts_engine = None
        if TTS_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                voices = self._tts_engine.getProperty("voices")
                for v in voices:
                    if "male" in v.name.lower() or "david" in v.name.lower():
                        self._tts_engine.setProperty("voice", v.id)
                        break
                self._tts_engine.setProperty("rate",   165)
                self._tts_engine.setProperty("volume", 1.0)
            except Exception as e:
                print(f"[TTS] Init error: {e}")
                self._tts_engine = None

        # ── Speech recogniser ─────────────────────────────────────────────────
        self._recogniser = sr.Recognizer() if SR_AVAILABLE else None
        if self._recogniser:
            self._recogniser.pause_threshold          = 0.8
            self._recogniser.dynamic_energy_threshold = True

        # ── Groq chat history (system prompt sets JARVIS personality) ─────────
        self._chat_history = [
            {
                "role": "system",
                "content": (
                    f"You are JARVIS, an advanced AI assistant inspired by Iron Man's JARVIS. "
                    f"The user's name is {USER_NAME}. Always address them by name occasionally. "
                    "Be concise, intelligent, and slightly witty. "
                    "Keep responses under 3 sentences for voice output unless the user asks for detail. "
                    "Never use markdown formatting like ** or # in your responses — speak naturally."
                ),
            }
        ]

        # ── Startup check ─────────────────────────────────────────────────────
        self._check_api_keys()
        print("[JARVIS] Core initialised.")

    # ──────────────────────────────────────────────────────────────────────────
    # Startup checks
    # ──────────────────────────────────────────────────────────────────────────

    def _check_api_keys(self):
        if not GROQ_API_KEY:
            print("=" * 60)
            print("  ⚠  GROQ_API_KEY not set!")
            print("  Get a free key at: https://console.groq.com")
            print("  Then paste it in jarvis_core.py at line ~40")
            print("=" * 60)
        else:
            print(f"[JARVIS] Groq API key loaded ✓  (model: {GROQ_MODEL})")

        if not WEATHER_API_KEY:
            print("[WARN]  WEATHER_API_KEY not set — weather command disabled.")
        else:
            print("[JARVIS] Weather API key loaded ✓")

    # ──────────────────────────────────────────────────────────────────────────
    # Event & status helpers
    # ──────────────────────────────────────────────────────────────────────────

    def post_event(self, event_type: str, data: str = ""):
        self.event_queue.put({"type": event_type, "data": data})

    def set_status(self, msg: str):
        self.status_message = msg
        self.post_event("status", msg)
        print(f"[STATUS] {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    # Text-to-Speech
    # ──────────────────────────────────────────────────────────────────────────

    def speak(self, text: str):
        print(f"[JARVIS] {text}")
        self.last_response = text
        self.set_status(text)
        self.post_event("speak", text)

        if self._tts_engine:
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception as e:
                    print(f"[TTS] Error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Wake-word + command loop
    # ──────────────────────────────────────────────────────────────────────────

    def start_listening(self):
        """Background thread: continuously listens for wake word then command."""
        if not SR_AVAILABLE:
            self.set_status("⚠ SpeechRecognition not installed. Install dependencies.")
            self._simulate_demo_mode()
            return

        try:
            mic = sr.Microphone()
        except Exception as e:
            self.set_status(f"⚠ No microphone found: {e}")
            self._simulate_demo_mode()
            return

        self.set_status(f"👂 Listening for '{WAKE_WORD.title()}'…")
        with mic as source:
            self._recogniser.adjust_for_ambient_noise(source, duration=1.5)

        while True:
            try:
                with mic as source:
                    self.mic_amplitude = 0.1
                    audio = self._recogniser.listen(source, timeout=3, phrase_time_limit=4)

                self.mic_amplitude = random.uniform(0.4, 0.9)
                text = self._recogniser.recognize_google(audio).lower()
                print(f"[HEARD] {text}")

                if WAKE_WORD in text:
                    self.is_awake = True
                    self.mic_amplitude = 1.0
                    self.post_event("wake", "")
                    self.speak(f"Yes {USER_NAME}, I'm listening.")
                    self._handle_command_input(mic)
                    self.is_awake = False
                    self.set_status(f"👂 Listening for '{WAKE_WORD.title()}'…")

            except sr.WaitTimeoutError:
                self.mic_amplitude = 0.0
            except sr.UnknownValueError:
                self.mic_amplitude = 0.0
            except Exception as e:
                self.mic_amplitude = 0.0
                time.sleep(0.5)

    def _handle_command_input(self, mic):
        """Record and process one command after wake word."""
        self.is_listening = True
        self.set_status("🎙 Listening for command…")
        try:
            with mic as source:
                audio = self._recogniser.listen(source, timeout=5, phrase_time_limit=8)
            command = self._recogniser.recognize_google(audio).lower()
            print(f"[COMMAND] {command}")
            self.post_event("command", command)
            self.process_command(command)
        except sr.WaitTimeoutError:
            self.speak("I didn't catch that. Please try again.")
        except sr.UnknownValueError:
            self.speak("Sorry, I couldn't understand. Could you repeat?")
        except Exception as e:
            self.speak(f"Something went wrong: {e}")
        finally:
            self.is_listening = False

    # ──────────────────────────────────────────────────────────────────────────
    # Command router
    # ──────────────────────────────────────────────────────────────────────────

    def process_command(self, command: str):
        """Route command string to the appropriate handler."""
        c = command.lower().strip()

        # ── Web / Browser ──────────────────────────────────────────────────────
        if "open youtube" in c:
            self._open_url("https://youtube.com", "Opening YouTube")
        elif "open google" in c:
            self._open_url("https://google.com", "Opening Google")
        elif "open github" in c:
            self._open_url("https://github.com", "Opening GitHub")
        elif "open reddit" in c:
            self._open_url("https://reddit.com", "Opening Reddit")
        elif "open instagram" in c:
            self._open_url("https://instagram.com", "Opening Instagram")
        elif "open twitter" in c or "open x" in c:
            self._open_url("https://x.com", "Opening X / Twitter")
        elif "open netflix" in c:
            self._open_url("https://netflix.com", "Opening Netflix")
        elif "open chatgpt" in c:
            self._open_url("https://chat.openai.com", "Opening ChatGPT")
        elif "search" in c:
            query = (c.replace("search google", "").replace("google search", "")
                      .replace("search web", "").replace("search", "").strip())
            if query:
                self._open_url(
                    f"https://google.com/search?q={query.replace(' ', '+')}",
                    f"Searching for {query}")
            else:
                self.speak("What would you like me to search for?")

        # ── System commands ────────────────────────────────────────────────────
        elif "screenshot" in c or "take screenshot" in c:
            self._take_screenshot()
        elif "shutdown" in c or "shut down" in c:
            self._shutdown()
        elif "restart" in c or "reboot" in c:
            self._restart()
        elif "sleep" in c or "hibernate" in c:
            self._sleep_system()
        elif "lock" in c and "screen" in c:
            self._lock_screen()

        # ── App launcher ───────────────────────────────────────────────────────
        elif "open" in c and any(app in c for app in APP_MAP):
            app_key = next(app for app in APP_MAP if app in c)
            self._open_app(app_key)

        # ── Music ──────────────────────────────────────────────────────────────
        elif "play music" in c or "play song" in c or "play some music" in c:
            self._play_music()
        elif "stop music" in c or "pause music" in c:
            self._stop_music()

        # ── Wikipedia ─────────────────────────────────────────────────────────
        elif "wikipedia" in c or "who is" in c or "what is" in c:
            query = (c.replace("wikipedia", "").replace("who is", "")
                      .replace("what is", "").strip())
            self._search_wikipedia(query)

        # ── Time / Date ────────────────────────────────────────────────────────
        elif any(w in c for w in ["time", "what time", "current time", "tell me the time"]):
            self._tell_time()
        elif any(w in c for w in ["date", "today's date", "what day"]):
            self._tell_date()

        # ── Weather ───────────────────────────────────────────────────────────
        elif "weather" in c:
            city = DEFAULT_CITY
            words = c.split()
            for i, w in enumerate(words):
                if w == "in" and i + 1 < len(words):
                    city = words[i + 1].capitalize()
                    break
            self._get_weather(city)

        # ── Jokes ─────────────────────────────────────────────────────────────
        elif "joke" in c or "make me laugh" in c or "funny" in c:
            self._tell_joke()

        # ── AI chat fallback → Groq ───────────────────────────────────────────
        else:
            self._ai_chat(command)

    # ──────────────────────────────────────────────────────────────────────────
    # Groq AI Chat  ← main AI engine
    # ──────────────────────────────────────────────────────────────────────────

    def _ai_chat(self, prompt: str):
        """
        Send prompt to Groq Cloud API and speak the response.
        Groq is free, extremely fast (~200 tokens/sec), no credit card needed.
        Get your key at: https://console.groq.com
        """
        if not REQUESTS_AVAILABLE:
            self.speak("Requests library not installed.")
            return

        if not GROQ_API_KEY:
            self.speak(
                "Groq API key not set. Please open jarvis core dot py "
                "and paste your Groq key at line 40."
            )
            return

        self.set_status("🤖 Thinking via Groq…")
        self._chat_history.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       GROQ_MODEL,
                    "messages":    self._chat_history,
                    "max_tokens":  200,
                    "temperature": 0.7,
                },
                timeout=15,
            )

            if resp.status_code == 200:
                answer = resp.json()["choices"][0]["message"]["content"].strip()
                self._chat_history.append({"role": "assistant", "content": answer})
                # keep history manageable (system prompt + last 10 turns)
                if len(self._chat_history) > 21:
                    self._chat_history = [self._chat_history[0]] + self._chat_history[-20:]
                self.speak(answer)

            elif resp.status_code == 401:
                self.speak("Invalid Groq API key. Please check jarvis core dot py.")
                print(f"[GROQ] 401 Unauthorized — check your GROQ_API_KEY")

            elif resp.status_code == 429:
                self.speak("Groq rate limit reached. Please wait a moment.")
                print(f"[GROQ] 429 Rate limited")

            else:
                self.speak("Groq returned an unexpected error.")
                print(f"[GROQ] Error {resp.status_code}: {resp.text}")

        except requests.exceptions.Timeout:
            self.speak("Groq took too long to respond. Please try again.")
        except requests.exceptions.ConnectionError:
            self.speak("No internet connection. Cannot reach Groq.")
        except Exception as e:
            self.speak(f"AI response failed: {e}")
            print(f"[GROQ] Exception: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Individual command handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _open_url(self, url: str, msg: str):
        self.speak(msg)
        webbrowser.open(url)

    def _take_screenshot(self):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Desktop/jarvis_screenshot_{ts}.png")
        if PYAUTOGUI_AVAILABLE:
            try:
                img = pyautogui.screenshot()
                img.save(path)
                self.speak(f"Screenshot saved to your Desktop.")
            except Exception as e:
                self.speak(f"Screenshot failed: {e}")
        else:
            sys_name = platform.system()
            try:
                if sys_name == "Darwin":
                    subprocess.run(["screencapture", path])
                    self.speak("Screenshot saved to Desktop.")
                elif sys_name == "Linux":
                    subprocess.run(["scrot", path])
                    self.speak("Screenshot saved.")
                elif sys_name == "Windows":
                    subprocess.run(["snippingtool"])
                    self.speak("Snipping tool opened.")
            except Exception as e:
                self.speak(f"Screenshot failed: {e}")

    def _shutdown(self):
        self.speak("Initiating system shutdown. Goodbye sir.")
        time.sleep(2)
        sys_name = platform.system()
        if sys_name == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "5"])
        elif sys_name in ("Linux", "Darwin"):
            subprocess.run(["sudo", "shutdown", "-h", "now"])

    def _restart(self):
        self.speak("Restarting system now.")
        time.sleep(2)
        sys_name = platform.system()
        if sys_name == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "5"])
        elif sys_name in ("Linux", "Darwin"):
            subprocess.run(["sudo", "shutdown", "-r", "now"])

    def _sleep_system(self):
        self.speak("Putting system to sleep.")
        sys_name = platform.system()
        if sys_name == "Windows":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif sys_name == "Darwin":
            subprocess.run(["pmset", "sleepnow"])
        elif sys_name == "Linux":
            subprocess.run(["systemctl", "suspend"])

    def _lock_screen(self):
        self.speak("Locking screen.")
        sys_name = platform.system()
        if sys_name == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif sys_name == "Darwin":
            subprocess.run([
                "/System/Library/CoreServices/Menu Extras/User.menu"
                "/Contents/Resources/CGSession", "-suspend"])
        elif sys_name == "Linux":
            subprocess.run(["gnome-screensaver-command", "-l"])

    def _open_app(self, app_key: str):
        sys_name = platform.system()
        os_key   = {"Windows": "win", "Darwin": "mac", "Linux": "linux"}.get(sys_name, "linux")
        cmd      = APP_MAP[app_key].get(os_key, "")
        if cmd:
            self.speak(f"Opening {app_key}.")
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                self.speak(f"Couldn't open {app_key}: {e}")
        else:
            self.speak(f"I don't know how to open {app_key} on this system.")

    def _play_music(self):
        self.speak("Playing music from your library.")
        sys_name = platform.system()
        if sys_name == "Windows":
            subprocess.Popen(f'start "" "{MUSIC_FOLDER}"', shell=True)
        elif sys_name == "Darwin":
            subprocess.Popen(["open", MUSIC_FOLDER])
        elif sys_name == "Linux":
            subprocess.Popen(["xdg-open", MUSIC_FOLDER])

    def _stop_music(self):
        self.speak("Stopping music.")
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "wmplayer.exe"])
        elif platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Music" to pause'])

    def _search_wikipedia(self, query: str):
        if not query:
            self.speak("What would you like me to look up on Wikipedia?")
            return
        self.speak(f"Searching Wikipedia for {query}.")
        if WIKI_AVAILABLE:
            try:
                result = wikipedia.summary(query, sentences=2)
                self.speak(result)
            except wikipedia.exceptions.DisambiguationError as e:
                self.speak(f"Multiple results found for {query}. Please be more specific.")
            except wikipedia.exceptions.PageError:
                self.speak(f"I couldn't find a Wikipedia page for {query}.")
            except Exception:
                self._open_url(
                    f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                    f"Opening Wikipedia for {query}")
        else:
            self._open_url(
                f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                f"Opening Wikipedia for {query}")

    def _tell_time(self):
        now = datetime.datetime.now()
        self.speak(f"The current time is {now.strftime('%I:%M %p')}.")

    def _tell_date(self):
        now = datetime.datetime.now()
        self.speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")

    def _get_weather(self, city: str):
        if not REQUESTS_AVAILABLE:
            self.speak("Requests library not installed. Cannot fetch weather.")
            return
        if not WEATHER_API_KEY:
            self.speak(
                "Weather API key not set. Get a free key from openweathermap.org "
                "and paste it in jarvis core dot py."
            )
            return
        try:
            url  = (f"https://api.openweathermap.org/data/2.5/weather"
                    f"?q={city}&appid={WEATHER_API_KEY}&units=metric")
            resp = requests.get(url, timeout=8)
            data = resp.json()
            if resp.status_code == 200:
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                hum  = data["main"]["humidity"]
                self.speak(
                    f"Weather in {city}: {desc}, {temp:.1f} degrees Celsius, "
                    f"humidity {hum} percent.")
            else:
                self.speak(f"Couldn't get weather for {city}. {data.get('message', '')}")
        except Exception as e:
            self.speak(f"Weather fetch failed: {e}")

    def _tell_joke(self):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
            "Why did the programmer quit? Because he didn't get arrays.",
            "I'm reading a book about anti-gravity. It's impossible to put down.",
            "Why do Java developers wear glasses? Because they don't C sharp.",
            "I asked my AI to tell me a joke. It said: I would, but I'm afraid it might go over your head.",
            "There are 10 types of people in the world: those who understand binary, and those who don't.",
        ]
        self.speak(random.choice(jokes))

    # ──────────────────────────────────────────────────────────────────────────
    # Demo mode (no microphone / missing deps)
    # ──────────────────────────────────────────────────────────────────────────

    def _simulate_demo_mode(self):
        """Cycles through demo responses so the dashboard stays animated."""
        demo_sequence = [
            (3,  "wake",    ""),
            (1,  "speak",   f"Hello {USER_NAME}! JARVIS online and ready."),
            (4,  "status",  f"👂 Listening for '{WAKE_WORD.title()}'…"),
            (5,  "command", "open youtube"),
            (1,  "speak",   "Opening YouTube for you."),
            (6,  "status",  f"👂 Listening for '{WAKE_WORD.title()}'…"),
            (5,  "command", "what is the time"),
            (1,  "speak",   f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."),
            (6,  "status",  f"👂 Listening for '{WAKE_WORD.title()}'…"),
            (5,  "wake",    ""),
            (1,  "speak",   "Groq AI is ready. Set your API key to activate AI chat."),
            (5,  "status",  f"👂 Listening for '{WAKE_WORD.title()}'…"),
        ]
        while True:
            for delay, etype, data in demo_sequence:
                time.sleep(delay)
                if etype == "speak":
                    self.last_response = data
                    self.mic_amplitude = random.uniform(0.5, 1.0)
                elif etype == "wake":
                    self.is_awake = True
                    self.mic_amplitude = 1.0
                elif etype == "command":
                    self.mic_amplitude = random.uniform(0.6, 1.0)
                elif etype == "status":
                    self.mic_amplitude = 0.05
                    self.is_awake = False
                self.post_event(etype, data)
                if etype in ("status", "speak"):
                    self.status_message = data
