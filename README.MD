## EDiscussion-slack-bot
#### A Slack integration for EDiscussion website where EDiscussion lacks compatabilty with mobile devices. The project is split into the following components:
## 1) ed-scheduler
#### a lambda function invoked by eventBridge cron job to look for new Threads on Ed and post it in a slack channel. 
## 2) ed-bot-api:
#### Main api will receive requests (commands, actions, webhooks) from Slack and publish it to an SQS FIFO queue for offline processing. Slack impose 3 second timeout on requests it's sends  

## 3) Sqs-reader
#### a lambda function will be triggered by sqs events to process users actions from slack and send it to ED through their API


## Architecture
![Alt text](assets/architecture.png?raw=true "Title")