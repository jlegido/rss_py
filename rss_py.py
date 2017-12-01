#!/usr/bin/python
'''
    Copyright 2013 Javier Legido javi@legido.com

    rss_py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    rss_py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
'''
import urllib,urllib2
from BeautifulSoup import BeautifulSoup
from sys import exit,argv
from datetime import datetime,date
import logging
import commands
import urllib2
import re
import time
from threading import Thread
from os.path import basename
import urlparse
import settings

logger = logging.getLogger('rss_py')
handler = logging.FileHandler(settings.path_log_main)
formatter = logging.Formatter( '%(asctime)s - %(lineno)s: %(levelname)s %(message)s' )
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

from requests import get
from traceback import format_exc

import feedparser

class ItemEncodingError(Exception):

    def __init__(self, value):
        self.value = value
        logger.error(value)

    def __str__(self):
        return repr(self.value)

class th_channel_compose_mobi(Thread):

    def __init__(self, channel):
        Thread.__init__(self)
        self.channel = channel

    def run(self):
        self.channel.compose_mobi()

class th_article_download(Thread):

    def __init__(self, article):
        Thread.__init__(self)
        self.article = article

    def run(self):
        self.article.download()

class channel(object):

    # NEW: media is now a dict taken from settings
    def __init__(self,media):
        self.url = media['url']
        self.title = media['title']
        self.nicetitle = self.title.replace(' ','_')
        self.articles = []
        self.content = ''
        self.element = ''
        self.summary = ''
        self.threads = []
        self.media = media
        self.encoding = ''
        self.date_parsing_callback = media['date_parsing_callback']
        # New
        self.items = []

    def start(self):
        '''Downloads channel index, split articles, download them and composes html'''
        logger.info('START '+self.title+' - '+self.url)
        self._download_channel_index()
        self._split_channels_into_articles()
        if self.download_articles():
            self.compose_html()
        logger.info('FINISH '+self.title+' - '+self.url)

    def _fix_url(self, url):
        ''' Fix malformed url link in La Haine '''
        # http://www.lahaine.org/index.php?blog=4&amp;p=74003
        return url.replace('amp;','') 

    def _split_channels_into_articles(self):
        #Iterates Items and if the date is from today, creates artivles objects
        for item in self.items:
            if self.is_from_today(item['published']):
                # BUG: La Haine malformed link:
                # http://www.lahaine.org/index.php?blog=4&amp;p=74003
                if self.nicetitle == 'La_Haine_lo_mas_nuevo':
                    item['links'][0]['href'] = self._fix_url(item['links'][0]['href'])
                try:
                    self.articles.append(self._from_item_create_article(
                                         item, self.media))
                except ItemEncodingError:
                    pass  
        logger.info('RSS ' + self.url + ' parsed')
        logger.info(str(len(self.articles))+' today\'s articles header got')

    def _from_item_create_article(self, item, media):
        ''' Creates an article object from an item. If there's missing fields -> None '''
        d = dict()
        # TODO: improve it. Error in La Haine:
        # UnicodeEncodeError: 'latin-1' codec can't encode character u'\u201c' ...
        try:
            d['date'] = item['published'].encode(self.encoding)
            d['title'] = item['title'].encode(self.encoding)
            d['link'] = item['links'][0]['href'].encode(self.encoding)
            d['channel_url'] = self.url
            # I assume that author is the only field potentially missing 
            if hasattr(item, 'author'):
                d['author'] = item['author'].encode(self.encoding)
            else:
                d['author'] = None
        #except UnicodeEncodeError:
        except UnicodeEncodeError as e:
            raise ItemEncodingError('Not able to parse item. Error: ' + str(e))
        else:
            return article(d, media)

    def _download_channel_index(self):
        #Downloads channel index and returns items
        # http://pythonhosted.org/feedparser/
        fp = feedparser.parse(self.url)
        self.items = fp['items']
        try:
            self.encoding = str(fp['encoding'])
        except KeyError as e:
            logger.error("%s looks down" %(self.url))

    def is_from_today(self,string):
        date_string = getattr(self,self.date_parsing_callback)(string)
        try:
            t_article = time.strptime(date_string,"%d %b %Y")
        except Exception,e:
            logger.error('Unable to determine if the article is from today. Date: '+\
                         string+'. Callback function tried: '+self.date_parsing_callback)
            return False

        dt_article = datetime(t_article[0],t_article[1],t_article[2])
        today = datetime.today()
        dt_today = datetime(today.year,today.month,today.day)
        if not (dt_today > dt_article):
            return True
        return False

    def _date_parsing_callback_1(self,string):
        ''' Returns a string with date month year in this format: 21 Aug 2013 '''
        # Thu, 22 Aug 2013 11:53:42 +0000
        l = string.split(' ')
        return "%s %s %s" % (l[1],l[2],l[3])

    def _date_parsing_callback_2(self, string):
        ''' Returns a string with date month year in this format: 21 Aug 2013 '''
        # dimecres, 14 ago 2013, 13:39:14 GMT
        # dissabte, 21 des 2013, 17:43:47 GMT
        l = string.split(' ')
        # TODO: temporary until we complete 12 months and get them in catalonian
        try:
            return "%s %s %s" % (l[1],settings.months[l[2]],l[3][:-1])
        except KeyError:
            logger.warning('Not able to parse date ' + string)
            return "Unknown"

    def download_articles(self):
        # NEW: threads
        for article in self.articles:
            t = th_article_download(article)
            t.start()
            self.threads.append(t)

        for t in self.threads:
            t.join()

        logger.info('All threads stopped')

        for article in self.articles:
            if article.content <> 'NO' and article.content <> '':
                nicename = re.sub('<[^<]+?>', '', article.title)
                self.summary += '<a href="#'+article.anchor+'"><h1>'+nicename+'</h1></a>'
                self.content += article.content
            else:
                self.articles.remove(article)
        logger.info(str(len(self.articles))+' today\'s article(s) downloaded and parsed')
        if len(self.articles) > 0:
            self.content = self.summary + self.content
            return True
        return False

    def compose_html(self):
        path_html_today = settings.path_html_today.replace('TITLE',self.nicetitle)
        html = html_replace(settings.html_template,\
                           (self.encoding,self.title,self.content))
        try:
            ptr = open(path_html_today, 'w')
            ptr.write(html)
            ptr.close()
        except Exception, e:
             logger.error('Unable to open/write file "'+path_html_today+\
                         '". Exception: '+str(e))

    def compose_mobi(self):
        path_mobi_today = settings.path_mobi_today.replace('TITLE',self.nicetitle)
        path_html_today = settings.path_html_today.replace('TITLE',self.nicetitle)

        logger.info('Creating .mobi file for '+self.nicetitle)
        result = commands.getstatusoutput(settings.path_calibre+'ebook-convert '+\
                path_html_today+' '+path_mobi_today)
        if result[0] == 0:
            logger.info('Created file '+path_mobi_today)
        else:
            logger.error('Unable to create file "'+path_mobi_today+\
                    '". Command output: '+result[1],'main')

class article(object):

    def __init__(self, dict_fields, media):
        self.date = '<p>' + dict_fields['date'] + '</p>'
        self.channel_url = dict_fields['channel_url']
        # Needed for La Haine
        self.link = self.build_link(dict_fields['link'])
        self.author = '<p>'+str(dict_fields['author'])+'</p>'
        self.anchor = self.link.replace(':','').replace('/','').replace('.','')
        self.title = '<a name="'+self.anchor+'">'+dict_fields['title']+'</a>'
        self.content = 'NO'
        self.raw_content = ''
        self.url_print = ''
        self.tag_id = 0
        self.media = media
        self.encoding = '' 

    def build_link(self,string):
        if 'http' in string:
            return string
        else:
            return self.channel_url.split('spip')[0] + string

    def download(self):
        '''Download article and parses it, if failure stores it to disk for debugging'''
        r = get(self.link)
        self.encoding = r.encoding
        self.raw_content = r.text.encode(self.encoding)
        self.parse()

        if self.content == 'NO':
            f = open(settings.path_articles_not_parsed+\
                    self.url_to_nice_string(self.link),'w')
            try:
                f.write(self.raw_content.encode(self.encoding))
            except Exception as e:
                logger.warning('Not able to write '+self.link+'. Error: '+str(e))
            f.close()

    def parse(self):
        # NEW: strict, just parse if both 2 tags are present
        if self.tag_id < len(self.media['tag']):
            if self.raw_content.find(self.media['tag'][self.tag_id]) <> -1\
            and self.raw_content.find(self.media['tag'][self.tag_id + 1]) <> -1:
                self.content = self.raw_content.split(self.media['tag'][self.tag_id])[1].\
                            split(self.media['tag'][self.tag_id + 1])[0]
                logger.debug('Parsed successfully article '+self.link)

                # Loop to get <img>
                soup = BeautifulSoup(''.join(self.content))
                imgData = ''

                imgTags = soup.findAll('img')
                for imgTag in imgTags:
                    try:
                        imgUrl = imgTag['src']
                    except Exception, e:
                        logger.warning('Unable to find src html tag. '+str(e))
                        break

                    # download only the proper image files
                    if imgUrl.lower().endswith('.jpeg') or \
                        imgUrl.lower().endswith('.jpg') or \
                        imgUrl.lower().endswith('.gif') or \
                        imgUrl.lower().endswith('.png') or \
                        imgUrl.lower().endswith('.bmp'):
                        try:
                            imgData = urllib2.urlopen(imgUrl.encode(self.encoding)).read()
                        except Exception, e:
                            try:
                                img_url = self.link.split('/')[0]+'//'+\
                                        self.link.split('/')[2]+'/'+imgUrl
                                imgData = urllib2.urlopen(img_url.encode(self.encoding))\
                                          .read()
                            except Exception, e:
                                logger.warning('Unable to download image. Tried '+imgUrl+\
                                        ' and '+img_url+'. '+str(e))
                                break

                        if len(imgData) >= settings.minFileSize:
                            try:
                                fileName = basename(urlparse.urlsplit(imgUrl)[2])
                                output = open(settings.path_img+fileName, 'wb')
                                output.write(imgData)
                                output.close()

                                # Append modified <img> tag to the html code
                                self.content += '<img src="'+settings.path_img_relative+\
                                                str(basename(\
                                                imgUrl.encode(self.encoding)))+'"/><br>'
                            except Exception, e:
                                logger.warning('Unable to write to disk image. '+str(e))

                self.compose_article()
                return True
            else:
                self.tag_id += 2
                self.parse()
        else:
            logger.warning('Unable to parse '+self.link+'. Tags tried: '+\
                            str(self.media['tag']))
            return False

    def compose_article(self):
        self.content = settings.styles['title'][0] + self.title +\
                       settings.styles['title'][1] + self.date + self.author+\
                       settings.styles['article'][0] + self.content +\
                       settings.html_anchor_index + settings.styles['article'][1]

    def url_to_nice_string(self,string):
        return string.replace('http://','').replace('=','_').replace('/','_')

def html_replace(html_template,html_blocks):
    for html_block in html_blocks:
        html_template = html_template.replace('HTML_BLOCK',html_block,1)
    return html_template

def main():
    logger.info('START of the script '+str(argv[0]))
    channels = []

    for media in settings.media:
        ch = channel(media)
        ch.start()
        channels.append(ch)

    if settings.create_mobi:
        threads_channel_compose_mobi = []
        for ch in channels:
            if len(ch.articles) > 0:
                tch = th_channel_compose_mobi(ch)
                tch.start()
                threads_channel_compose_mobi.append(tch)

        for t in threads_channel_compose_mobi:
            t.join()

    logger.info('FINISH of the script '+str(argv[0]))

if __name__ == "__main__":
    main()
