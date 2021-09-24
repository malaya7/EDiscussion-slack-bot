import json
import logging
import boto3
import os
from botocore.exceptions import ClientError

def sendSQSMessage(msg_body= dict()):
    # Send the SQS message
    QUEUE_URL_FIFO= os.environ['SQS_QUEUE_URL']
    sqs_client = boto3.client('sqs', region_name='us-west-1')

    try:
        # MessageGroupId is only for FIFO queue
        msg = sqs_client.send_message(QueueUrl=QUEUE_URL_FIFO, MessageBody=json.dumps(msg_body), MessageGroupId='xor', MessageDeduplicationId='dup1')
    except ClientError as e:
        logging.error(e)
        return None
    return True, msg

