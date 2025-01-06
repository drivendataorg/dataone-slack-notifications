# DataONE Package Notifications

A simple [Chalice](https://aws.github.io/chalice/index.html)/Slack notification system for a DataONE repository.

## Prerequisites

[Install Chalice](https://aws.github.io/chalice/quickstart.html) in your local environment. Using [uv](https://docs.astral.sh/uv/) for example:

```sh
uv venv --python 3.12
source .venv/bin/activate
uv sync
chalice
```

## Setup

### Slack App

- Create a new [Slack App](https://api.slack.com/apps).
- Select "From scratch" and give a descriptive name like "DataONE Notifications".
- Select your Slack workspace.
- In the "Basic Information" tab, click "Show" for the "Signing Secret" credential. (You will save this as the `SLACK_SIGNING_SECRET` in the AWS Secrets Manager.)
- Click the "Incoming Webhooks" tab in the sidebar.
- Toggle the "Activate Incoming Webhooks" switch to "On".
- Click "Add New Webhook to Workspace" and authorize the app to post to the desired Slack channel.
- Copy the Webhook URL. (You will save this as the `SLACK_WEBHOOK_URL` in AWS Secrets Manager.)

### Secrets

- Visit the [Secrets Manager](https://aws.amazon.com/secrets-manager/) resource in AWS.
- Create a new secret using "Store a new secret".
- Select Secret Type "Other type of secret"
- Create two Key/value pairs: `SLACK_SIGNING_SECRET` and `SLACK_WEBHOOK_URL` using the values from the Slack App.
- Click Next, and provide a secret name, such as `prod/DataONENotifications/env`. (You will need this value later as `SECRET_MANAGER_NAME` in `config.json`.)
- Click Next, Next, and Store to create your secret.
- View the secret you just created. Copy the Secret ARN. (You will need it to update `policy-dev.json`.)

### Chalice

Update the `dataone-package-notify/.chalice/config.json` file to include the following environment variables:

```json
  "environment_variables": {
    "REGION_NAME": "us-east-1",
    "SECRET_MANAGER_NAME": "prod/DataONENotifications/env",
    "DATAONE_API_URL": "https://cib.dataone.org/metacat/d1/mn/v2",
    "DATAONE_DATA_SOURCE": "CIB",
    "DATAONE_SUMMARY_URL": "https://cib.dataone.org/profile"
  }
```

Update `dataone-package-notify/.chalice/policy-dev.json` to include the Secret ARN to allow the Lambda instance to read your secrets:

```json
"Resource": [
    "arn:aws:secretsmanager:us-east-1:954976317582:secret:prod/<...>"
]
```

Deploy your chalice app with:

```sh
chalice deploy
```
