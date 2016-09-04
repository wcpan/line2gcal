from __future__ import print_function
from collections import namedtuple
import httplib2
import os
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import parsedatetime as pdt
import shlex
import boto3
from datetime import datetime as dt
from time import mktime
import datetime
from linebot.client import LineBotClient
import argparse
import json

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'credentials/client_secret.json'
APPLICATION_NAME = 'line2gcal'
TZ = 'Asia/Taipei'


class DynamodbStorage(oauth2client.client.Storage):
    def locked_delete(self):
        self.table.delete_item(
            self.table.deleteItem(
                Key={
                    'id': self.id
                }
            )
        )

    def locked_get(self):
        credentials = None
        val = self.table.get_item(
            Key={
                'id': self.id
            }
        )
        if 'Item' in val:
            credentials = client.Credentials.new_from_json(val['Item']['credential'])
        return credentials

    def locked_put(self, credentials):
        self.table.put_item(
            Item={
                'id': self.id,
                'credential': credentials.to_json()
            }
        )

    def __init__(self, id):
        super(DynamodbStorage, self).__init__()
        dynamodb = boto3.resource('dynamodb', region_name="ap-northeast-1")
        self.table = dynamodb.Table('line2gcal')
        self.id = id


def get_credentials():
    store = DynamodbStorage("sigmapan")
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
    return credentials


def parse_args(inputString):
    argv = shlex.split(inputString)
    # parser = argparse.ArgumentParser()
    # argv = parser.parse_args(args=arr)
    if argv[0] != "/gcal":
        exit(0)
    Args = namedtuple("Args", "title when duration who location description")
    args = Args(duration=60, title=argv[1], when=argv[2], description="", location="", who="")
    # TODO: fill the args

    return args


def lambda_handler(event, context):
    process_command(event['result'][0]['content']['text'])
    send_msg(event['result'][0]['content']['from'], "Done!!")
    return "ok"


def process_command(command):
    args = parse_args(command)

    set_timezone()
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_id = get_calendar_by_name(service, "family")
    return create_event(service, calendar_id, args)


def main():
    print(process_command("/gcal 'Hello World' +1d"))


def create_event(service, calendarId, args):
    start = parse_datetime(args.when)
    end = start + datetime.timedelta(minutes=args.duration)
    event = {
        'summary': args.title,
        'location': args.location,
        'description': args.description,
        'start': {
            'dateTime': start.isoformat(),
            'timeZone': TZ,
        },
        'end': {
            'dateTime': end.isoformat(),
            'timeZone': TZ,
        },
    }
    event = service.events().insert(
        calendarId=calendarId,
        body=event
    ).execute()
    return "event created: " + event.get('htmlLink')


def get_calendar_by_name(service, name):
    calendar_list = service.calendarList().list().execute().get('items', [])
    calendar_id = ""
    for calendar in calendar_list:
        if calendar['summary'] == name:
            calendar_id = calendar['id']
            break
    return calendar_id


def set_timezone():
    os.environ['TZ'] = TZ


def parse_datetime(str):
    c = pdt.Constants()
    p = pdt.Calendar(c)
    result, r = p.parse(str)
    return dt.fromtimestamp(mktime(result))


def send_msg(mid, msg):
    credentials = json.load(open("credentials/line_bot_credential.json"))
    line_bot_client = LineBotClient(**credentials)
    line_bot_client.send_text(
        to_mid=mid,
        text=msg
    )


if __name__ == '__main__':
    main()
