import json
import boto3
import os
import requests 

#from helper import findThreadID, createLog, failedMsg, commentStatus

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ED_THREAD_URL = "https://us.edstem.org/api/threads"
def findThreadID(blocks):
    d = dict()
    for i in blocks:
        if i['block_id'] == 'ThID':
            d['tid'] = i['text']['text']
        if i['block_id'] == 'writerName':
            d['name'] = i['text']['text']
    return d
  
def commentStatus(tid='', name='', endors=False, log=''):
    response = "Responsed to "
    if endors:
        response = "Endorsed"

    ackData = json.dumps({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{response} * {name} on EdDiscussion. Thread:{tid} :tada:\n {log}"
                }
            }
        ]})
    return ackData

def failedMsg(tid='', name='',log=''):
    response = "failed to respond to "

    ackData = json.dumps({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{response} * {name} on EdDiscussion. Thread:{tid} :sad:\n {log}"
                }
            }
        ]})
    return ackData

def createLog(ctx):
    group = ctx.log_group_name 
    strem = ctx.log_stream_name
    requst = ctx.aws_request_id
    fn = ctx.function_name
    res = f'{group}-{strem}-{requst}-{fn}'
    return res

def getToken():
    client = boto3.client(
        's3',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_KEY']
    )

    tokenS3Bucket = os.environ['S3_AUTH_TOKEN_BUCKET']
    obj = client.get_object(Bucket=tokenS3Bucket, Key='token.txt')
    token = obj['Body'].read()
    return token


TOKEN = getToken()

def slackCallBackBody(command='', data='Posted Successfully :tada:'):
    ackData = json.dumps({
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Command:{command}, {data}"
                }
            }
        ]})
    return ackData

def processSQS(event, context):
    print('SQS MESSAGE ---')
    loog = createLog(context)
    #SQS event only have Records array of messages(dict object)
    rec = event['Records']
    for msg in rec:
        jsonBody = msg['body']
        bodyData = json.loads(jsonBody)
        #print("SQS Message Body=>", bodyData)
        if bodyData['internalType'] == 'anncounce':
            print("***handleAnnounce***")
            handleAnnounce(bodyData, loog)
        if bodyData['internalType'] == 'action':
            print("***handleActions***")
            handleActions(bodyData, loog)

    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }

def handleAnnounce(data):
    textSplit = data['text'].split()
    
    title = textSplit[0] or ''
    text = ''.join(textSplit[1:])  or ''

    trigger = data['trigger_id']
    responseURL = data['response_url']
    slackCommand = data['command']

    # Send EDSTEM Annoucment request
    courseNum = os.environ['ED_COURSE_NUM']
    ThreadURL = f'https://us.edstem.org/api/courses/{courseNum}/threads'
    Headers = {"x-token": TOKEN, "Content-Type": "application/json"}

    postType = 'question' # should be annoucment
    threadPayload = {
        "thread": {
            "type": postType,
            "title": title,
            "category": "General",
            "subcategory": "",
            "subsubcategory": "",
            "content": f"<document version=\"2.0\"><paragraph>{text}</paragraph></document>",
            "is_pinned": False,
            "is_private": True,
            "is_anonymous": False,
            "is_megathread": False,
            "anonymous_comments": False
        }
    }
    payLoad = json.dumps(threadPayload)
    edResponse = requests.post(url=ThreadURL, headers=Headers, data=payLoad)
    
    print('ED Thread Status ==>>', edResponse.status_code,edResponse.text)

    slackPayload = slackCallBackBody(slackCommand)
    if edResponse.status_code != 201:
        slackPayload = slackCallBackBody(slackCommand, f"Failed with Status:{edResponse.status_code}")

    slackCall = requests.post(url=responseURL, headers={"Content-Type": "application/json"}, data=slackPayload)
    print("SlackCallBack status=>", slackCall.status_code, slackCall.text)

def handleActions(bodyData, loog):
    actionObject = bodyData['actions'][0]
    actionValue = actionObject['value']
    print("actionObject==>", actionObject)

    allBlocks = bodyData['message']['blocks']
    blockSData = findThreadID(allBlocks)
    thID = blockSData['tid']
    print("Thread ID=> ", thID)

    edRes = ''
    Headers = {"x-token": TOKEN, "Content-Type": "application/json"}
    endorsFlag = False
    
    # Make Endors Action in EDSTEM
    if actionValue == 'endorse':
        endorsFlag = True
        edRes = requests.post(url=f'{ED_THREAD_URL}/{thID}/endorse', headers=Headers)
    else:
        # Send ED STEAM answer
        edPayload = json.dumps({"comment": {
            "type": "answer",
            "content": f"<document version=\"2.0\"><paragraph> {actionValue} </paragraph></document>",
            "is_private": False,
            "is_anonymous": False
        }})
        edRes = requests.post(url=f'{ED_THREAD_URL}/{thID}/comments', headers=Headers, data=edPayload)

    print("EdResponse Status=>", edRes.status_code)
    print("EdResponse Response=>", edRes.text)

    # SEND SLACK REPLY
    ppload = commentStatus(thID, blockSData['name'], endorsFlag)
    
    if edRes.status_code > 399:
        ppload = failedMsg(thID, blockSData['name'], loog)

    print("sending Slack CallBack=>", ppload)
    r = requests.post(url=bodyData['response_url'], headers={"Content-Type": "application/json"}, data=ppload)
    print("Slack Call Status", r.status_code, r.text)


if __name__ == '__main__':
    EVENT= {'Records': [{'messageId': '5f20ff2a-2f35-4a63-85d6-e3e88159a264', 'receiptHandle': 'AQEBMXUPuI5g+YlIMKCjfFes1L59OKrZJs8dUlxNX7Pzb1HYJEIFVifF0Fyy7UIbo7WDhgwttXPQtiZXbmNeiz9pZCcvuilOLrbBZPGecnjUyI5jZKLHbFUj9y5PwKEgjeC4SzKiUhOU0/aiwx3nLhXuKBFzt7RGGaCrICuoqpb0d4gTvS11nmp64Awo16mVIpOeGAGQFWj0pmkcj7AQJuMuybXjomCjfa4gECWR370kDdtfQqaJgR5iX5Yz6I/ZUpxYw5oMxgM+AM0KWAA4p7A2rghKN6cqh8pDpdvpI9QEgKSdZWJpdZ1Ca5CxIZl/BKNYCyWv5cKxuMsxY/31FclvJykH1L9KyTPI94GhZ3+BwdC4q7jydiqIO6fhGY9TaHqlWTO5H3NbvEKXby+Ywp6waw==', 'body': '{"token": "kLNUnI4rA88yiC1CPuNvTZ2a", "team_id": "T019Z2K2P62", "team_domain": "hjt-workspace", "channel_id": "C029CHSA0F9", "channel_name": "bot-spam", "user_id": "U01AVKBEGTS", "user_name": "malaya", "command": "/announce", "text": "daskodkoasdoasdok", "api_app_id": "A02AHEBP9EC", "is_enterprise_install": "false", "response_url": "https://hooks.slack.com/commands/T019Z2K2P62/2358977118851/v9tyNoESIdPphtXEl1jQodTz", "trigger_id": "2355749516149.1339087091206.ade15b7123359dbdc87fd3b431a70b20"}', 'attributes': {'ApproximateReceiveCount': '1', 'SentTimestamp': '1628450171046', 'SenderId': 'AIDAZZBRTZSD4O3BKYGEN', 'ApproximateFirstReceiveTimestamp': '1628450171051'}, 'messageAttributes': {}, 'md5OfBody': 'cb0f5796d7438a8331468738dcd782c7', 'eventSource': 'aws:sqs', 'eventSourceARN': 'arn:aws:sqs:us-west-1:672266439815:ed-stem-queue', 'awsRegion': 'us-west-1'}]}
    processSQS(EVENT, '')

    """
    Sample SQS message, inside recoreds array
      {
         "messageId":"70f7f09b-f988-4fe3-b7d1-318885f29c1a",
         "receiptHandle":"AQEB4epV+Pt10UmRHAERwAb+i3BXVrsnReuKHO+SS3o8Hv4w8M6/ETA5MB01FMYKnpSaDrlsUs3sXavyK5EdCzPellaKCRvfWPqf7RklPdOf2ms2vd4hBjhxnuGj4hn7ltaOdlU6B8D3OJ+eaHZ/6wOK2/TZEQ8rslQfA5cgmL47sy0+eZuXIpixJMnduflg0dPAk6LFpi9k66Eyj+2xd6GrMfFfTldAtRxbdOVzPJTlBKUeYXyAE3ZwmAAVT8xOkYFUvYt2v40lNcWBNJoNlNfkcHsc5/VBR1MIq3pYe6hhHQ3SaDF2ooXCiya8xMhBxTzcCfhmOyHk8w/cyZeHDuaqquMghXGd9YfJxELUs+bKAa0MEZeIxKyy7j0hC/gHmATR5BE2KbBEgC/bEDpn4KXMtA==",
         "body":"{\"message\": \"ok\"}",
         "attributes":{
            "ApproximateReceiveCount":"1",
            "SentTimestamp":"1628433274238",
            "SenderId":"AIDAZZBRTZSD4O3BKYGEN",
            "ApproximateFirstReceiveTimestamp":"1628446068499"
         },
         "messageAttributes":{
            
         },
         "md5OfBody":"601d03e69139e812f4f7c6ea3bc1d382",
         "eventSource":"aws:sqs",
         "eventSourceARN":"arn:aws:sqs:us-west-1:672266439815:ed-stem-queue",
         "awsRegion":"us-west-1"
      }
    """ 
