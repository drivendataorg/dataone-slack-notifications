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


def sum_object_sizes(
    start: int = 0,
    page_size: int = 1000,
    max_count: int = 3000,
    running_total_size: int = 0,
    running_count: int = 0,
):
    response = requests.get(f"{DATAONE_API_URL}/object?start={start}&count={page_size}")
    tree = ElementTree.fromstring(response.content)
    running_count += len(tree)
    total_this_time = sum(int(item.find("size").text) for item in tree)
    running_total_size += total_this_time
    if max_count is None:
        max_count = int(tree.attrib.get("total"))
    logger.debug(
        f"start {start}, "
        f"running_total_size {running_total_size}, "
        f"running_count {running_count}, "
        f"len(tree) {len(tree)}, "
        f"batch_size {page_size}, "
        f"total {max_count}, "
        f"total_this_time {total_this_time}"
    )
    if (len(tree) > 0) or (running_count > max_count):
        running_total_size += sum_object_sizes(
            start=start + page_size,
            page_size=page_size,
            max_count=max_count,
            running_total_size=running_total_size,
            running_count=running_count,
        )

    return running_total_size


def get_metrics():
    response = requests.get(f"{DATAONE_API_URL}/object?start=0&count=0")
    tree = ElementTree.fromstring(response.content)
    object_count = int(tree.attrib.get("total"))

    total_size = sum_object_sizes()

    logger.info(f"Retrieved metrics object count {object_count} and total size {total_size}")

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
                        "text": f"*Object count*: {object_count:,}\n*Total size*: {total_size / 10**9:.2}GB",
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
