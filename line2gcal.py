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
from datetime import datetime as dt
from time import mktime

import datetime

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'line2gcal'
TZ = 'Asia/Taipei'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    credential_dir = os.path.join(os.curdir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'line2gcal.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def parseArgs(inputString):
    argv = shlex.split(inputString)
    # parser = argparse.ArgumentParser()
    # argv = parser.parse_args(args=arr)
    if (argv[0] != "/gcal"):
        exit(0)
    Args = namedtuple("Args", "title when duration who location description")
    args = Args(duration=60, title=argv[1], when=argv[2], description="", location="", who="")
    # TODO: fill the args

    return args


def lambda_handler(event, context):
    processCommand(event['result'][0]['content']['text'])
    return 'Hello from Lambda'


def processCommand(command):
    args = parseArgs(command)

    setTimezone()
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendarId = getCalendarIdByName(service, "family")
    createEvent(service, calendarId, args)


def main():
    processCommand("/gcal 'Hello World' +1d")


def createEvent(service, calendarId, args):
    start = parseDatetime(args.when)
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
    service.events().insert(
        calendarId=calendarId,
        body=event
    ).execute()


def getCalendarIdByName(service, name):
    calendarList = service.calendarList().list().execute().get('items', [])
    calendarId = ""
    for calendar in calendarList:
        if (calendar['summary'] == name):
            calendarId = calendar['id']
            break
    return calendarId


def setTimezone():
    os.environ['TZ'] = TZ


def parseDatetime(str):
    c = pdt.Constants()
    p = pdt.Calendar(c)
    result, r = p.parse(str)
    return dt.fromtimestamp(mktime(result))


if __name__ == '__main__':
    main()
