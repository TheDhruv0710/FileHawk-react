import re
import threading
import time
import json
import croniter
import os
from datetime import datetime, timezone
from run import app

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_app.models import Schedule, db
import paramiko

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
config_file_path = os.path.join(BASE_DIR, "server_config.json")

with open(config_file_path, "r") as f:
    SERVER_CONFIG = json.load(f)

# Database setup
DB_PATH = os.path.join(BASE_DIR, './instance/scheduler.db')  # Adjust for instance folder
engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)
session = Session()

# Airflow API credentials
AIRFLOWAPIID = "csp_af_api_nprd"
AIRFLOWAPIPS = "10Txklk9"

def check_file(server, filepath, filename):

    print("Checking file on remote server...")


    server_config = SERVER_CONFIG.get(server, {})
    hostname = server_config.get('hostname')
    username = server_config.get('username')
    password = server_config.get('password')
    server_path = server_config.get('path', '')

    full_path = os.path.join(server_path, filepath, filename)
    print(f"Checking file at: {full_path}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {hostname}...")
        ssh.connect(hostname, username=username, password=password)

        sftp = ssh.open_sftp()

        print(f"Accessing directory: {filepath}")
        files = sftp.listdir(filepath)

        # Filter files using regex
        matched_files = [file for file in files if re.search(filename, file)]
        sftp.close()
        if len(matched_files) == 1:
            print(f"Matched files in {filepath}:")
            for file in matched_files:
                print(f" - {file}")
            return True
        elif len(matched_files) > 1:
            print(f"Multiple files matched in {filepath}: {matched_files}")
        else:
            print(f"No files matched the pattern {filename} in {filepath}.")
            return False
    except paramiko.ssh_exception.SSHException as e:
        print(e)
        return False
    finally:
        ssh.close()
        print(f"Disconnected from {hostname}")

def airflow_exec(dag_id, replace_microseconds=True):
    logical_date = datetime.now(timezone.utc).isoformat()
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    data = {
        "execution_date": logical_date,
        "replace_microseconds": replace_microseconds  # Include the replace_microseconds option
    }
    base_url = "http://apvrd75942:4293//api/v1/"
    url = f"{base_url}dags/{dag_id}/dagRuns"
    response = requests.post(url, headers=headers, auth=(AIRFLOWAPIID, AIRFLOWAPIPS), json=data)
    if response.status_code != 200:
        print(response.json())
        print("Unable to trigger a run.")
        return False
    else:
        print(response.json())
    return True

def execute_command(server, command):
    if server == 'Airflow':
        airflow_exec(command)
    else:
        airflow_exec(command)
    # Simulate running a command on the dependent server
    print(f"Executing command on {server}: {command}")

def process_schedule(schedule):
    print(f"Processing config {schedule.task_id}")
    server_key = schedule.server_key
    dependency_server_key = schedule.dependency_server_key
    retries = schedule.retries
    retry_delay = schedule.retry_delay
    timeout = schedule.timeout
    command = schedule.command
    filepath = schedule.filepath
    filename = schedule.filename

    start_time = datetime.now()
    retry_count = 0

    with app.app_context(app):
        schedule.status = 'RUNNING'
        db.session.commit()

        try:
            while retry_count < retries and (datetime.now() - start_time).total_seconds() < timeout:
                if check_file(server_key, filepath, filename):
                    execute_command(dependency_server_key, command)
                    schedule.status = 'SUCCESS'
                    db.session.commit()
                    return True  # Task successful
                else:
                    print("File not found..")
                    schedule.status = 'RETRYING'
                    db.session.commit()

                time.sleep(retry_delay)
                retry_count += 1
            else:
                if schedule.status!= 'SUCCESS':
                    schedule.status = 'FAILED'
                    db.session.commit()
                    print(f"Task {schedule.task_id} failed after all retries.")
                    return False  # Task failed
        except Exception as e:
            print(f"An error occurred: {e}")
            schedule.status = 'FAILED'
            db.session.commit()
            return False

def scheduler_loop():
    while True:
        print("Scheduler is running...")
        now = datetime.now(timezone.utc)
        schedules = session.query(Schedule).all()

        for schedule in schedules:
            cron = croniter.croniter(schedule.schedule, schedule.timestamp)
            next_run = cron.get_next(datetime)
            next_run_local = next_run.replace(tzinfo=timezone.utc)
            print(now)
            print(next_run_local)
            print(next_run_local <= now)
            if next_run_local <= now:
                process_schedule(schedule)
                schedule.timestamp = now
                session.commit()

        time.sleep(5)

def start_scheduler():
    scheduler_thread = threading.Thread(target=scheduler_loop())
    scheduler_thread.daemon = True
    scheduler_thread.start()