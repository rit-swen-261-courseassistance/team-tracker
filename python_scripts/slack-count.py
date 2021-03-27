"""

Usage instructions: Set up a slack app as per the README

Install the following dependencies:
pip install slackclient

Usage:

python slack.py -t <OAuth access token from step 7> [-o <start date>] [-l <end date>]

E.g.
python slack.py -t xoxp-************-************-************-******************************** -o 11/5/2019 -l 11/25/2019

Dates are formatted mm/dd/yyyy, the format can be changed by including a --format parameter
https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior

"""

import argparse
import time
import datetime
from collections import Counter

import slack
from slack.errors import SlackApiError

parser = argparse.ArgumentParser(description="Count the number of messages sent by a team member")
parser.add_argument("--token", "-t", help="The access token from your slack app", required=True)
parser.add_argument("--oldest", "-o", help="The date of the earliest message to start counting at")
parser.add_argument("--latest", "-l", help="The date of the latest message to stop counting at")
parser.add_argument("--format", help="The format for date/time strings", default="%m/%d/%Y")
args = parser.parse_args()

client = slack.WebClient(token=args.token)

count = {}
counterStandup = {}
groups = {}
users = {}
users_backwards = {}
oldest_time = None
if args.oldest:
    oldest_time = int(time.mktime(datetime.datetime.strptime(args.oldest, args.format).timetuple()))
latest_time = None
if args.latest:
    latest_time = int(time.mktime(datetime.datetime.strptime(args.latest, args.format).timetuple()))

response = client.users_list()
for member in response["members"]:
    users[member["id"]] = member["profile"]["real_name"]
    users_backwards[member["profile"]["real_name"]] = member["id"]

response = client.usergroups_list(include_users="true")
for group in response["usergroups"]:
    groups[group["name"]] = group["users"]

response = client.conversations_list(types="public_channel,private_channel")
for channel in response["channels"]:

    # Skip enterprise level shared channels
    if "is_global_shared" in channel and channel["is_global_shared"]:
        continue

    options = {
        "channel": channel["id"],
        "count": 1000
    }
    if oldest_time:
        options["oldest"] = oldest_time
    if latest_time:
        options["latest"] = latest_time

    try:
        response = client.conversations_history(**options)
    except SlackApiError:
        print("Error in " + channel["name"])

    for message in response["messages"]:
        # If a bot_user verifies it is not a virtual standup bot.
        if "user" not in message:
            try:
                username = message["username"]
            except KeyError:
                continue
            openParentheses = username.find("(")
            username = username[:openParentheses-1]
            try:
                userId = users_backwards[username]
                if userId not in counterStandup:
                    counterStandup[userId] = 0
                counterStandup[userId] += 1
            except KeyError:
                print("Username: ", username, " not found")
        else:
            if "virtual-standup" in channel["name"]:
                if message["user"] not in counterStandup:
                    counterStandup[message["user"]] = 0
                counterStandup[message["user"]] += 1
            else:
                if message["user"] not in count:
                    count[message["user"]] = 0
                count[message["user"]] += 1

    #print(channel["name"])
    #for user in count:
    #    print("\t", users[user], ": ", count[user], sep="")
    #if "virtual-standup" in channel["name"]:
    #    counterStandup = Counter(count) + Counter(counterStandup)
    #else:
    #    counterNonStandup = Counter(count) + Counter(counterNonStandup)

#for key in CounterDict:
#    print(users[key], ", ", CounterDict[key])

for group in groups:
    print(group, " - Non-Standups:")
    for name in groups[group]:
        try:
            print("\t", users[name], ": ", count[name])
        except KeyError:
            continue
    print(group, " - Virtual-Standups:")
    for name in groups[group]:
        try:
            print("\t", users[name], ": ", counterStandup[name])
        except KeyError:
            continue
