import tweepy
import logging
import sys
import time


# set up logging
# guidance for getting to this to work from StackOverflow
# http://stackoverflow.com/a/28195348/1031615

logger = logging.getLogger()

# Clear the logs between runs.
# This stops it from repeating a ton of times
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

fhandler = logging.FileHandler(filename='twitter_bot.log', mode='a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler.setFormatter(formatter)

# Put logs in a logfile
logger.addHandler(fhandler)
# Print logs to the screen
logger.addHandler(logging.StreamHandler())
# Silence the other libraries
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("tweepy").setLevel(logging.WARNING)

# Only show info messages that are info or more important
logger.setLevel(logging.INFO)


##########################################
# Set up Markoff model fun times!        #
##########################################

import markovify

with open('tdo.txt', 'r') as f:
    tdo = f.read()
    tdo_model = markovify.Text(tdo)
    
def _generate_status(screen_name=None):
    status = ""
    if screen_name != None:
        status += '.@' + screen_name + ' '
    status += tdo_model.make_short_sentence(140 - len(status))
    return status


########################################
# Private Functions
########################################

# fetches up to 800 tweets a user was mentioned in
# can call at most 75 times per minute
def _fetch_mentions(api, last_id=None):
    try:
        mentions = api.mentions_timeline(since_id=last_id)

        return [t._json for t in mentions]
    except Exception as e:
        logger.warning('[Twitter API Error] {}'.format(e))
        return []


# Assume the bot responded to the most recent @mention when it boots up
def _initial_last_responded_id(api):
    responses = _fetch_mentions(api)
    if len(responses) == 0:
        return None
    return responses[0]['id']



########################################
# Public Functions
########################################

# Set up the tweepy API handler.
def set_up_tweepy(consumer_key, consumer_secret, access_token, access_token_secret):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


# Reply to all @mentions after a certain tweet
def reply_to_mentions(api, last_responded_id):
    tweets = _fetch_mentions(api, last_responded_id)
    if len(tweets) != 0:
        last_responded_id = tweets[0]['id']
        responses = [(t['user']['screen_name'], t['text']) for t in tweets]
        for (screen_name, text) in responses:
            post_status(api, screen_name)
    return last_responded_id


# Post a status at @mention someone if there is someone to mention
def post_status(api, mention=None):
    status = _generate_status(mention)
    try:
        api.update_status(status)
        logger.info('[Posting status] {}'.format(status))
    except Exception as e:
        logger.warning('[Twitter API Error] {}'.format(e))


########################################
# Run Loop Functions
########################################

starttime = time.time()

def main():
    if sys.argv[4] is not None:
        # Set up the API
        api = set_up_tweepy(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
        schedule_tweeting(api, interval=125.0)

def schedule_reply_to_mentions(api, last_id=None, interval = 30.0):
    # If we don't have the id of the last @mention, use the most recent @mention'ed tweet
    if last_id == None:
        last_id = _initial_last_responded_id(api)
    # Reply to all the tweets that we have to and save the new last responded to id
    last_id = reply_to_mentions(api, last_id)
    # Wait a period of time before calling the function again
    time.sleep(interval - ((time.time() - starttime) % interval))
    # And start the whole thing over!
    schedule_reply_to_mentions(api, last_id, interval)


def schedule_tweeting(api, interval=60.0):
    post_status(api)
    # Wait a period of time before calling the function again
    time.sleep(interval - ((time.time() - starttime) % interval))
    # And start the whole thing over!
    schedule_tweeting(api, interval=interval)

if __name__ == "__main__":
    main()

