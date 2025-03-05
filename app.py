from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from io import BytesIO
import docker
from docker.errors import DockerException
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:kittu@db.ysgdpkhwfimomuptacnx.supabase.co:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize Docker client
try:
    docker_client = docker.from_env()
    docker_client.ping()
except DockerException as e:
    print(f"Warning: Docker is not available - {e}. Code execution will not work.")
    docker_client = None

# Register the user_profile blueprint
from user_profile import user_profile_bp
app.register_blueprint(user_profile_bp, url_prefix='/profile')

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(50))

# Create tables with error handling
try:
    with app.app_context():
        db.create_all()
except OperationalError as e:
    print(f"Database connection failed: {e}")
    raise

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('start'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('start'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('User already exists.')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/start', methods=['GET', 'POST'])
def start():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        language = request.form['language']
        if not title:
            flash('Title is required.')
            return redirect(url_for('start'))
        return redirect(url_for('editor', title=title, language=language))
    return render_template('start.html')

@app.route('/editor')
def editor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.args.get('title')
    language = request.args.get('language')
    if not title or not language:
        return redirect(url_for('start'))
    return render_template('editor.html', title=title, language=language)

@app.route('/new')
def new_file():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('start'))

@app.route('/save', methods=['POST'])
def save():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    title = request.form['title']
    language = request.form['language']
    if not title:
        flash('Title is required.')
        return redirect(url_for('start'))
    new_document = Document(title=title, content=content, user_id=session['user_id'], language=language)
    db.session.add(new_document)
    db.session.commit()
    flash('Document saved successfully!')
    return redirect(url_for('editor', title=title, language=language))

@app.route('/save_and_download', methods=['POST'])
def save_and_download():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content']
    title = request.form['title']
    language = request.form['language']
    
    if not title:
        flash('Title is required.')
        return redirect(url_for('start'))

    # Define language extensions
    language_map = {
        'python': '.py',
        'javascript': '.js',
        'cpp': '.cpp',
        'java': '.java',
        'c': '.c',
        'ruby': '.rb',
        'go': '.go',
        'php': '.php',
    }
    
    # Define MIME types
    mime_types = {
        'python': 'text/x-python',
        'javascript': 'application/javascript',
        'cpp': 'text/x-c++src',
        'java': 'text/x-java-source',
        'c': 'text/x-csrc',
        'ruby': 'text/x-ruby',
        'go': 'text/x-go',
        'php': 'application/x-httpd-php',
    }

    # Get the correct extension for the language
    expected_ext = language_map.get(language, '.txt')
    
    # Check if the title already has the correct extension
    if not title.lower().endswith(expected_ext):
        filename = f"{title}{expected_ext}"
    else:
        filename = title

    # Get the appropriate MIME type
    mime_type = mime_types.get(language, 'text/plain')

    # Save the document
    new_document = Document(
        title=title,
        content=content,
        user_id=session['user_id'],
        language=language
    )
    db.session.add(new_document)
    db.session.commit()

    # Create the response
    response = send_file(
        BytesIO(content.encode('utf-8')),
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename  # Use download_name instead of attachment_filename
    )

    # Add Content-Disposition header explicitly
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@app.route('/open', methods=['POST'])
def open_file():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file = request.files['file']
    filename = file.filename
    content = file.read().decode('utf-8', errors='ignore')
    file_extension = os.path.splitext(filename)[1].lower()
    
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.cpp': 'cpp',
        '.java': 'java',
        '.c': 'c',
        '.rb': 'ruby',
        '.go': 'go',
        '.php': 'php',
    }
    language = language_map.get(file_extension, 'text')

    if file_extension in ['.txt', '.md', '.html', '.py', '.js', '.cpp', '.java', '.c', '.rb', '.go', '.php']:
        return redirect(url_for('editor', title=filename, language=language, content=content))
    else:
        flash('Unsupported file type.')
        return redirect(url_for('start'))

@app.route('/execute_code', methods=['POST'])
def execute_code():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    language = request.form['language']
    title = request.form.get('title')
    if not title:
        flash('Title is required.')
        return redirect(url_for('start'))
    
    if not docker_client:
        output = "Docker is not available. Please ensure Docker is installed and running."
        return render_template('editor.html', content=content, title=title, output=output, language=language)
    
    language_configs = {
        'python': ('python:3.9-slim', ['python', '-c'], '.py'),
        'javascript': ('node:16-slim', ['node', '-e'], '.js'),
        'cpp': ('gcc:latest', ['g++', '-x', 'c++', '-', '-o', '/tmp/a.out; /tmp/a.out'], '.cpp'),
        'java': ('openjdk:11', ['sh', '-c', 'echo "$0" > Main.java && javac Main.java && java Main'], '.java'),
        'c': ('gcc:latest', ['gcc', '-x', 'c', '-', '-o', '/tmp/a.out; /tmp/a.out'], '.c'),
        'ruby': ('ruby:3.0-slim', ['ruby', '-e'], '.rb'),
        'go': ('golang:latest', ['go', 'run', '-'], '.go'),
        'php': ('php:8.0-cli', ['php', '-r'], '.php'),
    }
    
    if language not in language_configs:
        output = 'Unsupported language'
        return render_template('editor.html', content=content, title=title, output=output, language=language)
    
    image, cmd_prefix, ext = language_configs[language]
    base_title, current_ext = os.path.splitext(title)
    if current_ext.lower() == ext:
        filename = title
    else:
        filename = f"{base_title}{ext}"

    try:
        container = docker_client.containers.run(
            image=image,
            command=cmd_prefix + [content],
            mem_limit='128m',
            cpu_period=100000,
            cpu_quota=50000,
            remove=True,
            stdout=True,
            stderr=True,
            stdin_open=False,
            network_disabled=True,
        )
        output = container.decode('utf-8')
    except docker.errors.ContainerError as e:
        output = e.stderr.decode('utf-8') if e.stderr else str(e)
    except DockerException as e:
        output = f"Execution error: {str(e)}"

    new_document = Document(title=base_title, content=content, user_id=session['user_id'], language=language)
    db.session.add(new_document)
    db.session.commit()

    return render_template('editor.html', content=content, title=title, output=output, language=language)

@app.route('/profile/progress')
def profile_progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('profile_progress.html', user=user)

@app.route('/profile/problems')
def profile_problems():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    documents = Document.query.filter_by(user_id=session['user_id']).all()
    return render_template('profile_problems.html', user=user, documents=documents)

if __name__ == '__main__':
    app.run(debug=True)