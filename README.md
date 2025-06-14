# Nova Voice Assistant 🤖


A **cross-platform intelligent voice assistant** that works on both Windows and macOS, with natural language processing, system control, and smart features.

## Features ✨

- **🌐 Cross-Platform**: Works seamlessly on Windows & macOS
- **🎙️ Voice Commands**: Responds to natural language
- **🧠 Smart Features**:
  - Math problem solver (`Calculate 45 plus 67`)
  - Wikipedia/Web search
  - Weather forecasts
  - News headlines
- **💻 System Control**:
  - Open/close applications
  - Shutdown/Restart/Lock
  - Volume/Brightness control
- **🎵 Media**:
  - Play/Pause music
  - Take screenshots
- **🌍 Multilingual**:
  - English (US female voice)
  - Hindi (Indian accent)

## Installation ⚙️

### Prerequisites
- Python 3.8+
- Microphone
- Internet connection

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/Nova-voice-assistant.git
   cd nova-voice-assistant

2. **Install dependencies:**

    bash
    pip install -r requirements.txt

3. **Platform-specific setup**:

-   Windows:
        bash
        pip install pyaudio pywin32
-   macOS:
        bash
        brew install portaudio
        pip install pyaudio

4. **Configure API keys:**

-   config.ini

**Usage 🚀**
    Run Nova:
        bash
        python nova.py

    Wake Phrases:
        "Hey Nova"
        "Nova"

    Example Commands:
        "Open Chrome"
        "What's the weather in London?"
        "Calculate 15 percent of 200"
        "Tell me a joke"
        "Change language to Hindi"

**System Requirements 📋**
Component	    Windows	        macOS
OS Version	     10/11	     Monterey (12+)
RAM	             4GB+	        4GB+
Storage	      500MB free	 500MB free
Python	         3.8+	        3.8+


**Troubleshooting 🔧**
Problem: Microphone not working
Solution:

Windows: Check mic privacy settings
macOS: System Preferences > Security & Privacy > Microphone

Problem: PyAudio installation fails
Solution:

bash
# Windows
python -m pip install --upgrade pip setuptools wheel
pip install pipwin
pipwin install pyaudio

# macOS
brew install portaudio
pip install pyaudio


**Contributing 🤝**

Fork the project
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit changes (git commit -m 'Add amazing feature')
Push to branch (git push origin feature/AmazingFeature)
Open a Pull Request

Made with ❤️ by Rishabh Mishra
"Hello, I'm Nova. How can I assist you today?" 🤖
