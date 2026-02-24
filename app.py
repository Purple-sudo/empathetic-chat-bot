import os
import base64
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
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
        """Detect emotional state from text using multiple signals."""
        # Overall sentiment (VADER)
        scores = sia.polarity_scores(text)
        vader_compound = scores["compound"]

        # Finer-grained sentiment (TextBlob)
        blob = TextBlob(text)
        tb_polarity = float(blob.sentiment.polarity)
        tb_subjectivity = float(blob.sentiment.subjectivity)

        # Richer emotional keyword sets (not exhaustive, but broad)
        emotional_keywords = {
            "anger": [
                "angry", "mad", "furious", "rage", "hate", "annoyed", "irritated",
                "frustrated", "resentful", "outraged"
            ],
            "sadness": [
                "sad", "depressed", "unhappy", "upset", "crying", "hurt", "heartbroken",
                "grief", "grieving", "down", "blue"
            ],
            "anxiety": [
                "anxious", "worried", "nervous", "stressed", "panic", "afraid",
                "scared", "overthinking", "on edge"
            ],
            "fear": [
                "terrified", "petrified", "horrified", "frightened", "phobia",
                "dread", "panic attack"
            ],
            "shame": [
                "ashamed", "embarrassed", "humiliated", "worthless", "disgusted with myself"
            ],
            "guilt": [
                "guilty", "regret", "regretting", "blame myself", "my fault"
            ],
            "loneliness": [
                "lonely", "alone", "isolated", "left out", "abandoned"
            ],
            "hopelessness": [
                "hopeless", "no way out", "what's the point", "whats the point",
                "nothing will change", "giving up", "give up"
            ],
            "overwhelm": [
                "overwhelmed", "too much", "can't handle", "cant handle",
                "burnt out", "burned out", "exhausted"
            ],
            "joy": [
                "happy", "glad", "excited", "joyful", "great", "wonderful", "amazing",
                "delighted", "thrilled", "ecstatic"
            ],
            "love": [
                "love", "loving", "caring", "affection", "grateful", "appreciate",
                "thankful", "blessed"
            ],
            "confusion": [
                "confused", "uncertain", "unsure", "lost", "don't understand",
                "dont understand", "mixed feelings"
            ],
            "relief": [
                "relieved", "finally over", "better now", "not so bad anymore"
            ],
            "pride": [
                "proud", "accomplished", "achieved", "succeeded"
            ],
            "neutral": []
        }

        text_lower = text.lower()
        detected_emotions = set()

        for emotion, keywords in emotional_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_emotions.add(emotion)

        # Heuristic to choose a primary emotion based on sentiment + keywords
        primary_emotion = "neutral"

        # Strong negative: look for specific negative emotions
        if vader_compound <= -0.4 or tb_polarity <= -0.3:
            for candidate in ["hopelessness", "sadness", "anger", "fear", "shame", "guilt", "anxiety", "overwhelm"]:
                if candidate in detected_emotions:
                    primary_emotion = candidate
                    break
            if primary_emotion == "neutral":
                primary_emotion = "sadness"
        # Mild negative / worried
        elif vader_compound < 0 or tb_polarity < 0:
            if "anxiety" in detected_emotions:
                primary_emotion = "anxiety"
            elif "overwhelm" in detected_emotions:
                primary_emotion = "overwhelm"
            elif "loneliness" in detected_emotions:
                primary_emotion = "loneliness"
            else:
                primary_emotion = "concerned"
        # Strong positive
        elif vader_compound >= 0.5 or tb_polarity >= 0.5:
            for candidate in ["joy", "love", "relief", "pride"]:
                if candidate in detected_emotions:
                    primary_emotion = candidate
                    break
            if primary_emotion == "neutral":
                primary_emotion = "joy"
        # Mild positive or mixed
        elif vader_compound > 0 or tb_polarity > 0:
            if "love" in detected_emotions:
                primary_emotion = "love"
            elif "relief" in detected_emotions:
                primary_emotion = "relief"
            else:
                primary_emotion = "calm"
        else:
            # Neutral sentiment – fall back to explicit emotions or neutral
            if detected_emotions:
                # Pick one consistently for storage
                primary_emotion = sorted(detected_emotions)[0]
            else:
                primary_emotion = "neutral"

        # Use VADER compound as intensity indicator
        intensity = vader_compound

        return primary_emotion, intensity, sorted(list(detected_emotions))
    
    def de_escalate_response(self, emotion, intensity, text):
        """Generate empathetic, de-escalating responses"""
        responses = {
            "anger": [
                "It sounds like you're carrying a lot of anger and frustration right now. That makes a lot of sense given what you're going through. If you’d like, we can unpack what’s behind that anger together.",
                "I hear how strongly this is affecting you, and it’s completely valid to feel angry. Would it help to talk through what happened, or to explore what you might need right now?",
                "Those feelings of anger are important – they often point to something that really matters to you. I'm here with you as you make sense of it, one step at a time."
            ],
            "sadness": [
                "I'm really sorry that you're going through something so heavy. It’s completely okay to feel sad about this. If you’d like, you can share a bit more about what’s weighing on your heart.",
                "I can feel how much this is hurting you. You don’t have to go through it alone – I’m here to listen and sit with you in this feeling.",
                "Sometimes sadness can feel like it’s taking up all the space inside. It’s okay to let it be here for a moment. What feels hardest about this right now?"
            ],
            "anxiety": [
                "Feeling anxious in a situation like this is very understandable. Let’s slow things down together and take it one small step at a time. What’s the worry that feels biggest right now?",
                "I hear a lot of worry in what you’re sharing. Anxiety can make everything feel more urgent and overwhelming. If you’d like, we can name some of those fears and explore them gently.",
                "It makes sense that you’re feeling on edge. Sometimes it helps to bring things back to the present moment. What’s one small thing you could do right now that might make you feel just a little safer or calmer?"
            ],
            "fear": [
                "It sounds like there’s a lot of fear in what you’re going through. That’s a very human response. Would it feel okay to talk about what scares you the most here?",
                "Being afraid in a situation like this doesn’t mean you’re weak – it means you’re human. I’m here with you while we gently look at what feels so frightening.",
                "Fear can make everything feel uncertain and shaky. You don’t have to have all the answers right now. We can explore this at your pace."
            ],
            "shame": [
                "I’m really glad you felt able to share this – shame can make us want to hide, but you don’t have to hide here. What you’re feeling is valid.",
                "It sounds like you’re being very hard on yourself. If it’s okay, we could gently look at where that harsh inner voice is coming from.",
                "Feeling ashamed can be incredibly painful. You’re still worthy of care and understanding, even with the things you’re struggling with."
            ],
            "guilt": [
                "It sounds like you’re carrying a lot of guilt. That’s a heavy feeling to hold on your own. Would it help to talk through what happened and how you see it?",
                "Guilt often shows up when something really matters to us. We can explore together what feels like your responsibility and what might not be entirely on you.",
                "You deserve compassion too, even while you’re feeling guilty. If you’d like, we can gently separate the facts from the harsh way you might be judging yourself."
            ],
            "loneliness": [
                "Feeling lonely can be incredibly hard, especially when it seems like no one truly sees what you’re going through. I’m here with you right now.",
                "You’re not strange or wrong for feeling alone – many people go through this, even if they don’t talk about it. Would it help to share a bit about when you feel loneliness the most?",
                "Loneliness can make the world feel distant. We can take a moment here just to acknowledge how isolating this feels, without rushing to fix it."
            ],
            "hopelessness": [
                "It sounds like things have felt heavy for a long time, and it’s hard to see a way forward. I’m really glad you’re talking about it with me.",
                "Feeling hopeless can be deeply exhausting. You don’t have to see the whole path right now – we can start with just one small step, if that feels okay.",
                "Even if you can’t feel it yet, the fact that you’re reaching out suggests that a part of you still wants support. That part of you matters a lot."
            ],
            "overwhelm": [
                "It really does sound like there’s a lot on your plate. Anyone in your position might feel overwhelmed too.",
                "When everything feels like too much, it can help to gently break things into smaller pieces. Would you like to talk through what feels most urgent versus what might be able to wait?",
                "You don’t have to carry all of this alone in this moment. We can sort through it together, one piece at a time."
            ],
            "joy": [
                "It’s really lovely to hear something positive in what you’re sharing. Would you like to talk more about what’s bringing you joy right now?",
                "I’m glad you’re experiencing this good feeling. Savoring it for a moment can be really nourishing. What about this experience feels most meaningful to you?",
                "It’s great to hear that something is going well. If you’d like, we can explore how to hold onto or build on this feeling."
            ],
            "love": [
                "It sounds like there’s a lot of care and love in what you’re describing. That’s a powerful feeling.",
                "Love can be both beautiful and complicated. If you want, we can explore what this love is bringing up for you right now.",
                "It’s really meaningful that you feel this way. How does this love show up in your day-to-day life?"
            ],
            "confusion": [
                "It’s completely okay to feel unsure or conflicted here. Many situations in life aren’t simple.",
                "We don’t have to rush to an answer. If you’d like, we can gently untangle what you’re feeling and what options you might have.",
                "Confusion can be a sign that you’re thinking deeply and honestly about something. We can walk through it together step by step."
            ],
            "relief": [
                "It’s good to hear that there’s at least a bit of relief in what you’re feeling. You’ve likely been holding a lot for a while.",
                "Sometimes even a small sense of relief can give us a bit more room to breathe. What feels a little lighter for you right now?",
                "I’m glad you’re experiencing some ease. We can talk about how to support that feeling and protect your energy going forward."
            ],
            "pride": [
                "You’re allowed to feel proud of yourself here. It sounds like you’ve worked hard for this.",
                "Recognizing your own progress is important. What about this makes you feel most proud?",
                "It’s really nice to hear you acknowledge your own efforts. You deserve to take a moment and let that pride sink in."
            ],
            "calm": [
                "It’s good to hear that things feel at least a bit steady right now. We can still explore anything that’s on your mind.",
                "If you’re feeling relatively calm, this can be a helpful time to reflect gently on what you need going forward.",
                "I’m here with you in this calmer moment. Is there anything you’d like to unpack or prepare for while things feel steadier?"
            ],
            "concerned": [
                "It makes sense to feel concerned about this. Your feelings are telling you that something matters here.",
                "We can take a closer look at what’s worrying you without judging it. What feels most important to understand right now?",
                "Even if you’re not sure exactly what you’re feeling yet, that’s okay. We can explore your concerns together at your pace."
            ],
            "neutral": [
                "I’m here and ready to listen to whatever you’d like to share.",
                "Thank you for reaching out. What feels most present for you right now?",
                "I’m here to support you. You can start wherever feels easiest."
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

