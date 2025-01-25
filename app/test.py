import json
from datetime import datetime, timezone
import requests

AIRFLOWAPIID = "csp_af_api_nprd"
AIRFLOWAPIPS = "10Txklk9"


def airflow_exec(dag_id):
    logical_date = datetime.now(timezone.utc).isoformat()
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', }
    data = {"execution_date": logical_date}
    base_url = "http://apvrd75942:4293//api/v1/"
    url = f"{base_url}dags/{dag_id}/dagRuns"
    response = requests.post(url, headers=headers, auth=(AIRFLOWAPIID, AIRFLOWAPIPS), data=json.dumps(data))
    if response.status_code != 200:
        print(response.json())
        print("Unable to trigger a run.")
        return False
    else:
        print(response.json())
    return True
