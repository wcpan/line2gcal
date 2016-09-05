from __future__ import print_function

import traceback
from collections import namedtuple
import httplib2
import os
from apiclient import discovery
import oauth2client.tools
from oauth2client import client
import parsedatetime as pdt
import shlex
import boto3
from datetime import datetime as dt
from time import mktime
import datetime
from linebot.client import LineBotClient
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


def get_credentials(mid):
    store = DynamodbStorage(mid)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        flow.redirect_uri = client.OOB_CALLBACK_URN
        authorize_url = flow.step1_get_authorize_url()
        msg = "Please authorize application: " + authorize_url + "\n" + "/gcal-auth [code]"
        raise Exception(msg)
    return credentials


def lambda_handler(event, context):
    try:
        msg = process_input(event['result'][0]['content']['from'], event['result'][0]['content']['text'])
        send_msg(event['result'][0]['content']['from'], msg)
    except Exception as err:
        send_msg(event['result'][0]['content']['from'], err.message)
    return "Done"


def process_gcal(mid, argv):
    GcalArgs = namedtuple("Args", "title when duration who location description calendar")
    args = GcalArgs(duration=60, title=argv[1], when=argv[2], description="", location="", who="", calendar=None)
    # TODO: fill the args

    credentials = get_credentials(mid)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_id = get_calendar_by_name(service, args.calendar)
    return create_event(service, calendar_id, args)


def process_gcal_auth(mid, argv):
    flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = client.OOB_CALLBACK_URN
    credentials = flow.step2_exchange(code=argv[1])
    store = DynamodbStorage(mid)
    store.put(credentials)
    return "Link successful"


def process_help():
    return """
/gcal [title] [when]
/gcal-auth [code]
/gcal-default [calendar_name]
/help
"""


def process_gcal_default(mid, argv):
    pass


def process_input(mid, input_string):
    set_timezone()
    argv = shlex.split(input_string)
    if argv[0][0] != '/':
        raise Exception("Not a command")
    cmd = argv[0][1:]
    if cmd == "gcal":
        return process_gcal(mid, argv)
    elif cmd == "gcal-auth":
        return process_gcal_auth(mid, argv)
    elif cmd == "gcal-default":
        return process_gcal_default(mid, argv)
    elif cmd == "help":
        return process_help()
    else:
        raise Exception("Unsupported command - " + cmd)


def main():
    try:
        print(process_input("sigmapan", "/gcal 'Hello World' +1d"))
        # print(process_input("sigmapan", "/gcal-auth 4/6Krpo2_4GB-30reEFhpq5robnymXEDdRX9kXzl7S2OY"))
    except Exception as err:
        print(err)


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
    if not name:
        return "primary"
    calendar_list = service.calendarList().list().execute().get('items', [])
    calendar_id = None
    for calendar in calendar_list:
        if calendar['summary'] == name:
            calendar_id = calendar['id']
            break
    if not calendar_id:
        raise Exception("Calendar " + name + " not found")
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
