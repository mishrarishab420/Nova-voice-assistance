import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")

import os
import sys
import time
import datetime
import webbrowser
import subprocess
import requests
import json
import wikipedia
import pyjokes
import pyautogui
import psutil
import random
import speech_recognition as sr
import pyttsx3
import platform
import re
import math
from bs4 import BeautifulSoup
from pygame import mixer
from threading import Thread
from configparser import ConfigParser
from gtts import gTTS  # For macOS compatible TTS
import tempfile  # For temporary audio files


# Configuration
config = ConfigParser()
config.read('config.ini')

# Constants
WAKE_WORDS = ['hey nova', 'nova']
WEATHER_API_KEY = config.get('api_keys', 'openweathermap', fallback='')
NEWS_API_KEY = config.get('api_keys', 'newsapi', fallback='')

# OS Detection
IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'

class NovaVoiceAssistant:
    def __init__(self):
        # Initialize speech components
        if IS_MAC:
            # macOS native speech doesn't need initialization
            self.speech_engine = 'macos_say'
        else:
            try:
                self.engine = pyttsx3.init()
                self.speech_engine = 'pyttsx3'
                self.set_voice_properties()
            except Exception as e:
                print(f"pyttsx3 initialization failed: {e}")
                self.speech_engine = 'gtts'  # Fallback to gTTS
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        with self.microphone as source:
            print("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
        # Initialize audio mixer
        mixer.init()
        
        # State variables
        self.listening = False
        self.last_command_time = time.time()
        self.command_timeout = 30  # seconds
        self.volume = 0.7  # Default volume (0.0 to 1.0)
        
        # Error responses variety
        self.error_responses = [
            "I didn't quite catch that. Could you repeat?",
            "Sorry, I didn't understand that.",
            "My apologies, I'm having trouble understanding.",
            "Could you say that again?",
            "I'm not sure I got that.",
            "Let me try that again. What was that?",
            "I missed that. Can you repeat please?"
        ]
        
        # User preferences
        self.user_name = config.get('user', 'name', fallback='')
        self.preferred_language = config.get('user', 'language', fallback='english')
        
        # Create necessary directories
        self.create_data_directories()
        
        # Set up system paths
        self.setup_system_paths()
        
    def set_voice_properties(self):
        """Set the voice properties for the assistant."""
        if hasattr(self, 'engine'):
            voices = self.engine.getProperty('voices')
            
            # Set US English female voice if available
            for voice in voices:
                if 'english_us' in voice.id.lower() or 'english' in voice.id.lower() and 'female' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    self.engine.setProperty('rate', 150)  # Speed percent
                    self.engine.setProperty('volume', self.volume)
                    break
            
            # If no US English female found, use first available English voice
            else:
                for voice in voices:
                    if 'english' in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
    
    def create_data_directories(self):
        """Create necessary directories for data storage."""
        directories = ['data/notes', 'data/reminders', 'data/alarms', 'data/music']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def setup_system_paths(self):
        """Set up common system paths for application launching."""
        self.system_paths = {}
        
        if IS_WINDOWS:
            self.system_paths.update({
                'notepad': 'notepad.exe',
                'calculator': 'calc.exe',
                'paint': 'mspaint.exe',
                'cmd': 'cmd.exe',
                'word': 'winword.exe',
                'excel': 'excel.exe',
                'powerpoint': 'powerpnt.exe',
                'chrome': os.path.expandvars('%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe'),
                'firefox': os.path.expandvars('%ProgramFiles%\\Mozilla Firefox\\firefox.exe'),
                'edge': 'msedge.exe'
            })
            
            # Try to find actual paths for common applications
            common_paths = {
                'chrome': [
                    os.path.expandvars('%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe'),
                    os.path.expandvars('%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe')
                ],
                'spotify': [
                    os.path.expandvars('%APPDATA%\\Spotify\\Spotify.exe'),
                    os.path.expandvars('%ProgramFiles%\\Spotify\\Spotify.exe')
                ],
                'whatsapp': [
                    os.path.expandvars('%LOCALAPPDATA%\\WhatsApp\\WhatsApp.exe')
                ]
            }
            
            for app, paths in common_paths.items():
                for path in paths:
                    if os.path.exists(path):
                        self.system_paths[app] = path
                        break
            
        elif IS_MAC:
            self.system_paths.update({
                'notepad': 'open -a TextEdit',
                'calculator': 'open -a Calculator',
                'terminal': 'open -a Terminal',
                'chrome': 'open -a "Google Chrome"',
                'firefox': 'open -a Firefox',
                'safari': 'open -a Safari',
                'spotify': 'open -a Spotify',
                'whatsapp': 'open -a WhatsApp',
                'mail': 'open -a Mail',
                'messages': 'open -a Messages'
            })
    
    def speak(self, text, language='en'):
        """Cross-platform text-to-speech implementation"""
        try:
            if IS_MAC and self.speech_engine == 'macos_say':
                # Use macOS native say command
                os.system(f'say "{text}"')
            elif self.speech_engine == 'pyttsx3' and hasattr(self, 'engine'):
                # Use pyttsx3 for Windows
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                # Use gTTS as fallback
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=True) as fp:
                    tts = gTTS(text=text, lang=language)
                    tts.save(fp.name)
                    if mixer.get_init() is None:
                        mixer.init()
                    mixer.music.load(fp.name)
                    mixer.music.play()
                    while mixer.music.get_busy():
                        time.sleep(0.1)
        except Exception as e:
            print(f"Speech error: {e}")
            # Fallback to printing if speech fails
            print(f"Assistant: {text}")
    
    def listen(self):
        """Listen for audio input and return recognized text."""
        with self.microphone as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source, phrase_time_limit=5)
        
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"Recognized: {text}")
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None
    
    def greet(self):
        """Greet the user based on time of day."""
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 21:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        if self.user_name:
            greeting += f", {self.user_name}"
        
        self.speak(f"{greeting}. I'm Nova, your voice assistant. How can I help you today?")

    def solve_math(self, problem):
        """Solve basic math problems."""
        try:
            # Remove words and keep only math expression
            cleaned = re.sub(r'[^\d+\-*/().]', '', problem)
            result = eval(cleaned)
            self.speak(f"The answer is {result}")
        except:
            self.speak("Sorry, I couldn't solve that math problem")
    
    def process_command(self, command):
        """Process the user command and execute appropriate action."""
        if not command:
            return False
        
        self.last_command_time = time.time()
        
        # System commands
        if any(word in command for word in ['open', 'launch', 'start']):
            self.open_application(command)
        elif any(word in command for word in ['close', 'exit', 'quit', 'stop']):
            self.close_application(command)
        elif 'search' in command:
            self.search_web(command)
        elif 'wikipedia' in command or 'wiki' in command:
            self.search_wikipedia(command)
        elif 'weather' in command:
            self.get_weather(command)
        elif 'news' in command:
            self.get_news(command)
        elif 'time' in command:
            self.get_time()
        elif 'date' in command:
            self.get_date()
        elif 'joke' in command:
            self.tell_joke()
        elif any(word in command for word in ['note', 'remember', 'write down']):
            self.take_note(command)
        elif 'reminder' in command:
            self.set_reminder(command)
        elif 'alarm' in command:
            self.set_alarm(command)
        elif 'volume' in command:
            self.adjust_volume(command)
        elif 'brightness' in command:
            self.adjust_brightness(command)
        elif 'screenshot' in command:
            self.take_screenshot()
        elif any(phrase in command for phrase in ['play music', 'play song', 'play some music']):
            self.play_music()
        elif any(phrase in command for phrase in ['pause music', 'stop music', 'pause the music']):
            self.pause_music()
        elif 'next song' in command:
            self.next_song()
        elif any(phrase in command for phrase in ['shutdown', 'shut down', 'turn off computer']):
            self.shutdown_system()
        elif 'restart' in command:
            self.restart_system()
        elif any(phrase in command for phrase in ['sleep', 'put to sleep']):
            self.sleep_system()
        elif any(phrase in command for phrase in ['lock', 'lock computer', 'lock screen']):
            self.lock_system()
        elif 'who are you' in command:
            self.speak("I'm Nova, your personal voice assistant. I'm here to help you with various tasks.")
        elif 'how are you' in command:
            self.speak("I'm functioning optimally, thank you for asking. How can I assist you?")
        elif any(phrase in command for phrase in ['thank you', 'thanks']):
            responses = ["You're welcome!", "My pleasure!", "Happy to help!", "Anytime!"]
            self.speak(random.choice(responses))
        elif 'your name' in command:
            self.speak("My name is Nova. I'm your voice assistant.")
        elif any(phrase in command for phrase in ['change language', 'hindi', 'switch to hindi']):
            self.change_language(command)
        elif any(phrase in command for phrase in ['what can you do', 'your capabilities', 'help']):
            self.list_capabilities()
        elif any(phrase in command for phrase in ['exit', 'goodbye', 'bye', 'see you later']):
            self.speak("Goodbye! Have a great day.")
            sys.exit(0)
        elif 'math' in command or 'calculate' in command:
            self.solve_math(command)
        else:
            self.speak(random.choice(self.error_responses))
            return False
        
        return True
    
    def open_application(self, command):
        """Open the specified application."""
        apps = {
            'notepad': 'notepad',
            'calculator': 'calculator',
            'paint': 'paint',
            'command prompt': 'cmd',
            'terminal': 'terminal',
            'word': 'word',
            'excel': 'excel',
            'powerpoint': 'powerpoint',
            'chrome': 'chrome',
            'firefox': 'firefox',
            'edge': 'edge',
            'safari': 'safari',
            'spotify': 'spotify',
            'whatsapp': 'whatsapp',
            'mail': 'mail',
            'messages': 'messages'
        }
        
        for app_name, app_key in apps.items():
            if app_name in command:
                if app_key in self.system_paths:
                    try:
                        if IS_MAC and isinstance(self.system_paths[app_key], str) and self.system_paths[app_key].startswith('open -a'):
                            subprocess.Popen(self.system_paths[app_key], shell=True)
                        else:
                            subprocess.Popen(self.system_paths[app_key])
                        self.speak(f"Opening {app_name}")
                    except Exception as e:
                        self.speak(f"Sorry, I couldn't open {app_name}. Error: {str(e)}")
                else:
                    self.speak(f"I don't know how to open {app_name} on this system.")
                return
        
        # If no specific app found, try to open a website
        if 'website' in command or 'open' in command:
            websites = {
                'youtube': 'https://youtube.com',
                'google': 'https://google.com',
                'facebook': 'https://facebook.com',
                'twitter': 'https://twitter.com',
                'instagram': 'https://instagram.com',
                'linkedin': 'https://linkedin.com',
                'github': 'https://github.com',
                'amazon': 'https://amazon.com',
                'netflix': 'https://netflix.com'
            }
            
            for site_name, site_url in websites.items():
                if site_name in command:
                    webbrowser.open(site_url)
                    self.speak(f"Opening {site_name}")
                    return
            
            # If no known website, try to extract a URL
            try:
                url_start = command.find('open') + 4 if 'open' in command else command.find('website') + 7
                url = command[url_start:].strip()
                if '.' not in url:
                    url += '.com'
                if not url.startswith('http'):
                    url = 'https://' + url
                webbrowser.open(url)
                self.speak(f"Opening {url}")
            except:
                self.speak("I couldn't determine what you want me to open.")
        
        else:
            self.speak("I'm not sure which application you want me to open.")
    
    def close_application(self, command):
        """Close the specified application."""
        apps = {
            'notepad': 'notepad.exe',
            'calculator': 'calculator.exe',
            'paint': 'mspaint.exe',
            'command prompt': 'cmd.exe',
            'terminal': 'Terminal',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'powerpoint': 'powerpnt.exe',
            'chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'edge': 'msedge.exe',
            'safari': 'Safari',
            'spotify': 'spotify.exe',
            'whatsapp': 'whatsapp.exe'
        }
        
        for app_name, process_name in apps.items():
            if app_name in command:
                try:
                    if IS_WINDOWS:
                        os.system(f'taskkill /f /im {process_name}')
                    elif IS_MAC:
                        os.system(f'pkill -f {process_name}')
                    self.speak(f"Closing {app_name}")
                except Exception as e:
                    self.speak(f"Sorry, I couldn't close {app_name}. Error: {str(e)}")
                return
        
        if 'yourself' in command or 'nova' in command:
            self.speak("Goodbye! Have a great day.")
            sys.exit(0)
        
        self.speak("I'm not sure which application you want me to close.")
    
    def search_web(self, command):
        """Search the web using the default browser."""
        query_start = command.find('search for') + 10 if 'search for' in command else command.find('search') + 6
        query = command[query_start:].strip()
        
        if query:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            self.speak(f"Here are the search results for {query}")
        else:
            self.speak("What would you like me to search for?")
    
    def search_wikipedia(self, command):
        """Search Wikipedia for information."""
        query_start = command.find('wikipedia') + 9 if 'wikipedia' in command else command.find('wiki') + 4
        query = command[query_start:].strip()
        
        if not query:
            self.speak("What would you like me to search on Wikipedia?")
            return
        
        try:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(query, sentences=2)
            self.speak(f"According to Wikipedia: {summary}")
        except wikipedia.exceptions.DisambiguationError as e:
            self.speak(f"There are multiple options for {query}. Could you be more specific?")
        except wikipedia.exceptions.PageError:
            self.speak(f"I couldn't find any information about {query} on Wikipedia.")
        except Exception as e:
            self.speak(f"Sorry, I encountered an error while searching Wikipedia: {str(e)}")
    
    def get_weather(self, command):
        """Get weather information for a location."""
        if not WEATHER_API_KEY:
            self.speak("Weather functionality is not configured. Please set up an API key in the config file.")
            return
        
        location_start = command.find('weather in') + 10 if 'weather in' in command else command.find('weather') + 7
        location = command[location_start:].strip()
        
        if not location:
            self.speak("For which location would you like the weather?")
            return
        
        try:
            base_url = "http://api.openweathermap.org/data/2.5/weather?"
            complete_url = f"{base_url}appid={WEATHER_API_KEY}&q={location}"
            response = requests.get(complete_url)
            data = response.json()
            
            if data["cod"] != "404":
                main_data = data["main"]
                temperature = main_data["temp"] - 273.15  # Convert from Kelvin to Celsius
                pressure = main_data["pressure"]
                humidity = main_data["humidity"]
                weather_data = data["weather"][0]
                weather_description = weather_data["description"]
                
                weather_report = (
                    f"The weather in {location} is currently {weather_description}. "
                    f"The temperature is {temperature:.1f} degrees Celsius with "
                    f"{humidity}% humidity and atmospheric pressure of {pressure} hectopascals."
                )
                
                self.speak(weather_report)
            else:
                self.speak(f"I couldn't find weather information for {location}.")
        except Exception as e:
            self.speak(f"Sorry, I couldn't retrieve the weather information. Error: {str(e)}")
    
    def get_news(self, command):
        """Get the latest news headlines."""
        if not NEWS_API_KEY:
            self.speak("News functionality is not configured. Please set up an API key in the config file.")
            return
        
        try:
            news_source = "bbc-news"  # Default news source
            if 'tech' in command or 'technology' in command:
                news_source = "techcrunch"
            elif 'business' in command:
                news_source = "business-insider"
            elif 'sports' in command:
                news_source = "espn"
            
            news_url = f"https://newsapi.org/v2/top-headlines?sources={news_source}&apiKey={NEWS_API_KEY}"
            response = requests.get(news_url)
            news_data = response.json()
            
            if news_data["status"] == "ok" and news_data["totalResults"] > 0:
                articles = news_data["articles"][:5]  # Get top 5 headlines
                self.speak(f"Here are the latest news headlines from {news_source.replace('-', ' ')}:")
                for i, article in enumerate(articles, 1):
                    self.speak(f"{i}. {article['title']}")
            else:
                self.speak("Sorry, I couldn't retrieve the news at the moment.")
        except Exception as e:
            self.speak(f"Sorry, I encountered an error while fetching news: {str(e)}")
    
    def get_time(self):
        """Get the current time."""
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        self.speak(f"The current time is {current_time}")
    
    def get_date(self):
        """Get the current date."""
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        self.speak(f"Today is {current_date}")
    
    def tell_joke(self):
        """Tell a random joke."""
        joke = pyjokes.get_joke()
        self.speak(joke)
    
    def take_note(self, command):
        """Take a note and save it to a file."""
        note_start = command.find('note') + 4 if 'note' in command else command.find('remember') + 8
        note_text = command[note_start:].strip()
        
        if not note_text:
            self.speak("What would you like me to remember?")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        note_filename = f"data/notes/note_{timestamp}.txt"
        
        with open(note_filename, 'w') as note_file:
            note_file.write(note_text)
        
        self.speak("I've made a note of that.")
    
    def set_reminder(self, command):
        """Set a reminder for a specific time."""
        # Extract time and reminder text from command
        self.speak("Please tell me the time and what you want to be reminded about.")
        reminder_details = self.listen()
        
        if reminder_details:
            try:
                # Simple parsing - in a real app you'd use more sophisticated NLP
                time_match = re.search(r'(\d{1,2}):?(\d{2})?\s?(am|pm)?', reminder_details, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3).lower() if time_match.group(3) else 'am'
                    
                    if period == 'pm' and hour < 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                    
                    # Get current time
                    now = datetime.datetime.now()
                    reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If the time has already passed today, set for tomorrow
                    if reminder_time < now:
                        reminder_time += datetime.timedelta(days=1)
                    
                    # Extract reminder text
                    reminder_text = re.sub(r'(\d{1,2}):?(\d{2})?\s?(am|pm)?', '', reminder_details, flags=re.IGNORECASE).strip()
                    
                    # Save reminder
                    timestamp = reminder_time.strftime("%Y-%m-%d_%H-%M-%S")
                    reminder_filename = f"data/reminders/reminder_{timestamp}.txt"
                    
                    with open(reminder_filename, 'w') as reminder_file:
                        reminder_file.write(reminder_text)
                    
                    self.speak(f"I'll remind you to {reminder_text} at {reminder_time.strftime('%I:%M %p')}")
                else:
                    self.speak("I couldn't understand the time. Please try again.")
            except Exception as e:
                self.speak(f"Sorry, I couldn't set the reminder. Error: {str(e)}")
        else:
            self.speak("I didn't hear the reminder details. Please try again.")
    
    def set_alarm(self, command):
        """Set an alarm for a specific time."""
        self.speak("Please tell me the time for the alarm.")
        alarm_time = self.listen()
        
        if alarm_time:
            try:
                # Simple parsing - in a real app you'd use more sophisticated NLP
                time_match = re.search(r'(\d{1,2}):?(\d{2})?\s?(am|pm)?', alarm_time, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3).lower() if time_match.group(3) else 'am'
                    
                    if period == 'pm' and hour < 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                    
                    # Get current time
                    now = datetime.datetime.now()
                    alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If the time has already passed today, set for tomorrow
                    if alarm_time < now:
                        alarm_time += datetime.timedelta(days=1)
                    
                    # Calculate time difference
                    time_diff = (alarm_time - now).total_seconds()
                    
                    # Save alarm
                    timestamp = alarm_time.strftime("%Y-%m-%d_%H-%M-%S")
                    alarm_filename = f"data/alarms/alarm_{timestamp}.txt"
                    
                    with open(alarm_filename, 'w') as alarm_file:
                        alarm_file.write("Alarm set by user")
                    
                    # Start alarm thread
                    Thread(target=self._alarm_thread, args=(time_diff,)).start()
                    
                    self.speak(f"Alarm set for {alarm_time.strftime('%I:%M %p')}")
                else:
                    self.speak("I couldn't understand the time. Please try again.")
            except Exception as e:
                self.speak(f"Sorry, I couldn't set the alarm. Error: {str(e)}")
        else:
            self.speak("I didn't hear the alarm time. Please try again.")
    
    def _alarm_thread(self, delay):
        """Thread function for alarm countdown."""
        time.sleep(delay)
        self.speak("Alarm! Alarm! Wake up!")
        # Play alarm sound
        try:
            mixer.music.load('data/alarms/alarm_sound.mp3')  # You need to provide this file
            mixer.music.play()
        except:
            pass
    
    def adjust_volume(self, command):
        """Adjust the system volume."""
        if 'increase' in command or 'up' in command:
            self.volume = min(1.0, self.volume + 0.1)
            if hasattr(self, 'engine'):
                self.engine.setProperty('volume', self.volume)
            self.speak(f"Volume increased to {int(self.volume * 100)} percent")
        elif 'decrease' in command or 'down' in command:
            self.volume = max(0.0, self.volume - 0.1)
            if hasattr(self, 'engine'):
                self.engine.setProperty('volume', self.volume)
            self.speak(f"Volume decreased to {int(self.volume * 100)} percent")
        elif 'mute' in command or 'silent' in command:
            self.volume = 0.0
            if hasattr(self, 'engine'):
                self.engine.setProperty('volume', self.volume)
            self.speak("Volume muted")
        elif 'unmute' in command or 'sound on' in command:
            self.volume = 0.7
            if hasattr(self, 'engine'):
                self.engine.setProperty('volume', self.volume)
            self.speak("Volume unmuted")
        else:
            self.speak(f"Current volume is set to {int(self.volume * 100)} percent")
    
    def adjust_brightness(self, command):
        """Adjust the screen brightness."""
        try:
            if IS_WINDOWS:
                if 'increase' in command or 'up' in command:
                    # Windows brightness control requires additional libraries
                    self.speak("Increasing screen brightness")
                elif 'decrease' in command or 'down' in command:
                    self.speak("Decreasing screen brightness")
                else:
                    self.speak("Current brightness level cannot be determined")
            elif IS_MAC:
                if 'increase' in command or 'up' in command:
                    os.system("brightness 0.8")  # Set to 80%
                    self.speak("Increased screen brightness")
                elif 'decrease' in command or 'down' in command:
                    os.system("brightness 0.4")  # Set to 40%
                    self.speak("Decreased screen brightness")
                else:
                    self.speak("Current brightness level cannot be determined")
        except:
            self.speak("Sorry, I can't adjust brightness on this system.")
    
    def take_screenshot(self):
        """Take a screenshot of the current screen."""
        try:
            screenshots_dir = "data/screenshots"
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
                
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            screenshot_filename = f"{screenshots_dir}/screenshot_{timestamp}.png"
            pyautogui.screenshot(screenshot_filename)
            self.speak("Screenshot taken and saved")
        except Exception as e:
            self.speak(f"Sorry, I couldn't take a screenshot. Error: {str(e)}")
    
    def play_music(self):
        """Play music from a default directory."""
        music_dir = "data/music"
        if not os.path.exists(music_dir):
            os.makedirs(music_dir)
        
        music_files = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav', '.m4a'))]
        
        if not music_files:
            self.speak("No music files found in the music directory.")
            return
        
        # Play a random song
        song = random.choice(music_files)
        try:
            mixer.music.load(os.path.join(music_dir, song))
            mixer.music.play()
            self.speak(f"Playing {os.path.splitext(song)[0]}")
        except Exception as e:
            self.speak(f"Sorry, I couldn't play the music. Error: {str(e)}")
    
    def pause_music(self):
        """Pause the currently playing music."""
        if mixer.music.get_busy():
            mixer.music.pause()
            self.speak("Music paused")
        else:
            self.speak("No music is currently playing")
    
    def next_song(self):
        """Play the next song in the music directory."""
        self.pause_music()
        self.play_music()
    
    def shutdown_system(self):
        """Shutdown the computer."""
        self.speak("Shutting down the system in 10 seconds. Say 'cancel' to abort.")
        
        # Give user time to cancel
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.listen() and 'cancel' in self.listen():
                self.speak("Shutdown cancelled.")
                return
            time.sleep(1)
        
        try:
            if IS_WINDOWS:
                os.system('shutdown /s /t 1')
            elif IS_MAC:
                os.system('osascript -e \'tell app "System Events" to shut down\'')
        except:
            self.speak("Sorry, I couldn't shutdown the system.")
    
    def restart_system(self):
        """Restart the computer."""
        self.speak("Restarting the system in 10 seconds. Say 'cancel' to abort.")
        
        # Give user time to cancel
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.listen() and 'cancel' in self.listen():
                self.speak("Restart cancelled.")
                return
            time.sleep(1)
        
        try:
            if IS_WINDOWS:
                os.system('shutdown /r /t 1')
            elif IS_MAC:
                os.system('osascript -e \'tell app "System Events" to restart\'')
        except:
            self.speak("Sorry, I couldn't restart the system.")
    
    def sleep_system(self):
        """Put the system to sleep."""
        self.speak("Putting the system to sleep.")
        try:
            if IS_WINDOWS:
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            elif IS_MAC:
                os.system('pmset sleepnow')
        except:
            self.speak("Sorry, I couldn't put the system to sleep.")
    
    def lock_system(self):
        """Lock the computer."""
        self.speak("Locking the system.")
        try:
            if IS_WINDOWS:
                os.system('rundll32.exe user32.dll,LockWorkStation')
            elif IS_MAC:
                os.system('/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend')
        except:
            self.speak("Sorry, I couldn't lock the system.")
    
    def change_language(self, command):
        """Change the assistant's language."""
        if 'hindi' in command:
            self.preferred_language = 'hindi'
            self.speak("भाषा हिंदी में बदल गई है", language='hi')
        else:
            self.preferred_language = 'english'
            self.speak("Language changed to English")
    
    def list_capabilities(self):
        """List what the assistant can do."""
        capabilities = [
            "I can open applications like Notepad, Calculator, Chrome, etc.",
            "I can search the web or Wikipedia for information.",
            "I can tell you the current time and date.",
            "I can give you weather forecasts.",
            "I can read news headlines.",
            "I can tell jokes to lighten your mood.",
            "I can take notes for you to remember things.",
            "I can set reminders and alarms.",
            "I can adjust system volume and brightness.",
            "I can take screenshots.",
            "I can play music from your collection.",
            "I can control your system - shutdown, restart, sleep or lock.",
            "I can switch between English and Hindi languages.",
            "I can perform math calculations."
        ]
        
        self.speak("Here's what I can do:")
        for capability in capabilities:
            self.speak(capability)
    
    def run(self):
        """Main loop for the voice assistant."""
        self.speak("Nova voice assistant initialized. Waiting for wake word.")
        
        while True:
            try:
                # Listen for wake word
                with self.microphone as source:
                    print("Waiting for wake word...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, phrase_time_limit=3)
                
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"Heard: {text}")
                    
                    # Check for wake word
                    if any(wake_word in text for wake_word in WAKE_WORDS):
                        self.listening = True
                        self.greet()
                        
                        # Main command loop
                        while self.listening:
                            command = self.listen()
                            if not command:
                                # If no command heard for timeout period, go back to sleep
                                if time.time() - self.last_command_time > self.command_timeout:
                                    self.speak("I'm going back to sleep. Say 'Hey Nova' to wake me up.")
                                    self.listening = False
                                continue
                            
                            # Check if user wants to stop listening
                            if any(phrase in command for phrase in ['stop listening', 'go to sleep', 'that\'s all']):
                                self.speak("I'll stop listening now. Say 'Hey Nova' to wake me up.")
                                self.listening = False
                                break
                            
                            # Process the command
                            self.process_command(command)
                
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
                    time.sleep(1)
            
            except KeyboardInterrupt:
                self.speak("Goodbye!")
                sys.exit(0)
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    # Create default config file if it doesn't exist
    if not os.path.exists('nova_config.ini'):
        with open('config.ini', 'w') as f:
            f.write("""[user]
name = Rishabh
language = hindi

[api_keys]
openweathermap = 07c8d3211d6b0865c09bb0c3e191a0d0
newsapi = dee28dbc351742f58095e3ad62ac25ce
""")
    
    assistant = NovaVoiceAssistant()
    assistant.run()