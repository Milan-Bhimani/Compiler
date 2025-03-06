from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
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
@login_required
def submit_solution(problem_id):
    solution = request.form['solution']
    # Here you would add logic to check the solution
    # For simplicity, we'll assume the solution is correct
    progress = Progress(user_id=current_user.id, problem_id=problem_id, status='Solved')
    db.session.add(progress)
    db.session.commit()
    flash('Solution submitted successfully!')
    return redirect(url_for('user_profile.problem', problem_id=problem_id))

@user_profile_bp.route('/progress')
@login_required
def progress():
    progress = Progress.query.filter_by(user_id=current_user.id).all()
    return render_template('profile/progress.html', progress=progress)