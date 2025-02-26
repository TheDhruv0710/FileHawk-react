import os
import zipfile

import json
from datetime import datetime, timedelta
import argparse

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.log import log, close_log
from dotenv import load_dotenv

load_dotenv()

def get_runtime_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processes", help="Chrysalis Processes", type=str, required=False, default="None"
    )
    args = parser.parse_args()
    log.info("Run time argument - Specific Processes Only: " + args.processes)

    return args

def send_alert(sender, recipient, subject, body, cc_addresses=None):
    attachedFile = None
    logPath = os.path.join(os.getcwd(), "log")
    for file in os.listdir(logPath):
        if file.endswith(".log"):
            attachedFile = file
            break
    
    msg = MIMEMultipart()
    email_body = MIMEText(body, 'plain')
    msg['From'] = sender  
    msg['To'] = recipient
    if cc_addresses is not None:
        msg['Cc'] = cc_addresses
    msg['Subject'] = subject
    msg.attach(email_body)
    if attachedFile is not None:
        with open(os.path.join(logPath, attachedFile), 'rb') as file:
            msg.attach(MIMEApplication(file.read(), Name=attachedFile))
    # smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 25))
    server = smtplib.SMTP("mailo2.uhc.com", smtp_port)
    server.sendmail(sender, recipient, msg.as_string())

# function to delete log file after sending email
def delete_log():
    try:
        if os.path.exists("log"):
            for file in os.listdir("log"):
                if file.endswith(".log"):
                    os.remove(os.path.join("log", file))
                    log.info(f"Deleted log file {file}")
    except Exception as e:
        log.error(f"An error occurred while deleting the log file: {e}")

def load_config(config_file):
    with open(config_file, 'r') as file:
        return json.load(file)

def delete_old_files(directory_path, days_old):
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)

        for year in os.listdir(directory_path):
            year = os.path.join(directory_path, year)
            if os.path.isdir(year):
                for directory in os.listdir(year):
                    directory = os.path.join(year, directory)
                    if os.path.isdir(directory):
                        for filename in os.listdir(directory):
                            file_path = os.path.join(directory, filename)
                            if os.path.isfile(file_path):
                                modified_time = os.path.getmtime(file_path)
                                modified_date = datetime.fromtimestamp(modified_time)
                                if modified_date < cutoff_date:
                                    os.remove(file_path)
                                    log.info(f"Deleted {file_path}")
    except Exception as e:
        log.error("An error occurred while deleting files:")
        raise e

def zip_and_archive_files(directory_path, archive_folder, file_extensions, days_old):
    try:
        if not os.path.exists(archive_folder):
            os.makedirs(archive_folder)
        cutoff_date = datetime.now() - timedelta(days=days_old)
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(tuple(ext.lower() for ext in file_extensions.split(','))):
                modified_time = os.path.getmtime(file_path)
                modified_date = datetime.fromtimestamp(modified_time)
                if modified_date < cutoff_date:
                    year_folder = modified_date.strftime('%Y')
                    month_folder = modified_date.strftime('%B')
                    archive_subfolder = os.path.join(archive_folder, year_folder, month_folder)
                    if not os.path.exists(archive_subfolder):
                        os.makedirs(archive_subfolder)
                    zip_file_name = f"{filename}.zip"
                    zip_file_path = os.path.join(archive_subfolder, zip_file_name)
                    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(file_path, filename)
                        log.info(f"Added {file_path} to {zip_file_path}")
                    os.remove(file_path)
                    log.info(f"Zipped and moved {filename} to {archive_subfolder}.")
    except Exception as e:
        log.error("An error occurred while zipping and archiving files:")
        raise e

def main():
    try:
        # Get the runtime arguments
        args = get_runtime_arguments()

        p_process_id ="CHRYSALIS"

        # Load configuration
        config = load_config(os.path.join(os.getcwd(), os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config/configDetails3.json')))

        try:
            email_info = config["ArchivalProcessName"][p_process_id]["Email"]
            # sender = email_info["EmailTo"]
            sender = config["EmailDetails"]["EmailFrom"]
            recipient = email_info["EmailTo"]
            subject = email_info["EmailSubject"]
            success_body = email_info["EmailSuccessBody"]
            failure_body = email_info["EmailFailureBody"]
            if "EmailCc" in email_info:
                cc_addresses = email_info["EmailCc"]
            else:
                cc_addresses = None
        except KeyError as e:
            log.error(f"{e} field is missing from the configuration")
            return e
        except Exception as e:
            log.error(f"An error occurred while retrieving email information: {e}")
            return e

        if args.processes != "None":
            set_processes = [process.strip() for process in args.processes.split(",")]
        else:
            set_processes = []
        for key in config["ArchivalProcessName"][p_process_id]["Process"].keys():
            if len(set_processes) == 0:
                log.info(f"Process: {key}")
                for config_data in config["ArchivalProcessName"][p_process_id]["Process"][key]:
                    if config_data["Action"] == "Archive":
                        archival_file_path = config_data["FilePath"]
                        archive_directory = config_data["ArchiveFilePath"]
                        file_extensions = config_data["FileExtension"]
                        days_old = config_data["FilePurgeDays"]

                        log.info("==============++++++++++++=====================")
                        log.info("Action: Archive")
                        log.info(f"Archival File Path: {archival_file_path}")
                        log.info(f"Archival Directory: {archive_directory}")
                        log.info(f"Accepted File Extension: {file_extensions}")
                        log.info(f"File Purge Days: {days_old}")
                        zip_and_archive_files(archival_file_path, archive_directory, file_extensions, days_old)
                        log.info("Files archived successfully.")
                        log.info("==============++++++++++++=====================")
                    if config_data["Action"] == "Delete":
                        archival_file_path = config_data["ArchiveFilePath"]
                        days_old = config_data["FilePurgeDays"]
                        log.info("==============++++++++++++=====================")
                        log.info("Action: Delete")
                        log.info(f"Archival File Path: {archival_file_path}")
                        log.info(f"File Purge Days: {days_old}")
                        delete_old_files(archival_file_path, days_old)
                        log.info("Files deleted successfully.")
                        log.info("==============++++++++++++=====================")
            else:
                if key in set_processes:
                    log.info(f"Process: {key}")
                    for config_data in config["ArchivalProcessName"][p_process_id]["Process"][key]:
                        if config_data["Action"] == "Archive":
                            archival_file_path = config_data["FilePath"]
                            archive_directory = config_data["ArchiveFilePath"]
                            file_extensions = config_data["FileExtension"]
                            days_old = config_data["FilePurgeDays"]

                            log.info("==============++++++++++++=====================")
                            log.info("Action: Archive")
                            log.info(f"Archival File Path: {archival_file_path}")
                            log.info(f"Archival Directory: {archive_directory}")
                            log.info(f"Accepted File Extension: {file_extensions}")
                            log.info(f"File Purge Days: {days_old}")
                            zip_and_archive_files(archival_file_path, archive_directory, file_extensions, days_old)
                            log.info("Files archived successfully.")
                            log.info("==============++++++++++++=====================")
                        if config_data["Action"] == "Delete":
                            archival_file_path = config_data["ArchiveFilePath"]
                            days_old = config_data["FilePurgeDays"]
                            log.info("==============++++++++++++=====================")
                            log.info("Action: Delete")
                            log.info(f"Archival File Path: {archival_file_path}")
                            log.info(f"File Purge Days: {days_old}")
                            delete_old_files(archival_file_path, days_old)
                            log.info("Files deleted successfully.")
                            log.info("==============++++++++++++=====================")
        try:
            if cc_addresses is not None:
                send_alert(sender, recipient, subject, success_body, cc_addresses)
            else:
                send_alert(sender, recipient, subject, success_body)
            log.info("Email alert sent successfully.")
        except Exception as e:
            log.error(f"An error occurred while sending email alert: {e}")
    except KeyError as e:
        log.error(f"{e} field is missing from the configuration file")
        try:
            if cc_addresses is not None:
                send_alert(sender, recipient, subject, failure_body, cc_addresses)
            else:
                send_alert(sender, recipient, subject, failure_body)
            log.info("Email alert sent successfully.")
        except Exception as e:
            log.error(f"An error occurred while sending email alert: {e}")
    except FileNotFoundError as e:
        log.error(f"File not found: {e}")
        try:
            if cc_addresses is not None:
                send_alert(sender, recipient, subject, failure_body, cc_addresses)
            else:
                send_alert(sender, recipient, subject, failure_body)
            log.info("Email alert sent successfully.")
        except Exception as e:
            log.error(f"An error occurred while sending email alert: {e}")
    except Exception as e:
        log.error(f"An error occurred while processing the configuration: {e}")
        try:
            if cc_addresses is not None:
                send_alert(sender, recipient, subject, failure_body, cc_addresses)
            else:
                send_alert(sender, recipient, subject, failure_body)
            log.info("Email alert sent successfully.")
        except Exception as e:
            log.error(f"An error occurred while sending email alert: {e}")
    
    close_log()
    delete_log()

if __name__ == "__main__":
    main()
