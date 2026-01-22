# Empathetic Chatbot - Aria

A friendly, emotionally intelligent chatbot designed to understand human emotions and gently de-escalate intense feelings and situations. Aria provides empathetic support through natural conversation, responding with care and understanding to users' emotional states.

## ✨ Features

- **Emotion Detection**: Automatically detects emotional states (angry, sad, anxious, happy, confused, etc.) from user messages
- **Empathetic Responses**: Provides caring, understanding responses tailored to detected emotions
- **De-escalation**: Gently helps users manage intense emotions through calm, supportive dialogue
- **Friendly Tone**: Balanced friendliness - warm but not overly casual, professional yet approachable
- **Real-time Chat Interface**: Beautiful, responsive web interface for seamless interaction
- **Context Awareness**: Maintains conversation context to provide relevant, continuous support

## 🎯 Design Philosophy

Aria is designed with empathy at its core:
- **Not overly friendly**: Maintains a professional, calm demeanor
- **Understanding**: Recognizes and acknowledges emotional states
- **De-escalating**: Uses gentle language and techniques to help calm intense emotions
- **Supportive**: Provides a safe space for users to express themselves
- **Non-judgmental**: Responds with acceptance and understanding

## 🛠 Tech Stack

- **Backend**: Python 3.x with Flask
- **Natural Language Processing**: 
  - NLTK (Natural Language Toolkit)
  - TextBlob
  - VADER Sentiment Analyzer
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Emotion Detection**: Keyword analysis + sentiment scoring

## 📦 Installation

1. **Navigate to the project directory:**
   ```bash
   cd empathetic-chatbot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the chatbot:**
   Open http://127.0.0.1:5001 in your browser

## 💬 How It Works

### Emotion Detection

Aria uses a combination of:
- **Sentiment Analysis**: VADER (Valence Aware Dictionary and sEntiment Reasoner) to analyze emotional polarity
- **Keyword Detection**: Identifies emotional keywords in messages
- **Intensity Scoring**: Measures the strength of detected emotions

### Response Generation

Based on detected emotions, Aria:
1. Acknowledges the user's emotional state
2. Validates their feelings
3. Offers supportive, de-escalating responses
4. Suggests helpful next steps when appropriate

### De-escalation Techniques

- **Validation**: Acknowledging that feelings are valid
- **Calming Language**: Using gentle, reassuring words
- **Breathing Space**: Offering moments to pause when needed
- **Non-judgmental Listening**: Creating a safe space for expression
- **Gradual Guidance**: Slowly helping users move toward calmer states

## 🎨 Interface Features

- **Beautiful Design**: Modern, calming color scheme with smooth animations
- **Real-time Chat**: Instant message exchange with typing indicators
- **Emotion Badges**: Visual indicators showing detected emotions
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Conversation Reset**: Option to start fresh conversations

## 📝 Example Interactions

**User:** "I'm so frustrated with everything right now!"

**Aria:** "I can hear that you're feeling really upset right now. That sounds incredibly difficult. Would you like to take a moment to breathe, or would it help to talk about what's bothering you?"

**User:** "I'm worried about tomorrow's presentation"

**Aria:** "It sounds like you're feeling a lot of worry or stress. That's completely understandable. Sometimes it helps to name what we're feeling. Can you tell me a bit more about what's causing this anxiety?"

## 🔧 Customization

You can customize Aria by:

1. **Adjusting Responses**: Modify response templates in `app.py` under the `de_escalate_response` method
2. **Adding Emotions**: Extend the `emotional_keywords` dictionary to detect more emotional states
3. **Changing Tone**: Modify response language to match your desired level of friendliness
4. **UI Styling**: Update CSS in `templates/index.html` to change the visual appearance

## ⚠️ Important Notes

- This chatbot is designed for emotional support and de-escalation
- It is **not a replacement** for professional mental health services
- For serious mental health concerns, please contact a licensed professional
- The chatbot maintains conversation context for up to 10 recent exchanges

## 🚀 Future Enhancements

Potential improvements:
- Integration with professional mental health resources
- Multi-language support
- Voice interaction capabilities
- Advanced machine learning models for better emotion detection
- Conversation analytics and insights
- Export conversation history option

## 📄 License

This project is open source and available for educational and supportive purposes.

## 🤝 Contributing

Feel free to suggest improvements or contribute to making Aria more empathetic and helpful!

---

**Remember**: While Aria is here to provide support, if you're experiencing a mental health crisis, please reach out to a mental health professional or crisis hotline immediately.

