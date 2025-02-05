from flask_app.database_config import setup_app
from flask_app.views import app_blueprint
import threading
import os
import subprocess

app = setup_app()

# Register the blueprint
app.register_blueprint(app_blueprint)

def run_scheduler():
    # Set the working directory to the directory of the current script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Use subprocess to run scheduler.py as a separate process
    subprocess.run(["python", "scheduler/scheduler.py"])

if __name__ == '__main__':
    print(app.url_map)

    # Create and start a thread for the scheduler
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Run the Flask app
    app.run(debug=True)