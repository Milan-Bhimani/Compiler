from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from io import BytesIO
import docker
from docker.errors import DockerException
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from extensions import db

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:kittu@db.ysgdpkhwfimomuptacnx.supabase.co:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

# Import models
from models import User, Document, Problem, Progress

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables with error handling
try:
    with app.app_context():
        db.create_all()
except OperationalError as e:
    print(f"Database connection failed: {e}")
    raise

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('start'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
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
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/start', methods=['GET', 'POST'])
@login_required
def start():
    if request.method == 'POST':
        title = request.form['title']
        language = request.form['language']
        if not title:
            flash('Title is required.')
            return redirect(url_for('start'))
        return redirect(url_for('editor', title=title, language=language))
    return render_template('start.html')

@app.route('/editor')
@login_required
def editor():
    title = request.args.get('title')
    language = request.args.get('language')
    if not title or not language:
        return redirect(url_for('start'))
    return render_template('editor.html', title=title, language=language)

@app.route('/new')
@login_required
def new_file():
    return redirect(url_for('start'))

@app.route('/save', methods=['POST'])
@login_required
def save():
    content = request.form['content']
    title = request.form['title']
    language = request.form['language']
    if not title:
        flash('Title is required.')
        return redirect(url_for('start'))
    new_document = Document(title=title, content=content, user_id=current_user.id, language=language)
    db.session.add(new_document)
    db.session.commit()
    flash('Document saved successfully!')
    return redirect(url_for('editor', title=title, language=language))

@app.route('/save_and_download', methods=['POST'])
@login_required
def save_and_download():
    content = request.form['content']
    title = request.form['title']
    language = request.form['language']
    
    if not title:
        flash('Title is required.')
        return redirect(url_for('start'))

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

    expected_ext = language_map.get(language, '.txt')
    if not title.lower().endswith(expected_ext):
        filename = f"{title}{expected_ext}"
    else:
        filename = title

    mime_type = mime_types.get(language, 'text/plain')

    new_document = Document(
        title=title,
        content=content,
        user_id=current_user.id,
        language=language
    )
    db.session.add(new_document)
    db.session.commit()

    response = send_file(
        BytesIO(content.encode('utf-8')),
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename
    )
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/open', methods=['POST'])
@login_required
def open_file():
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
@login_required
def execute_code():
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

    new_document = Document(title=base_title, content=content, user_id=current_user.id, language=language)
    db.session.add(new_document)
    db.session.commit()

    return render_template('editor.html', content=content, title=title, output=output, language=language)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)