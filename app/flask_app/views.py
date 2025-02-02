import datetime
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from flask_app.models import db, Schedule
import json

def load_server_config():
    with open('server_config.json', 'r') as file:
        config = json.load(file)
    return config

app_blueprint = Blueprint('app_blueprint', __name__)


@app_blueprint.route('/')
def index():
    username = session.get('username', 'Guest')
    return render_template('landing_page.html', username=username)

@app_blueprint.route('/create_task', methods=['GET', 'POST'])
def create_task():
    # Render the create task page
    config = load_server_config()

    server_keys = list(config.keys())
    return render_template('create_task.html', server_keys=server_keys, dependent_server_keys=server_keys)

@app_blueprint.route('/tasks')
def view_tasks():
    # Fetch all tasks from the database
    tasks = Schedule.query.all()
    return render_template('view_tasks.html', tasks=tasks)

@app_blueprint.route('/stats', methods=['GET', 'POST'])
def stats():
    # Render the statistics page
    config = load_server_config()
    server_keys = list(config.keys())
    return render_template('stats.html', server_keys=server_keys)

@app_blueprint.route('/add_task', methods=['POST'])
def add_task():
    # Create a new task from form data
    task = Schedule(
        task_id=request.form['task_id'],
        schedule=request.form['schedule'],
        filename=request.form['filename'],
        filepath=request.form['filepath'],
        server_key=request.form['server_key'],
        retries=int(request.form.get('retries', 3)),
        retry_delay=int(request.form.get('retry_delay', 60)),
        timeout=int(request.form.get('timeout')) if request.form.get('timeout') else None,
        dependency_server_key=request.form.get('dependent_server_keys'),
        command=request.form.get('command')
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for('app_blueprint.create_task'))

@app_blueprint.route('/current_jobs_data')
def current_jobs_data():
    # Fetch current job data for the dashboard
    running_jobs = Schedule.query.filter(Schedule.retries > 0).all()
    running_jobs_count = len([task for task in running_jobs if task.check_file()])

    failed_jobs = Schedule.query.filter(Schedule.retries <= 0).all()
    failed_jobs_count = len([task for task in failed_jobs if not task.check_file()])

    waiting_jobs = Schedule.query.filter(Schedule.retries > 0).all()
    waiting_jobs_count = len([task for task in waiting_jobs if not task.check_file()])

    retrying_jobs_count = len([task for task in running_jobs if not task.check_file()])  # Retrying jobs

    total_jobs = Schedule.query.count()

    return jsonify({
        'running_jobs': running_jobs_count,
        'failed_jobs': failed_jobs_count,
        'waiting_jobs': waiting_jobs_count,
        'retrying_jobs': retrying_jobs_count,
        'total_jobs': total_jobs
    })

@app_blueprint.route('/task_summary')
def task_summary():
    # Fetch task statistics based on server and file pattern filters
    server = request.args.get('server', 'all')
    file_pattern = request.args.get('file_pattern', '')

    tasks = Schedule.query

    if server != 'all':
        tasks = tasks.filter_by(server_key=server)
    if file_pattern:
        tasks = tasks.filter(Schedule.filename.like(f"%{file_pattern}%"))

    # Example statistics calculation
    success = tasks.filter(Schedule.retries > 0).count()
    failed = tasks.filter(Schedule.retries <= 0).count()
    waiting = tasks.count() - (success + failed)

    return jsonify({
        'labels': ['Success', 'Failed', 'Waiting'],
        'statistics': [success, failed, waiting]
    })

@app_blueprint.route('/recent_activity')
def recent_activity():
    # Fetch recent activity of tasks
    activity = []
    tasks = Schedule.query.all()

    for task in tasks:
        status_message = "completed successfully" if task.check_file() else "failed"
        activity.append({'task_id': task.task_id, 'status': status_message, 'timestamp': task.timestamp})

    return jsonify(activity)

@app_blueprint.route('/delete_task/<int:id>', methods=['DELETE'])
def delete_task(id):
    # Delete a task by ID
    task = Schedule.query.get(id)
    if not task:
        return jsonify({'message': 'Task not found'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})