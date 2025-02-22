import datetime
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from flask_app.models import db, Schedule
import json, os
from flask_app.models import AuditLog


def load_server_config():
    with open('/app/server_config.json', 'r') as file:
        config = json.load(file)
    return config


app_blueprint = Blueprint('app_blueprint', __name__, template_folder="/app/flask_app/templates")


@app_blueprint.route('/create_server')
def create_server():
    return render_template('server.html')


@app_blueprint.route('/save_server', methods=['POST'])
def save_server():
    servername = request.form['servername']
    host = request.form['host']
    username = request.form['username']
    password = request.form['password']

    with open('/app/server_config.json', 'r') as f:

        cred = json.load(f)
    cred[servername] = {
        "hostname": host,
        "username": username,
        "password": password
    }

    with open('/app/server_config.json', 'w') as f:
        json.dump(cred,f)


    return 'Credentials saved successfully!'


@app_blueprint.route('/')
def index():
    username = session.get('username', 'Guest')
    return render_template('landing_page.html', username=username)


@app_blueprint.route('/create_task', methods=['GET', 'POST'])
def create_task():
    config = load_server_config()
    server_keys = list(config.keys())
    return render_template('create_task.html', server_keys=server_keys, dependent_server_keys=server_keys)


@app_blueprint.route('/tasks')
def view_tasks():
    tasks = Schedule.query.all()
    return render_template('view_tasks.html', tasks=tasks)


@app_blueprint.route('/stats', methods=['GET', 'POST'])
def stats():
    config = load_server_config()
    server_keys = list(config.keys())
    return render_template('stats.html', server_keys=server_keys)


@app_blueprint.route('/audit_logs')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_logs.html', logs=logs)


@app_blueprint.route('/update_config', methods=['GET', 'POST'])
def update_config():
    with open('/app/server_config.json', 'r') as f:
        server_config = json.load(f)

    if request.method == 'POST':
        # Get the form data
        server_name = request.form['server-name']
        hostname = request.form['hostname']
        username = request.form['username']
        password = request.form['password']

        # Update the server_config.json file
        with open('/app/server_config.json', 'r+') as f:
            config = json.load(f)
            config[server_name] = {
                'hostname': hostname,
                'username': username,
                'password': password
            }
            f.seek(0)  # Reset file pointer to the beginning
            json.dump(config, f, indent=4)  # Write the updated config
            f.truncate()  # Truncate the file in case the new config is shorter

        return "Configuration updated successfully!"  # Or redirect to another page

    return render_template('update_config.html', server_config=server_config)


@app_blueprint.route('/add_task', methods=['POST'])
def add_task():
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
        command=request.form.get('command'),
        status='WAITING'  # Set initial status to WAITING
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for('app_blueprint.create_task'))


@app_blueprint.route('/delete_config/<server_name>', methods=['DELETE'])
def delete_config(server_name):
    with open('server_config.json', 'r+') as f:
        config = json.load(f)
        if server_name in config:
            del config[server_name]
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
            return jsonify({'message': 'Configuration deleted successfully'}), 200
        else:
            return jsonify({'message': 'Configuration not found'}), 404


@app_blueprint.route('/current_jobs_data')
def current_jobs_data():
    try:
        running_jobs = Schedule.query.filter_by(status='RUNNING').count()
        failed_jobs = Schedule.query.filter_by(status='FAILED').count()
        waiting_jobs = Schedule.query.filter_by(status='WAITING').count()
        retrying_jobs = Schedule.query.filter_by(status='RETRYING').count()
        total_jobs = Schedule.query.count()

        return jsonify({
            'running_jobs': running_jobs,
            'failed_jobs': failed_jobs,
            'waiting_jobs': waiting_jobs,
            'retrying_jobs': retrying_jobs,
            'total_jobs': total_jobs
        })
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'Failed to fetch task data'}), 500


@app_blueprint.route('/task_summary')
def task_summary():
    server = request.args.get('server', 'all')
    file_pattern = request.args.get('file_pattern', '')

    tasks = Schedule.query

    if server != 'all':
        tasks = tasks.filter_by(server_key=server)
    if file_pattern:
        tasks = tasks.filter(Schedule.filename.like(f"%{file_pattern}%"))

    success = tasks.filter_by(status='SUCCESS').count()
    failed = tasks.filter_by(status='FAILED').count()
    waiting = tasks.filter_by(status='WAITING').count()

    return jsonify({
        'labels': ['Success', 'Failed', 'Waiting'],
        'statistics': [success, failed, waiting]
    })


@app_blueprint.route('/recent_activity')
def recent_activity():
    activity = []
    tasks = Schedule.query.all()

    for task in tasks:
        activity.append({'task_id': task.task_id, 'status': task.status, 'timestamp': task.timestamp})
    return jsonify(activity)


@app_blueprint.route('/delete_task/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Schedule.query.get(id)
    if not task:
        return jsonify({'message': 'Task not found'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})


@app_blueprint.route('/trend_data')
def trend_data():
    time_range = request.args.get('time_range')
    server = request.args.get('server', 'all')
    file_pattern = request.args.get('file_pattern', '')

    try:
        start_date_str, end_date_str = time_range.split(' - ')
        start_date = datetime.datetime.strptime(start_date_str, '%m/%d/%Y').date()
        end_date = datetime.datetime.strptime(end_date_str, '%m/%d/%Y').date()
    except ValueError:
        return jsonify({'error': 'Invalid date range format'}), 400

    tasks = Schedule.query.filter(Schedule.timestamp.between(start_date, end_date))

    if server != 'all':
        tasks = tasks.filter_by(server_key=server)

    if file_pattern:
        tasks = tasks.filter(Schedule.filename.like(f"%{file_pattern}%"))

    # Group tasks by date and count successes and failures
    data = {}
    for task in tasks:
        date_str = task.timestamp.strftime('%Y-%m-%d')
        if date_str not in data:
            data[date_str] = {'successes': 0, 'failures': 0}
        if task.status == 'SUCCESS':
            data[date_str]['successes'] += 1
        elif task.status == 'FAILED':
            data[date_str]['failures'] += 1

    # Prepare data for Chart.js
    labels = list(data.keys())
    successes = [data[label]['successes'] for label in labels]
    failures = [data[label]['failures'] for label in labels]

    return jsonify({'labels': labels, 'successes': successes, 'failures': failures})
