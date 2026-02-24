import os
import base64
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime, date
from functools import wraps
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'

# Download required NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)
try:
    nltk.data.find('punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Crisis / self-harm detection keywords (non-exhaustive)
CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "end it all",
    "hurt myself",
    "self harm",
    "self-harm",
    "cut myself",
    "cutting",
    "overdose",
    "don't want to live",
    "dont want to live",
    "wish i were dead",
    "wish i was dead",
    "can't go on",
    "cant go on"
]

# High-level crisis resources to surface to the user
HELPLINE_RESOURCES = [
    {
        "region": "If you are in immediate danger",
        "details": "Please contact your local emergency number right away (for example 911 in the US/Canada, 999 or 112 in the UK/EU)."
    },
    {
        "region": "United States & Canada",
        "details": "Call or text 988, or use chat via 988lifeline.org for the Suicide & Crisis Lifeline (24/7, free and confidential)."
    },
    {
        "region": "United Kingdom & Ireland",
        "details": "Call Samaritans at 116 123 or visit samaritans.org (24/7)."
    },
    {
        "region": "Australia",
        "details": "Call Lifeline at 13 11 14 or visit lifeline.org.au (24/7)."
    },
    {
        "region": "Other countries",
        "details": "Visit findahelpline.com or search online for your local suicide or crisis hotline."
    }
]

# Encryption utilities
def get_encryption_key(session_id, secret_key):
    """Generate encryption key from session ID and secret key"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'empathetic_chatbot_salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(f"{session_id}{secret_key}".encode()))
    return key

def encrypt_message(message, session_id, secret_key):
    """Encrypt a message using session-based key"""
    try:
        key = get_encryption_key(session_id, secret_key)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(message.encode())
        # Fernet already returns URL-safe base64 encoded bytes, just decode to string
        return encrypted.decode()
    except Exception as e:
        # Fallback to plain text if encryption fails
        print(f"Encryption error: {e}")
        return message

def decrypt_message(encrypted_message, session_id, secret_key):
    """Decrypt a message using session-based key"""
    try:
        key = get_encryption_key(session_id, secret_key)
        fernet = Fernet(key)
        # Fernet expects URL-safe base64 encoded bytes
        decrypted = fernet.decrypt(encrypted_message.encode())
        return decrypted.decode()
    except Exception as e:
        # Return as-is if decryption fails (might be plain text)
        print(f"Decryption error: {e}")
        return encrypted_message

class EmpatheticChatbot:
    def __init__(self):
        self.name = "Aria"
        self.conversation_context = []

    def detect_crisis(self, text):
        """Detect potential self-harm or suicidal ideation."""
        text_lower = text.lower()
        matched_keywords = [kw for kw in CRISIS_KEYWORDS if kw in text_lower]
        return len(matched_keywords) > 0, matched_keywords
        
    def detect_emotion(self, text):
        """Detect emotional state from text"""
        # Use VADER sentiment analyzer
        scores = sia.polarity_scores(text)
        
        # Detect emotional keywords
        emotional_keywords = {
            'angry': ['angry', 'mad', 'furious', 'rage', 'hate', 'annoyed', 'frustrated'],
            'sad': ['sad', 'depressed', 'unhappy', 'upset', 'crying', 'hurt', 'lonely'],
            'anxious': ['anxious', 'worried', 'nervous', 'stressed', 'panic', 'afraid', 'scared'],
            'happy': ['happy', 'glad', 'excited', 'joyful', 'great', 'wonderful', 'amazing'],
            'confused': ['confused', 'uncertain', 'unsure', 'lost', 'dont understand'],
            'grateful': ['thank', 'thanks', 'grateful', 'appreciate', 'blessed']
        }
        
        text_lower = text.lower()
        detected_emotions = []
        intensity = scores['compound']
        
        for emotion, keywords in emotional_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_emotions.append(emotion)
        
        # Determine primary emotion based on sentiment
        if intensity <= -0.5:
            if 'angry' in detected_emotions:
                primary_emotion = 'angry'
            elif 'sad' in detected_emotions:
                primary_emotion = 'sad'
            else:
                primary_emotion = 'distressed'
        elif intensity <= -0.1:
            primary_emotion = 'anxious' if 'anxious' in detected_emotions else 'concerned'
        elif intensity >= 0.5:
            primary_emotion = 'happy' if 'happy' in detected_emotions else 'positive'
        elif intensity >= 0.1:
            primary_emotion = 'calm' if 'grateful' in detected_emotions else 'neutral'
        else:
            primary_emotion = 'neutral'
            
        return primary_emotion, intensity, detected_emotions
    
    def de_escalate_response(self, emotion, intensity, text):
        """Generate empathetic, de-escalating responses"""
        responses = {
            'angry': [
                "I can hear that you're feeling really upset right now. That sounds incredibly difficult. Would you like to take a moment to breathe, or would it help to talk about what's bothering you?",
                "It sounds like something is really bothering you, and I understand that frustration. Sometimes expressing these feelings can help. I'm here to listen without judgment.",
                "I sense a lot of strong emotion in what you're sharing. These feelings are valid. Would it help to step back for a moment, or would talking through it feel better right now?"
            ],
            'sad': [
                "I'm sorry you're going through this. It sounds really hard, and it's okay to feel this way. I'm here to listen. What's on your mind?",
                "That sounds really painful. I want you to know that you're not alone in this. Would it help to share a bit more about what's weighing on you?",
                "I can sense that you're hurting right now. These feelings can be overwhelming. Remember, it's okay to feel sad, and I'm here with you through this."
            ],
            'anxious': [
                "I understand that worry and anxiety can feel overwhelming. You're not alone in feeling this way. Let's take things one step at a time. What would help you feel a little more at ease right now?",
                "It sounds like you're feeling a lot of worry or stress. That's completely understandable. Sometimes it helps to name what we're feeling. Can you tell me a bit more about what's causing this anxiety?",
                "I hear the concern in your words. Anxiety can make everything feel bigger than it is. Would it help to focus on one thing at a time, or would talking about what's worrying you be more helpful?"
            ],
            'distressed': [
                "I can tell you're going through something really difficult right now. I'm here to listen, and there's no pressure. How are you feeling in this moment?",
                "It sounds like things are really tough for you. Your feelings are important and valid. Would you like to share what's happening, or would you prefer to take a moment first?",
                "I sense that you're dealing with something significant. Remember, it's okay to not be okay. I'm here to support you. What would be most helpful right now?"
            ],
            'confused': [
                "It sounds like you're feeling a bit uncertain or confused about something. That's completely okay - confusion is a normal part of figuring things out. Can you help me understand what's unclear?",
                "I hear that you're feeling unsure about this. Sometimes talking through things can help bring clarity. Would it help if we explored this together?",
                "Confusion can be frustrating, but it's also a sign that you're thinking deeply about something. Let's work through this together. What would you like to understand better?"
            ],
            'neutral': [
                "I'm here and ready to listen. How are you feeling today?",
                "Thank you for reaching out. What's on your mind?",
                "I'm here to support you. What would you like to talk about?"
            ],
            'positive': [
                "It's wonderful to hear that you're doing well! I'm glad things are going positively for you. Is there anything specific you'd like to share or discuss?",
                "That sounds really nice! It's great to feel good. Is there anything else on your mind today?",
                "I'm happy to hear that you're in a good place. How can I support you today?"
            ]
        }
        
        # Select response based on emotion and intensity
        if emotion in responses:
            if intensity <= -0.7:  # Very intense negative emotion
                response = responses[emotion][0] if len(responses[emotion]) > 0 else responses['distressed'][0]
            elif intensity <= -0.3:
                response = responses[emotion][1] if len(responses[emotion]) > 1 else responses[emotion][0]
            else:
                response = responses[emotion][-1] if len(responses[emotion]) > 0 else responses['neutral'][0]
        else:
            response = responses['neutral'][0]
        
        return response
    
    def generate_response(self, user_input, session_id=None, secret_key=None):
        """Generate empathetic response based on user input"""
        # Detect emotion
        emotion, intensity, detected_emotions = self.detect_emotion(user_input)

        # Detect potential crisis / self-harm content
        is_crisis, matched_keywords = self.detect_crisis(user_input)
        
        # Generate de-escalating response
        response = self.de_escalate_response(emotion, intensity, user_input)

        # If crisis detected, gently add crisis-specific guidance
        crisis_message = None
        if is_crisis:
            crisis_message = (
                "I’m really glad you shared this with me. Your safety matters a lot.\n\n"
                "I’m an AI and not a replacement for professional help, and I can’t respond in emergencies. "
                "If you are thinking about hurting yourself or feel in immediate danger, please contact a crisis "
                "hotline or your local emergency number right away. I can share some resources that may help."
            )
            # Append a brief note to the main response so it stays empathetic but safety-focused
            response = (
                response
                + "\n\nI’m also sensing that you might be going through something very serious. "
                  "If there’s any chance you might hurt yourself, please consider reaching out to a trusted person "
                  "or a crisis service right now."
            )
        
        # Get current timestamp
        now = datetime.now()
        timestamp = now.isoformat()
        formatted_timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # Encrypt messages for storage
        encrypted_user = user_input
        encrypted_response = response
        if session_id and secret_key:
            encrypted_user = encrypt_message(user_input, session_id, secret_key)
            encrypted_response = encrypt_message(response, session_id, secret_key)
        
        # Track conversation context (encrypted)
        self.conversation_context.append({
            'user': encrypted_user,
            'emotion': emotion,
            'intensity': intensity,
            'response': encrypted_response,
            'timestamp': timestamp,
            'formatted_timestamp': formatted_timestamp,
            'is_crisis': is_crisis
        })
        
        # Keep only last 10 exchanges for context
        if len(self.conversation_context) > 10:
            self.conversation_context = self.conversation_context[-10:]
        
        return {
            'response': response,  # Return unencrypted for display
            'emotion_detected': emotion,
            'intensity': round(intensity, 2),
            'bot_name': self.name,
            'timestamp': timestamp,
            'formatted_timestamp': formatted_timestamp,
            'is_crisis': is_crisis,
            'crisis_message': crisis_message,
            'crisis_resources': HELPLINE_RESOURCES if is_crisis else []
        }
    
    def reset_conversation(self):
        """Reset conversation context"""
        self.conversation_context = []

# Initialize chatbot
chatbot = EmpatheticChatbot()

# Minimum age requirement (18 years)
MINIMUM_AGE = 18

def calculate_age(birth_date):
    """Calculate age from birth date"""
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Redirect to age check if not verified, login if not logged in, or chat if authenticated"""
    if not session.get('age_verified'):
        return redirect(url_for('age_check'))
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/help')
def help_page():
    """Static help page with crisis resources"""
    return render_template('help.html')

@app.route('/age-check', methods=['GET', 'POST'])
def age_check():
    """Age verification page with identification requirement"""
    if session.get('age_verified'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        birth_date_str = request.form.get('birth_date')
        id_type = request.form.get('id_type')
        id_number = request.form.get('id_number', '').strip()
        
        # Validate inputs
        if not birth_date_str:
            return render_template('age_check.html', error='Please enter your date of birth')
        
        if not id_type:
            return render_template('age_check.html', error='Please select an identification type')
        
        if not id_number:
            return render_template('age_check.html', error='Please enter your identification number')
        
        try:
            # Parse birth date
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            
            # Calculate age
            age = calculate_age(birth_date)
            
            # Check if user is old enough
            if age < MINIMUM_AGE:
                return render_template('age_check.html', 
                                     error=f'You must be at least {MINIMUM_AGE} years old to use this service. You are currently {age} years old.')
            
            # Store age verification in session
            session['age_verified'] = True
            session['birth_date'] = birth_date_str
            session['age'] = age
            session['id_type'] = id_type
            
            # Redirect to login
            return redirect(url_for('login'))
            
        except ValueError:
            return render_template('age_check.html', error='Invalid date format. Please use YYYY-MM-DD format.')
        except Exception as e:
            return render_template('age_check.html', error=f'An error occurred: {str(e)}')
    
    return render_template('age_check.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - requires age verification first"""
    if not session.get('age_verified'):
        return redirect(url_for('age_check'))
    
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username:
            return render_template('login.html', error='Please enter a username')
        
        if not password:
            return render_template('login.html', error='Please enter a password')
        
        # Simple authentication (in production, use proper password hashing and database)
        # For demo purposes, accept any username/password combination
        # In production, you would verify against a database
        
        session['logged_in'] = True
        session['username'] = username
        
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('age_check'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please log in to continue'}), 401
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request: JSON data required'}), 400
        
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Please enter a message'}), 400
        
        # Get session ID for encryption
        session_id = session.get('username', 'default')
        secret_key = app.config['SECRET_KEY']
        
        response_data = chatbot.generate_response(user_message, session_id, secret_key)
        # Do not expose emotion detection signals to end users (kept internally in context)
        response_data.pop('emotion_detected', None)
        response_data.pop('intensity', None)
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': f'Something went wrong: {str(e)}'}), 500

@app.route('/theme', methods=['GET', 'POST'])
@login_required
def theme():
    """Get or set user theme preference"""
    if request.method == 'POST':
        try:
            data = request.json or {}
            theme_name = data.get('theme', 'default')
            session['theme'] = theme_name
            return jsonify({'success': True, 'theme': theme_name})
        except Exception as e:
            return jsonify({'error': f'Invalid request: {str(e)}'}), 400
    else:
        return jsonify({'theme': session.get('theme', 'default')})

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please log in to continue'}), 401
    
    chatbot.reset_conversation()
    return jsonify({'message': 'Conversation reset'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)

