"""
DAG Description : NAS Archival Process

Author          : Narendiran Ramalingam

Date            : 01/10/2025

Version         : 1.0

History         : 

v1.0: Narendiran Ramalingam -> NAS Archival Process

"""


from airflow import DAG
from datetime import datetime, timedelta, date
from CspCommonFunction import  func_airflow_ssh_oper, func_env_variables_extract
from airflow.operators.dummy_operator import DummyOperator
from CspCommonFunction import func_adhoc_request_check, task_failure_callback
from airflow.sensors.weekday import DayOfWeekSensor
from airflow.models import Variable
import pendulum
import os.path


# DAG ID is same as file name
DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

# Default timezone to CST
tz_local = pendulum.timezone("America/Chicago")


region = Variable.get("region")

if (region == 'prod'):

    lstrDefaultRegion = "aspfpr01"
    depends_on_past=True
    wait_for_downstream=True
    EMAIL = ['Narendiran.Ramalingam@optum.com','cspfacets-ctsom_dl@ds.uhc.com','EligibilityTeamCaprica@ds.uhc.com']


else:

    lstrDefaultRegion = "aspfts05"
    depends_on_past=True
    wait_for_downstream=True
    EMAIL = ['Narendiran.Ramalingam@optum.com']




# Schedule interval
lstrScheduleInterval = "0 2 * * 0"

default_args = {
    'owner': 'csp_ntjb',
    'depends_on_past': False,
    'start_date': datetime(2024, 10, 19, tzinfo=tz_local),
    'email': EMAIL,
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 0,
    'retry_delay': timedelta(days=1),
}


#Loading the env variables
ldictPackage = func_env_variables_extract()

ssh_oper_1={
    'pTaskId':"SSH_Operator1",
    'pDefaultRegion':lstrDefaultRegion,
    'EnvVariables':ldictPackage,
    'pSshConnID':"EnvVariables[ENV]['windows']",
    'pSshCommand':"'python E:/FSG/Scripts/NasArchival/src/main.py'",
    'pSoftFail':False
}

with DAG(DAG_ID,  tags=['RUNS EVERY Sunday 2AM'], default_args=default_args, max_active_runs=1, schedule_interval=lstrScheduleInterval, catchup=False) as dag:

    StartOfDAG = DummyOperator(
        task_id="StartOfDAG",
        depends_on_past=True,
        wait_for_downstream=True,
        dag=dag)

    EndOfDAG = DummyOperator(
        task_id='EndOfDAG', 
        dag=dag)

    StartOfDAG >> func_adhoc_request_check() >> func_airflow_ssh_oper(dag,**ssh_oper_1) >> EndOfDAG
    StartOfDAG >> EndOfDAG
    