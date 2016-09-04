import json
from linebot.client import LineBotClient

credentials = json.load(open("line_bot_credential.json"))
client = LineBotClient(**credentials)
client.send_text(
    to_mid="",
    text="hi"
)
