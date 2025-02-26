from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


def func_send_email(self, p_from_list, p_to_list, p_email_subject, p_email_body, p_attachmentPath='',
                    p_attachmentFileList=None):
    try:

        email_server = 'mailo2.uhc.com'
        msg = MIMEMultipart()

        body_part = MIMEText(p_email_body, 'plain')
        msg['Subject'] = p_email_subject
        msg['From'] = p_from_list
        msg['To'] = p_to_list
        msg.attach(body_part)

        for attachFile in p_attachmentFileList or []:
            with open(p_attachmentPath + attachFile, 'rb') as file:
                msg.attach(MIMEApplication(file.read(), Name=attachFile))

        server = smtplib.SMTP(email_server)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()

    except Exception as e1:
        print("Error while sending Email.")
