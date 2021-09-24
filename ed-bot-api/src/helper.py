import hashlib
import hmac
import os 
from typing import Tuple

#Jwong Seceret
SLACK_SECERTE= os.environ['SLACK_SECERTE']

def verifySlackSig(slackSig, timestamp, body):
  version = 'v0'
  body = body.decode()
  basestr = f'{version}:{timestamp}:{body}'.encode("utf-8")
  slack_signing_secret = bytes(SLACK_SECERTE, "utf-8")

  mySig = "v0=" +  hmac.new(slack_signing_secret, basestr, hashlib.sha256).hexdigest()
  return True  if hmac.compare_digest(mySig, slackSig) else False