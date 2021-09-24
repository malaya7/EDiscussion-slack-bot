import json 

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