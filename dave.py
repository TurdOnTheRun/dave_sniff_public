import gspread
import tweepy
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import random
import os.path
import time
from datetime import datetime
import traceback
import requests
import json

BASEURL = '/home/pi/davidsniff/'
# BASEURL = '/home/maximilian/Documents/sudo/davidsniff/'
FILEFOLDER = BASEURL + 'files/'
ERRORLOG = BASEURL + 'errorlog.txt'

ADDRESS = "tz1PEkni8U4XKXLNtspcFF2jXkyGkfMyPjoL"
SALES_QUERY = """query Sales($address: String!) {
  hic_et_nunc_trade(order_by: {timestamp: desc}, where: {token: {creator: {address: {_eq: $address}}}}) {
    timestamp
    token {
      id
      title
      creator {
        address
      }
    }
    amount
    swap {
      price
    }
    buyer {
      address
      name
    }
  }
}
"""
COLLECTORS_QUERY = """query Sales {
  hic_et_nunc_trade(order_by: {timestamp: desc}, where: {swap: {price: {_gte: "10000000", _lte: "500000000"}}}, limit: 200) {
    buyer {
      address
    }
  }
}
"""

class Dave:

    def __init__(self):
        # setup twitter
        try:
            auth = tweepy.OAuthHandler('', '')
            auth.set_access_token('', '')
            self.api = tweepy.API(auth)
        except Exception as e:
            self.log_error('Failed to setup tweepy', exception=e)
            raise e
        # setup sheet
        try:
            gc = gspread.service_account()
            self.sh = gc.open('HEN NFTs')
        except Exception as e:
            self.log_error('Failed to setup gspread', exception=e)
            raise e
        # setup drive
        try:
            gauth = GoogleAuth()
            gauth.LocalWebserverAuth()
            self.drive = GoogleDrive(gauth)
        except Exception as e:
            self.log_error('Failed to setup drive', exception=e)
            raise e
        
        self.newLastId = None
        self.nfts = None
        self.nftRepresentation = None
    
    def get_nfts(self):
        nfts = self.sh.worksheet('works').get_all_records()
        representation = []
        for i, nft in enumerate(nfts):
            if not nft['representation']:
                continue
            for j in range(nft['representation']):
                representation.append(i)
        self.nfts = nfts
        self.nftRepresentation = representation

    def get_contacts(self):
        return self.sh.worksheet('contacts').col_values(1)
    
    def get_potential_collectors(self):
        return self.sh.worksheet('potentialcollectors').get_all_records()

    def get_collectors_tzids(self):
        return self.sh.worksheet('collectors').col_values(1)[1:]

    def get_potential_collectors_tzids(self):
        return self.sh.worksheet('potentialcollectors').col_values(1)[1:]

    def get_keywords1(self):
        return self.sh.worksheet('keywords1').col_values(1)

    def get_keywords2(self):
        return self.sh.worksheet('keywords2').col_values(1)

    def get_hashtags(self):
        return self.sh.worksheet('hashtags').col_values(1)

    def get_mentions(self):
        return self.sh.worksheet('mentions').col_values(1)

    def get_last(self):
        last = self.sh.worksheet('settings').get_all_records()[0]['lastdrop']
        return int(last)
    
    def get_follow(self):
        follow = self.sh.worksheet('settings').get_all_records()[0]['follow']
        return follow

    def get_likeonfollow(self):
        like = self.sh.worksheet('settings').get_all_records()[0]['likeonfollow']
        return not not like

    def get_likecollectors(self):
        like = self.sh.worksheet('settings').get_all_records()[0]['likecollectors']
        return not not like

    def get_likegeneral(self):
        like = self.sh.worksheet('settings').get_all_records()[0]['likegeneral']
        return not not like
    
    def add_potential_collector(self, row):
        self.sh.worksheet('potentialcollectors').append_row(row)
    
    def update_last(self):
        self.sh.worksheet('settings').update_cell(2, 1, self.newLastId)
    
    def update_collectors(self, collectors):
        worksheet = self.sh.worksheet('collectors')
        worksheet.batch_clear(['2:1000',])
        worksheet.append_rows(collectors)

    def log_error(self, message, exception=None, nft=None, req=None):
        now = datetime.now()
        logList = [now.strftime('%d/%m/%Y %H:%M:%S'), message]
        if exception:
            logList.append(''.join(traceback.format_exception(etype=type(exception), value=exception, tb=exception.__traceback__)).replace('\n',' --- ').replace('\t',' -- '))
        else:
            logList.append('')
        if nft:
            logList.append(nft['title'])
        else:
            logList.append('')
        if req:
            logList.append(req['id'])
        else:
            logList.append('')
        try:
            self.sh.worksheet('errors').append_row(logList)
        except Exception:
            with open(ERRORLOG, 'a') as f:
                f.write(', '.join(logList) + '\n')
    
    def log_run(self, count):
        now = datetime.now()
        logList = [now.strftime('%d/%m/%Y %H:%M:%S'), count]
        self.sh.worksheet('runs').append_row(logList)

    def log_interactions(self, typ, tweets):
        now = time.time()
        row = [now, typ] + tweets
        try:
            self.sh.worksheet('interactions').append_row(row)
        except Exception as e:
            self.log_error('Failed to log interactions', exception=e)

    def fetch_sales(self, address):
        return requests.post('https://api.hicdex.com/v1/graphql', json={'query': SALES_QUERY, 'variables': {"address": address}, 'operationName': 'Sales'})

    def fetch_potential_collectors(self):
        return requests.post('https://api.hicdex.com/v1/graphql', json={'query': COLLECTORS_QUERY, 'variables': {}, 'operationName': 'Sales'})

    def fetch_userdata(self, address):
        return requests.post('https://indexer.tzprofiles.com/v1/graphql', json={'query': 'query MyQuery($address: String!) { tzprofiles_by_pk(account: $address) { valid_claims } }', 'variables': {"address": address}, 'operationName': 'MyQuery'})

    def fetch_userdatas(self, tzs):
        output = {}
        for tz in tzs:
            data = json.loads(self.fetch_userdata(tz).text)
            if data['data']['tzprofiles_by_pk']:
                claims = data['data']['tzprofiles_by_pk']['valid_claims']
                for claim in claims:
                    for thing in claim:
                        if 'TwitterVerification' in thing:
                            thing = json.loads(thing)
                            output[tz] = thing['evidence']['handle']
            if tz not in output:
                output[tz] = ''
        return output
    
    def select_nft(self):
        i = random.choice(self.nftRepresentation)
        return self.nfts[i]
    
    def select_mentions(self, mentions):
        ments = [mentions[0],]
        mentions = mentions[1:]
        number = random.randint(0, len(mentions))
        ments += random.sample(mentions, number)
        return ments

    def download_file(self, fileid, filename):
        gfile = self.drive.CreateFile({'id': fileid})
        gfile.GetContentFile(FILEFOLDER + filename)            
    
    def upload_media(self, nft):
        if not os.path.isfile(FILEFOLDER + nft['filename']):
            try:
                self.download_file(nft['fileid'], nft['filename'])
            except Exception as e:
                self.log_error('Failed to download media', exception=e, nft=nft)
                return False

        fileType = nft['filename'].split('.')[-1]
        
        if fileType == 'gif':
            mediaCategory = "tweet_gif"
        elif fileType == 'jpg' or fileType == 'jpeg' or fileType == 'png':
            mediaCategory = "tweet_image"
        elif fileType == 'mp4':
            mediaCategory = "tweet_video"
        else:
            self.log_error('Media category does not exist', nft=nft)
            return False

        try:
            media = self.api.media_upload(FILEFOLDER + nft['filename'], chunked=True, media_category=mediaCategory)
            nft['twittermediaid'] = media.media_id
            return True
        except Exception as e:
            self.log_error('Failed to upload media', exception=e, nft=nft)
            return False

    def get_drop_requests(self):

        requests = []
        contacts = self.get_contacts()
        keywords1 = self.get_keywords1()
        keywords2 = self.get_keywords2()
        lastId = self.get_last()
        self.newLastId = lastId

        for contact in contacts:
            try:
                tweets = self.api.user_timeline(screen_name=contact, since_id=lastId, include_rts=False, exclude_replies=True)
            except Exception as e:
                self.log_error('Failed to load user timeline of "' + contact + '"', exception=e)
                continue
            for tweet in tweets:

                tweetFormat = False
                tweetKeyword1 = False
                tweetKeyword2 = False
                linkOnly = False
                oneWord = False

                if 'media' not in tweet.entities and not tweet.entities['user_mentions'] and not tweet.entities['urls']:
                    tweetFormat = True
                else:
                    continue

                for kw in keywords1:
                    if kw in tweet.text.lower():
                        tweetKeyword1 = True
                        break
                
                if tweetKeyword1:
                    for kw in keywords2:
                        if kw in tweet.text.lower():
                            tweetKeyword2 = True
                            break
                else:
                    continue
                
                if 'only link' in tweet.text.lower() or 'links only' in tweet.text.lower() or 'link only' in tweet.text.lower():
                    linkOnly = True

                if 'one word' in tweet.text.lower() or 'single word' in tweet.text.lower():
                    oneWord = True
                
                if tweetFormat and tweetKeyword1 and tweetKeyword2:
                    requests.append({'id': tweet.id, 'username': tweet.user.screen_name, 'linkonly': linkOnly, 'oneword': oneWord})
                else:
                    continue
                
                if self.newLastId < tweet.id:
                    self.newLastId = tweet.id
        
        if len(requests) > 10:
            requests = random.sample(requests, 10)
        
        return requests

    def drop_them(self):

        self.get_nfts()
        requests = self.get_drop_requests()
        hashtags = self.get_hashtags()
        mentions = self.get_mentions()

        for req in requests:
            nft = self.select_nft()
            withLink = (random.random() < .2)

            if req['linkonly'] or nft['linkonly'] or withLink:
                text = nft['tweetlink']
                try:
                    self.api.update_status(text, in_reply_to_status_id=req['id'], auto_populate_reply_metadata=True)
                except Exception as e:
                    self.log_error('Failed to tweet link only', exception=e, nft=nft, req=req)
                    continue
            else:
                text = '\n' + nft['title'] + '\n' + nft['nftlink']
                if req['oneword']:
                    text = '\n' + nft['title'].split(' ')[0] + '\n' + nft['nftlink']
                withMentions = (random.random() < .3)
                withHashtags = (random.random() < .85)
                if withHashtags or withMentions:
                    text += '\n' + '~' * random.randint(0, 3) + '\n'
                    if withHashtags:
                        random.shuffle(hashtags)
                        text += '#' + ' #'.join(hashtags) + ' '
                    if withMentions:
                        ments = self.select_mentions(mentions)
                        text += '@' + ' @'.join(ments)

                    if 'twittermediaid' not in nft:
                        try:
                            success = self.upload_media(nft)
                        except Exception as e:
                            self.log_error('Media upload failed with an uncaught error', exception=e, nft=nft, req=req)
                            continue
                        
                        if not success:
                            self.log_error('Replacing media with link...')
                            text += '\n' + nft['tweetlink']
                            self.api.update_status(text, in_reply_to_status_id=req['id'], auto_populate_reply_metadata=True)
                            continue
                    
                    try:
                        self.api.update_status(text, in_reply_to_status_id=req['id'], media_ids=[nft['twittermediaid']], auto_populate_reply_metadata=True)
                    except Exception as e:
                        self.log_error('Failed to tweet with media', exception=e, nft=nft, req=req)
                        continue

            try:
                self.api.create_favorite(req['id'])
            except Exception as e:
                pass
        
        if requests:
            self.update_last()
            self.log_interactions('answer', [req['id'] for req in requests])
        
        self.log_run(len(requests))

    def make_friends(self):
        fans = self.fetch_new_potential_collectors()
        like = self.get_likeonfollow()

        for fan in fans:
            
            if like:
                try:
                    posts = self.api.user_timeline(screen_name=fan[1], include_rts=False, exclude_replies=True)
                except Exception as e:
                    self.log_error('Failed to load user timeline of "' + fan[1] + '"', exception=e)
                    continue
                amount = random.randint(2,3)
                if len(posts) <= amount:
                    tweets = posts
                else:
                    tweets = random.sample(posts, amount)
                for tweet in tweets:
                    wait = random.randint(3,15) + random.random()
                    if random.random() < 0.12:
                        wait += 50
                    time.sleep(wait)
                    try:
                        self.api.create_favorite(tweet.id)
                    except Exception as e:
                        pass
                self.log_interactions('like', [tweet.id for tweet in tweets])

            try:
                self.api.create_friendship(screen_name=fan[1])
            except Exception as e:
                self.log_error('Failed to follow "' + fan[1] + '"', exception=e)
                continue
            fan.append(time.time())
            self.add_potential_collector(fan)
    
    def socialize(self):
        likecollectors = self.get_likecollectors()
        likegeneral = self.get_likegeneral()
        fans = self.get_potential_collectors()
        lastId = self.get_last()

        tweets = []

        if likecollectors:
            for fan in fans:
                if fan['unfollowed'] or bool(random.getrandbits(1)):
                    continue
                try:
                    posts = self.api.user_timeline(screen_name=fan['twitter'], include_rts=False, exclude_replies=True, since_id=lastId)
                except Exception as e:
                    self.log_error('Failed to load user timeline of "' + fan['twitter'] + '"', exception=e)
                    continue
                amount = 1
                if len(posts) <= amount:
                    tweets += posts
                else:
                    tweets += random.sample(posts, amount)
        
        if likegeneral:
            samplesize = random.randint(7,13)
            try:
                posts = self.api.search_tweets('#hicetnunc OR #hicetnunc2000 OR @hicetnunc2000 AND -filter:replies', since_id=lastId, count=200)
                posts = random.sample(posts, samplesize)
            except Exception as e:
                self.log_error('Failed to load posts in likegeneral', exception=e)
                posts = []
            tweets += posts

        for tweet in tweets:
            wait = random.randint(4,15) + random.random()
            if random.random() < 0.11:
                wait += 60
            time.sleep(wait)
            try:
                self.api.create_favorite(tweet.id)
            except Exception as e:
                pass
        self.log_interactions('like', [tweet.id for tweet in tweets])

    def load_collectors(self):
        try:
            data = json.loads(self.fetch_sales(ADDRESS).text)
        except Exception as e:
            self.log_error('Failed to fetch sales', exception=e)
            return
        
        collectors = {}

        for collect in data['data']['hic_et_nunc_trade']:
            tz = collect['buyer']['address']
            date = datetime.strptime(collect['timestamp'].split('T')[0], '%Y-%m-%d')
            if tz in collectors:
                collectors[tz]['count'] += 1
                if date > collectors[tz]['lastacquiry']:
                    collectors[tz]['lastacquiry'] = date
            else:
                collectors[tz] = {
                    'tz': tz,
                    'name': collect['buyer']['name'],
                    'count': 1,
                    'lastacquiry': date
                }

        try:
            twitters = self.fetch_userdatas(collectors.keys())
        except Exception as e:
            self.log_error('Failed to fetch userdata', exception=e)
            return
        rows = []
        for collector in collectors.values():
            r = [collector['tz'], collector['name'], collector['count'], twitters[collector['tz']], collector['lastacquiry']]
            rows.append(r)
        rows = sorted(rows, key=lambda item: item[4], reverse=True)
        for r in rows:
            r[4] = r[4].strftime('%d.%m.%Y')
        self.update_collectors(rows)
    
    def fetch_new_potential_collectors(self):
        follow = self.get_follow()
        collectors = self.get_collectors_tzids()
        potentialcollectors = self.get_potential_collectors_tzids()
        skippers = collectors + potentialcollectors
        newpotentialcollectors = []
        try:
            data = json.loads(self.fetch_potential_collectors().text)
        except Exception as e:
            self.log_error('Failed to fetch new potential collectors', exception=e)
            return []
        for collect in data['data']['hic_et_nunc_trade']:
            tz = collect['buyer']['address']
            if tz in skippers:
                continue
            twitter = self.fetch_userdatas([tz,])
            if tz in twitter and twitter[tz]:
                newpotentialcollectors.append([tz, twitter[tz]])
                skippers.append(tz)
                if len(newpotentialcollectors) == follow:
                    break
        return newpotentialcollectors


# https://auth0.com/blog/how-to-make-a-twitter-bot-in-python-using-tweepy/
# https://github.com/tweepy/tweepy/issues/1267
