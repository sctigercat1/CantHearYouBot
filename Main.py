#Copyright: Copyright 2016 /u/sagiksp, all right reserved.
#Seriously, don't be a dick.

import praw, time, re, json
import os.path

# Variables
# Consider adding these in from a config file?
user_agent = ""
username = ""
password = ""

# Constants
dataStoreName = 'data.json'
Triggers = ('what', 'wut', 'wat')

footer = """***

[^^^Beep ^^^boop.](https://np.reddit.com/r/CantHearYouBot/)""" # Text to be in the end of a message

lastUpdated = 0

# users = {'username': lasttimeused}
# yelled = {'parentpostid': timeresponded}
if os.path.exists(dataStoreName):
    # Read from the existing datastore.
    with open(dataStoreName, 'r') as data:
        data = json.loads(data.read())
        users = data['users']
        yelled = data['yelled']
else:
    # Form a new datastore and save it.
    users = {}
    yelled = {}
    with open(dataStoreName, 'w') as data:
        data.write(json.dumps({'users': users, 'yelled': yelled}))

def check_condition(c):
    # Is the comment a trigger, and is the author not rate limited.
    return (c.body.lower().rstrip('?') in Triggers) and (not RateLimit(c.author.name))

def bot_action(c,r):
    global users, yelled
    # Action the bot preforms
    parent = r.get_info(thing_id=c.parent_id)

    # Check for if the comment is a top-level reply
    if c.is_root:
        return

    # If parent is bot and comment is not "in da but"
    if parent.author.name == username and parent.body != "In da but":
        return

    # Check for if the bot's already responded to this comment
    if parent.id in yelled:
        return

    # Save some data about the user and post
    users[c.author.name] = yelled[parent.id] = int(time.time())

    if check_condition(parent): # What What
        try:
            c.reply("In da but")
        except:
            pass
        return

    lines = parent.body.split("\n")
    total = ""
    for line in lines:
        # Parse line and add to total
        total += parseLine(line)
    try:
        c.reply(total + footer) # Reply
        print("\n\n"+total+"\n") # Debug
    except Exception as e:
        print('ERROR WHEN REPLYING:',e)
        return

def RateLimit(username):
    # Boolean. If user has used the bot in the last 5 minutes, stop.
    if username == "sagiksp":
        return False

    currentTime = int(time.time())
    lastUseTime = users[username] if username in users else 0

    return (currentTime - lastUseTime) <= (60 * 5) # 5 minutes

def parseLine(line):
    # Some basic parsing rules that bypass the rest of our logic.
    if line == '' or line == '***': # Restore split newline // Horizontal rule
        return line + '\n'
    
    # Bold the line
    if line[0] != '#':
        line = '#' + line
    
    # Uppercase the line, all except URLs.
    ldata = re.split(r"(\[.*?\]\(.*?\))", line) # Reddit markdown URLs.
    line = ''
    for content in ldata:
        if not content.startswith('['): # Typical string
            content = content.upper()
        else:
            # URL, so let's break it up a little further and capitalize the title also.
            url_groups = re.search(r"\[(.*)\]\((.*)\)", content)
            content = '[' + url_groups.group(1).upper() + '](' + url_groups.group(2) + ')'
        
        line += content
    
    # Finally, return!
    return line + '\n'

def updateData():
    global users, yelled

    currentTime = int(time.time())

    # USERS
    # NB: http://stackoverflow.com/a/11941855/2676181
    for user in users.keys():
        if (currentTime - users[user]) >= (60 * 60): # Keep users for an hour (rate limit-->only 5 mins)
            del users[user]

    # YELLED
    for yell in yelled.keys():
        if (currentTime - yelled[yell]) >= (60 * 60 * 24 * 5): # Keep yelled parents for 5 days
            del yelled[yell]

    # Save the new data.
    with open(dataStoreName, 'w') as data:
        data.write(json.dumps({'users': users, 'yelled': yelled}))

    # Debug
    print('Updated the datastores @',currentTime)
    return

r = praw.Reddit(user_agent)

r.login(username=username,password=password)

# Use try/finally to run one last command after a keyboardinterrupt
try:
    for c in praw.helpers.comment_stream(r, 'all'):
        if check_condition(c):
            bot_action(c,r) # Actually go through the motions.

        if (int(time.time()) - lastUpdated) >= (60 * 30): # 30 minutes
            # We haven't updated our database in while, do so now
            updateData()
            lastUpdated = int(time.time())
finally:
    # Alternatively, update the datastore on exit.
    updateData()
