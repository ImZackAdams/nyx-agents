import tweepy
import time

# Authenticate to Twitter
auth = tweepy.OAuth1UserHandler(
    consumer_key='yZ251MvWTTgHkTzWIuZ7cRPRL',
    consumer_secret='axLXTtZg05L6hmF812zpd46hMopaYcxGfIqkvFRIPCmmriFmEh',
    access_token='1440847096525967362-JgWqGHvk5NU30tFp4msUYpZ5YklMQw',
    access_token_secret='b2vtlM7RKr00Ip9Mzrn4dgC7mNK53McptrFhrhhiKxRN9'
)

api = tweepy.API(auth)

# Get rate limit status
rate_limit_status = api.rate_limit_status()

# Function to convert epoch time to human-readable time
def convert_epoch_to_human(epoch_time):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(epoch_time))

# Print human-readable rate limit status
print("Twitter API Rate Limits:\n")
for category, endpoints in rate_limit_status['resources'].items():
    print(f"Category: {category}")
    for endpoint, limits in endpoints.items():
        print(f"  Endpoint: {endpoint}")
        print(f"    Limit: {limits['limit']}")
        print(f"    Remaining: {limits['remaining']}")
        print(f"    Reset Time: {convert_epoch_to_human(limits['reset'])}")
    print()
