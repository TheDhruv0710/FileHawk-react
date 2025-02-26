import datetime
from flask import Blueprint, request, render_template, session, flash, jsonify
import pandas as pd
from flask_app.models import db, Schedule
import json, os
from flask_app.models import AuditLog


def load_server_config():
    with open('server_config.json', 'r') as file:
        config = json.load(file)
    return config


app_blueprint = Blueprint('app_blueprint', __name__, template_folder="templates")

@app_blueprint.route('/login')
def login():
    return render_template('login.html')

@app_blueprint.route('/create_server')
def create_server():
    return render_template('server.html')


@app_blueprint.route('/save_server', methods=['POST'])
def save_server():
    servername = request.form['servername']
    host = request.form['host']
    username = request.form['username']
    password = request.form['password']

    with open('server_config.json', 'r') as f:

        cred = json.load(f)
    cred[servername] = {
        "hostname": host,
        "username": username,
        "password": password
    }

    with open('server_config.json', 'w') as f:
        json.dump(cred,f)


    return 'Credentials saved successfully!'


@app_blueprint.route('/')
def index():
    username = session.get('username', 'Guest')
    return render_template('login.html', username=username)

@app_blueprint.route('/dashboard')
def dashboard():
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

@app_blueprint.route('/create_automation', methods=['GET', 'POST'])
def create_automation():
    os.makedirs("config_files", exist_ok=True)
    if request.method == 'POST':
        try:
            # 1. Extract data from the form
            automation_name = request.form['automation_name']
            archival_process_name = request.form['archival_process_name']
            email_from = request.form['email_from']
            email_to = request.form['email_to']
            process_name = request.form['process_name']
            file_path = request.form['file_path']
            archive_file_path = request.form['archive_file_path']
            file_extension = request.form['file_extension']
            file_purge_days = int(request.form['file_purge_days'])
            archive_delete_days = int(request.form['archive_delete_days'])

            # 2. Construct the config.json structure
            config_data = {
                "EmailDetails": {
                    "EmailFrom": email_from,
                    "EmailDefaultTo": email_to
                },
                "ArchivalProcessName": {
                    archival_process_name: {
                        "Process": {
                            process_name: [
                                {
                                    "FilePath": file_path,
                                    "ArchiveFilePath": archive_file_path,
                                    "FileExtension": file_extension,
                                    "FilePurgeDays": file_purge_days,
                                    "Action": "Archive"
                                },
                                {
                                    "ArchiveFilePath": archive_file_path,
                                    "FilePurgeDays": archive_delete_days,
                                    "Action": "Delete"
                                }
                            ]
                        },
                        "Email": {
                            "EmailTo": email_to,
                            "EmailSubject": f"{archival_process_name} File Archival",
                            "EmailSuccessBody": f"Team - {archival_process_name} File archival completed.",
                            "EmailFailureBody": f"Team - {archival_process_name} File archival failed, please refer the log for more details."
                        }
                    }
                }
            }

            # 3. Save the config.json file
            config_filepath = os.path.join("config_files", f"{automation_name}.json")
            os.makedirs("config_files", exist_ok=True)
            with open(config_filepath, 'w') as f:
                json.dump(config_data, f, indent=4)

            # 4. Run the archival process
            main.main(config_filepath)

            flash(f'Automation "{automation_name}" created and executed successfully!')
            return redirect(url_for('app_blueprint.view_automation'))
        except Exception as e:
            flash(f'Error creating or executing automation: {str(e)}')
    return render_template('create_automation.html')

@app_blueprint.route('/view_automation')
def view_automation():
    config_files = [f for f in os.listdir("config_files") if f.endswith('.json')]
    automations = []
    for config_file in config_files:
        with open(os.path.join("config_files", config_file), 'r') as f:
            config_data = json.load(f)
            automations.append({
                'name': config_file[:-5],
                'config': config_data
            })
    return render_template('view_automation.html', automations=automations)


@app_blueprint.route('/poc_for_state', methods=['GET', 'POST'])
def poc_for_state():
    if request.method == 'POST':
        try:
            file = request.files['excel_file']
            df = pd.read_excel(file)
            session['poc_data'] = df.to_html(index=False, classes='table table-striped')
            flash('Excel file imported successfully!')
        except Exception as e:
            flash(f'Error importing Excel file: {str(e)}')
    return render_template('poc.html', poc_data=session.get('poc_data'))


@app_blueprint.route('/update_config', methods=['GET', 'POST'])
def update_config():
    with open('server_config.json', 'r') as f:
        server_config = json.load(f)

    if request.method == 'POST':
        # Get the form data
        server_name = request.form['server-name']
        hostname = request.form['hostname']
        username = request.form['username']
        password = request.form['password']

        # Update the server_config.json file
        with open('server_config.json', 'r+') as f:
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
