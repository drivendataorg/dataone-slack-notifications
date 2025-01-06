import json
import logging
import os
from xml.etree import ElementTree

import boto3

from botocore.exceptions import ClientError
from chalice import Chalice, Cron
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SECRET_MANAGER_NAME = os.environ["SECRET_MANAGER_NAME"]
REGION_NAME = os.environ["REGION_NAME"]
DATAONE_API_URL = os.environ["DATAONE_API_URL"].strip("/")
DATAONE_DATA_SOURCE = os.environ["DATAONE_DATA_SOURCE"]
DATAONE_SUMMARY_URL = os.environ["DATAONE_SUMMARY_URL"].strip("/")

app = Chalice(app_name="dataone-package-notify")
SECRETS = {}


def get_secret(key):
    logger.info(f"Getting secret {key}")
    if key not in SECRETS:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=REGION_NAME)

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=SECRET_MANAGER_NAME
            )
        except ClientError as e:
            raise e

        SECRETS.update(json.loads(get_secret_value_response["SecretString"]))
    return SECRETS[key]


def get_metrics():
    response = requests.get(f"{DATAONE_API_URL}/object?start=0&count=0")
    tree = ElementTree.fromstring(response.content)
    object_count = int(tree.attrib.get("total"))

    response = requests.get(
        f"{DATAONE_API_URL}/query/solr/?q=datasource:*{DATAONE_DATA_SOURCE}&wt=json&rows=0&stats=true&stats.field=size"
    )
    total_size = response.json()["stats"]["stats_fields"]["size"]["sum"]

    logger.info(
        f"Retrieved metrics object count {object_count} and total size {total_size}"
    )

    return {
        "text": "Repository report",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":earth_americas: Repository report :earth_americas:",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"For more detail visit the <{DATAONE_SUMMARY_URL}|Summary of Holdings> page",
                    }
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Object count*: {object_count:,}\n*Total size*: {total_size / 2**30:.2f}GiB",
                    }
                ],
            },
        ],
    }


@app.schedule(Cron("0", "12", "?", "*", "MON-FRI", "*"))
def size_report(event):
    logger.info("Lambda triggered by schedule")
    metrics = get_metrics()
    webhook_url = get_secret("SLACK_WEBHOOK_URL")

    response = requests.post(
        webhook_url,
        json=metrics,
        headers={"Content-type": "application/json"},
    )

    logger.info(f"Response from Slack webhook: {response.status_code}")
