#!/usr/bin/python

import os
from datetime import date
import time
import urlparse
from os.path import basename

# Bytes
minFileSize = 3000
#path = os.path.dirname(os.path.realpath(__file__))+'/'
path = '/mnt/rss/'
path_mobi = path + 'mobi/'
path_log = path + 'logs/'
path_log_main = path_log + 'main.log'
path_html = path + 'html/'
path_img = path_html + 'img/'
path_img_relative = 'img/'
path_articles_not_parsed = path + 'articles_not_parsed/'
path_html_today = path_html+'TITLE'+'.html'
path_mobi_today = path_mobi+'TITLE'+'.mobi'
path_calibre = '/usr/local/calibre/'

months = {
          'gen':'Jan',
          'feb':'Feb',
          'mar':'Mar',
          'jul':'Jul',
          'ago':'Aug',
          'set':'Sep',
          'oct':'Oct',
          'nov':'Nov',
          'des':'Dec',
         }
default_encoding = 'UTF-8'

# TODO: improve link up  <a href="../rss">Channel Index</a><br>
html_template = '\
                <html>\
                <head>\
                <meta http-equiv="Content-Type" content="text/html; charset=HTML_BLOCK"\
                 />\
                <title>HTML_BLOCK</title>\
                </head>\
                <body>\
                <a href="../rss">Channel Index</a><br>\
                <a name="index"></a>\
                HTML_BLOCK\
                </body>\
                </html>\
                '
styles = {
        'article':('<h2>','</h2>'),
        'title':('<h1>','</h1>'),
}
html_anchor_index = '<br><a href="#index">Index</a>'
url_timeout = 20
create_mobi = False

media = (
        {'title':'Indymedia Barcelona',
            'url':'http://barcelona.indymedia.org/newswire.rss',
            'tag':('class="summary">','<tr><td colspan="2" class="license">',),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
        {'title' : 'Arainfo',
            'url' : 'http://arainfo.org/feed/',
            'tag' : ('</script><p>',
             '<!-- AddThis Share Buttons below via filter on the_content -->',
                     '<p class="fckJus">',
             '<!-- AddThis Share Buttons below via filter on the_content -->',
                     '</script><div>',
             '<!-- AddThis Share Buttons below via filter on the_content -->',
                   ),
            'date_parsing_callback' : '_date_parsing_callback_1',
        },
        {'title':'CNT',
            'url':'http://www.cnt.es/en/rss.xml',
            'tag':('<div class="content">','<div id="navigation"'),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
       {'title':'La Haine lo mas nuevo',
            'url':'http://www.lahaine.org/index.php?blog=1&tempskin=_rss2',
            'tag':('</span></strong></p>','<p><em>',
                   '<div class="space_dash"></div><p><strong>','<p><em>',
                   '<div class="content_full"><div class="space_dash"></div>',
                   '</p></div>'),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
        {'title':'A las barricadas',
              'url':'http://www.alasbarricadas.org/noticias/rss.xml',
            'tag':('<div class="content">','<ul class="links inline">'),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
        {'title':'Kaos en la red',
            'url':'http://kaosenlared.net/feed',
            'tag':('<div class="entry">',
                   '<div class="addtoany_share_save_container',),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
        {'title':'International Middle East Media Center',
            'url':'http://imemc.org/feed/',
            'tag':('class="img-responsive alignleft" />',
                   '<a class="synved-social-button',),
            'date_parsing_callback':'_date_parsing_callback_1',
        },
        {'title' : 'Directa',
            'url' : 'https://directa.cat/rss.xml',
            'tag' : ('<div class="field-body">',
                     '<p style="text-align:center">', ),
            'date_parsing_callback' : '_date_parsing_callback_1',
        },
)
