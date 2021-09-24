import datetime
import os
import requests
import json
import boto3

from dateutil import parser
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

COURSE_ID = os.environ['ED_COURSE_NUM']
SLACK_HOOK_URL = os.environ['SLACK_CALLBACK_URL']


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


def fetchThreads():
    PARAMS = {'limit': 30, 'sort': "new"}

    Headers = {"x-token": TOKEN}
    edURL = f"https://us.edstem.org/api/courses/{COURSE_ID}/threads?"
    print("Feting Threads:" + edURL)

    r = requests.get(url=edURL, params=PARAMS, headers=Headers)
    print("Feting Threads Status Code:", r.status_code)

    if r.status_code == 401:
        authPayload = json.dumps({
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Token Invalid, Please use command => /token update <value>"
                    }
                }
            ]})
        r = requests.post(url=SLACK_HOOK_URL, data=authPayload)
        print('Send update Token message =>', r.status_code)
        return []

    if r.status_code != 200:
        print("Got ERROR=>", r.text)
        return []

    data = r.json()
    allThreads = data["threads"]
    # print(allThreads)
    result = list(filter(lambda x: (x['is_answered'] == False and x['is_seen'] == False), allThreads))
    #result = list(filter(lambda x: (x['id'] == 573041), allThreads))
    #print(result)
    if not len(result):
        print("NO New Posts Found!")
        '''
        b = json.dumps({
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No New Threads!"
                    }
                }
            ]})
        r = requests.post(url=SLACK_HOOK_URL,  data=b)
        print("Send Slack Hook for empty", r.text, r.status_code)
        '''
    print(f"Found {len(result)} New Threads")
    return result


def sendSlackMsg(threadDict):
    for singleThread in threadDict:
        print("************************")
        #print(singleThread)
        sname = singleThread['user']['name']
        thId = f"{singleThread['id']}"
        content = singleThread['document']
        isPrivate = singleThread['is_private']
        createdAt = singleThread['created_at']
        title = singleThread['title']
        date_time_obj = parser.parse(createdAt).strftime("%Y-%m-%d %H:%M")

        print("Processing Thread:", thId)
        payload = json.dumps({
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "block_id": "ThID",
                    "text": {
                        "type": "mrkdwn",
                        "text": thId,
                    }
                },
                                {
                    "type": "section",
                    "block_id": "private",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Private: *{isPrivate}*"
                    }
                },
                {
                    "type": "section",
                    "block_id": "writerName",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Author Name: *{sname}* - Time: {date_time_obj}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                            "type": "mrkdwn",
                        "text": content
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                                "type": "plain_text",
                                "text": "ENDORSE",
                                        "emoji": True
                        },
                        "value": "endorse",
                        "action_id": "endorse"
                    }
                },
                {
                    "dispatch_action": True,
                    "type": "input",
                    "block_id": "reply_bot",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reply_action"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Reply Here:",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },

            ]
        })
        r = requests.post(url=SLACK_HOOK_URL,  data=payload)
        print("Sending Slack Msg:", r.status_code, r.text)
        if r.status_code == 200:
            # Thread posted to Slack mark it as Seen in ED
            seenURL = f"https://us.edstem.org/api/threads/{thId}/read"
            sRes = requests.post(url=seenURL, headers={"x-token": TOKEN})
            print("seen Request=>", sRes.status_code, r.text)
        #break


def run(event, context):
    current_time = datetime.datetime.now().time()
    name = context.function_name
    print("Your cron function " + name + " ran at " + str(current_time))
    threads = fetchThreads()
    sendSlackMsg(threads)


if __name__ == "__main__":
    threads = fetchThreads()
    sendSlackMsg(threads)