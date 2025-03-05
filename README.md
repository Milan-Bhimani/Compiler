# Real-Time Collaborative Text Editor

## Project Setup

1. **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd Project 1
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Initialize the database**:
    ```bash
    python init_db.py
    ```

5. **Run the Flask application**:
    ```bash
    python app.py
    ```

6. **Open your browser and navigate to**:
    ```
    http://127.0.0.1:5000/
    ```

## Features

- User authentication (login/register)
- Real-time collaborative text editing
- Save, download, open, and create new files

## File Structure

- `app.py`: Main Flask application
- `models.py`: Database models
- `init_db.py`: Script to initialize the database
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript)
