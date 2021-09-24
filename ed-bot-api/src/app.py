import os
import json
import requests
import boto3

from Sendersqs import sendSQSMessage
from helper import verifySlackSig

from flask import Flask, request, jsonify
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ED_THREAD_URL = "https://us.edstem.org/api/threads"

def slackCallBackBody(command='', data=' Successfully :tada:'):
    ackData = json.dumps({
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Command:{command}, Updated {data}"
                }
            }
        ]})
    return ackData

def commentStatus(tid='', name='', endors=False):
    response = "Responsed to "
    if endors:
        response = "Endorsed"

    ackData = json.dumps({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{response} * {name} on EdDiscussion. Thread:{tid} :tada:"
                }
            }
        ]})
    return ackData

def getToken():
    client = boto3.client(
        's3',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_KEY']
    )

    obj = client.get_object(Bucket=os.environ['S3_AUTH_TOKEN_BUCKET'], Key='token.txt')
    token = obj['Body'].read()
    return token


TOKEN = getToken()


def findThreadID(blocks):
    d = dict()
    for i in blocks:
        if i['block_id'] == 'ThID':
            d['tid'] = i['text']['text']
        if i['block_id'] == 'writerName':
            d['name'] = i['text']['text']
    return d


app = Flask(__name__)


@app.route("/health")
def home():
    res = {"message": "OK"}
    return jsonify(res)


@app.route('/slack/actions', methods=["POST"])
def handleAction():
    d = json.loads(request.form['payload'])
    # app.logger.info(d)
    d['internalType'] = 'action'
    isSent = sendSQSMessage(d)
    app.logger.info(f"Post SQS Message {isSent}")
    return ('', 400) if not isSent else ('', 200)

@app.route('/slack/commands/announce', methods=["POST"])
def handleAnnounce():
    slackTimeStamp = request.headers['X-Slack-Request-Timestamp']
    slackSignature = request.headers['X-Slack-Signature']

    isValid = verifySlackSig(slackSignature, slackTimeStamp, request.get_data())
    if not isValid:
        return '', 400

    data = request.form.to_dict()
    data['internalType'] = 'anncounce'
    isSent = sendSQSMessage(data)
    return ('', 400) if not isSent else ('', 200)

@app.route('/slack/commands/token', methods=["POST"])
def handleToken():
    slackTimeStamp = request.headers['X-Slack-Request-Timestamp']
    slackSignature = request.headers['X-Slack-Signature']

    isValid = verifySlackSig(slackSignature, slackTimeStamp, request.get_data())
    if not isValid:
        return '', 400

    data = request.form.to_dict()

    text = data['text']
    app.logger.info(text)
    textParts = text.split()
    if len(textParts) < 2:
        return ('Error: Missing sub command', 200) 

    if textParts[0] == 'update':
        s3 = boto3.resource('s3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
            aws_secret_access_key=os.environ['AWS_SECRET_KEY']
        )
        s3.Object(os.environ['S3_AUTH_TOKEN_BUCKET'], 'token.txt').put(Body=textParts[1])
        return 'Token Updated', 200

    if textParts[0] == 'show':
        pass 
    # r= requests.post(url=resUrl, headers={"Content-Type": "application/json"}, data=json.dumps({'msg':'Missing sub command'}))
    return  ('', 200)

if __name__ == "__main__":
    app.run(debug=True, port=os.environ["PORT"])
