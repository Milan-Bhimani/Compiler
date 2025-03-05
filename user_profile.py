from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from models import Problem, Progress, db

user_profile_bp = Blueprint('user_profile', __name__)

@user_profile_bp.route('/problems')
def problems():
    problems = Problem.query.all()
    return render_template('profile/problems.html', problems=problems)

@user_profile_bp.route('/problem/<int:problem_id>')
def problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    return render_template('profile/problem.html', problem=problem)

@user_profile_bp.route('/submit_solution/<int:problem_id>', methods=['POST'])
def submit_solution(problem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    solution = request.form['solution']
    # Here you would add logic to check the solution
    # For simplicity, we'll assume the solution is correct
    progress = Progress(user_id=session['user_id'], problem_id=problem_id, status='Solved')
    db.session.add(progress)
    db.session.commit()
    flash('Solution submitted successfully!')
    return redirect(url_for('user_profile.problem', problem_id=problem_id))

@user_profile_bp.route('/progress')
def progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    progress = Progress.query.filter_by(user_id=session['user_id']).all()
    return render_template('profile/progress.html', progress=progress)
