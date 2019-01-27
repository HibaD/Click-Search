
# Copyright (C) 2011 by Peter Goodman
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import urllib2
import urlparse
from BeautifulSoup import BeautifulSoup, Tag
from collections import defaultdict
from sets import Set
import re
import sqlite3
from pagerank import *

def attr(elem, attr):
    """An html attribute from an html element. E.g. <a href="">, then
    attr(elem, "href") will get the href or an empty string."""
    try:
        return elem[attr]
    except:
        return ""

WORD_SEPARATORS = re.compile(r'\s|\n|\r|\t|[^a-zA-Z0-9\-_]')

class crawler(object):
    """Represents 'Googlebot'. Populates a database by crawling and indexing
    a subset of the Internet.

    This crawler keeps track of font sizes and makes it simpler to manage word
    ids and document ids."""

    def __init__(self, db_conn, url_file):
        """Initialize the crawler with a connection to the database to populate
        and with the file containing the list of seed URLs to begin indexing."""
        self._url_queue = [ ]
        self._doc_id_cache = { }
        self._word_id_cache = { }
        self.db_conn = db_conn

        #added data structures for enhanced performance
        self._document_index = { }	
        self._lexicon = { }
        self._inverted_index = defaultdict(set)
        self.c = db_conn.cursor()	

        #linktolink a helper db table for page rank
        #wordtolink stores the page rank scores
        #lexicon stores the words and their ids
        #document_index stores the urls and their ids
        #inverted_index stores the doc ids and relevant word id that correspond to these doc ids
        self.c.execute("CREATE TABLE IF NOT EXISTS linktolink (fromLink integer, toLink integer, PRIMARY KEY (fromLink, toLink))")
        self.c.execute("CREATE TABLE IF NOT EXISTS wordtolink (word text, url text, score real DEFAULT 0, PRIMARY KEY (word, url))")
        self.c.execute("CREATE TABLE IF NOT EXISTS lexicon (word_id INTEGER PRIMARY KEY, word text NOT NULL UNIQUE)")
        self.c.execute("CREATE TABLE IF NOT EXISTS document_index (doc_id INTEGER PRIMARY KEY, url text NOT NULL UNIQUE, title text, description text)")
        self.c.execute("CREATE TABLE IF NOT EXISTS inverted_index (word_id INTEGER, doc_id INTEGER, PRIMARY KEY (word_id, doc_id))")

        self.db_conn.commit()

        # functions to call when entering and exiting specific tags
        self._enter = defaultdict(lambda *a, **ka: self._visit_ignore)
        self._exit = defaultdict(lambda *a, **ka: self._visit_ignore)

        # add a link to our graph, and indexing info to the related page
        self._enter['a'] = self._visit_a

        # record the currently indexed document's title an increase
        # the font size
        def visit_title(*args, **kargs):
            self._visit_title(*args, **kargs)
            self._increase_font_factor(7)(*args, **kargs)

        # increase the font size when we enter these tags
        self._enter['b'] = self._increase_font_factor(2)
        self._enter['strong'] = self._increase_font_factor(2)
        self._enter['i'] = self._increase_font_factor(1)
        self._enter['em'] = self._increase_font_factor(1)
        self._enter['h1'] = self._increase_font_factor(7)
        self._enter['h2'] = self._increase_font_factor(6)
        self._enter['h3'] = self._increase_font_factor(5)
        self._enter['h4'] = self._increase_font_factor(4)
        self._enter['h5'] = self._increase_font_factor(3)
        self._enter['title'] = visit_title
        
        # decrease the font size when we exit these tags
        self._exit['b'] = self._increase_font_factor(-2)
        self._exit['strong'] = self._increase_font_factor(-2)
        self._exit['i'] = self._increase_font_factor(-1)
        self._exit['em'] = self._increase_font_factor(-1)
        self._exit['h1'] = self._increase_font_factor(-7)
        self._exit['h2'] = self._increase_font_factor(-6)
        self._exit['h3'] = self._increase_font_factor(-5)
        self._exit['h4'] = self._increase_font_factor(-4)
        self._exit['h5'] = self._increase_font_factor(-3)
        self._exit['title'] = self._increase_font_factor(-7)

        # never go in and parse these tags
        self._ignored_tags = set([
                'meta', 'script', 'link', 'meta', 'embed', 'iframe', 'frame', 
                'noscript', 'object', 'svg', 'canvas', 'applet', 'frameset', 
                'textarea', 'style', 'area', 'map', 'base', 'basefont', 'param',
        ])

        # set of words to ignore
        self._ignored_words = set([
                '', 'the', 'of', 'at', 'on', 'in', 'is', 'it',
                'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                'u', 'v', 'w', 'x', 'y', 'z', 'and', 'or',
        ])

        self._mock_next_doc_id = 1
        self._mock_next_word_id = 1

        # keep track of some info about the page we are currently parsing
        self._curr_depth = 0
        self._curr_url = ""
        self._curr_doc_id = 0
        self._font_size = 0
        self._curr_words = None

        # get all urls into the queue
        try:
            with open(url_file, 'r') as f:
                for line in f:
                    self._url_queue.append((self._fix_url(line.strip(), ""), 0))
        except IOError:
            pass

    def _mock_insert_document(self, url):
        """A function that pretends to insert a url into a document db table 
        and then returns that newly inserted document's id."""
    
        #put into db table
        self.c.execute("INSERT OR IGNORE INTO document_index (url) VALUES (?)",(url,))
        self.db_conn.commit()
        self.c.execute('SELECT * FROM document_index where url = (?)',(url,))
        for row in self.c.fetchall():
            ret_id = row[0]
        return ret_id


    def _mock_insert_word(self, word):
        """A function that pretends to inster a word into the lexicon db table 
        and then returns that newly inserted word's id."""
        self.c.execute("INSERT OR IGNORE INTO lexicon (word) VALUES (?)", (word,))
        self.db_conn.commit()

        self.c.execute('SELECT * FROM lexicon where word = (?)', (word,))
        for row in self.c.fetchall():
            ret_id = row[0]

        return ret_id

    def word_id(self, word):
        """Get the word id of some specific word."""
        #	1) add the word to the lexicon, if that fails, then the
        #          word is in the lexicon 
        #    	2) query the lexicon for the id assigned to this word, 
        #          store it in the word id cache, and return the id.
        if word not in self._lexicon.values():
            word_id = self._mock_insert_word(word)
            self._lexicon[word_id] = word
            self._word_id_cache[word] = word_id
        else:
            word_id = self._word_id_cache[word]

        return word_id

    def document_id(self, url):
        """Get the document id for some url."""

        # 	Just like word id cache, but for documents. if the document
        #       doesn't exist in the db then only insert the url and leave
        #       the rest to their defaults.

        if url not in self._document_index.values():
            document_id = self._mock_insert_document(url)
            self._document_index[document_id] = url
            self._doc_id_cache[url] = document_id
        else:
            document_id = self._doc_id_cache[url]

        return document_id

    def _fix_url(self, curr_url, rel):
        """Given a url and either something relative to that url or another url,
        get a properly parsed url."""

        rel_l = rel.lower()
        if rel_l.startswith("http://") or rel_l.startswith("https://"):
            curr_url, rel = rel, ""

        # compute the new url based on import 
        curr_url = urlparse.urldefrag(curr_url)[0]
        parsed_url = urlparse.urlparse(curr_url)
        return urlparse.urljoin(parsed_url.geturl(), rel)

    def add_link(self, from_doc_id, to_doc_id):
        """Add a link into the database, or increase the number of links between
        two pages in the database."""
        set_of_links = [(from_doc_id,to_doc_id)]
        self.c.executemany("INSERT OR IGNORE INTO linktolink VALUES (?,?)",set_of_links)
        self.db_conn.commit()

    def _visit_title(self, elem):
        """Called when visiting the <title> tag."""
        title_text = self._text_of(elem).strip()
	# update document title for document id self._curr_doc_id
        self.c.execute("SELECT url FROM document_index WHERE url = (?)", (self._curr_url,))
        rows =  self.c.fetchall()
        for row in rows:
                self.c.execute("UPDATE document_index set title = (?) where url = (?)",(title_text,row[0]))
                self.db_conn.commit()
        

    def _visit_a(self, elem):
        """Called when visiting <a> tags."""
        dest_url = self._fix_url(self._curr_url, attr(elem,"href"))

        # add the just found URL to the url queue
        self._url_queue.append((dest_url, self._curr_depth))

        # add a link entry into the database from the current document to the
        # other document
        self.add_link(self._curr_doc_id, self.document_id(dest_url))


    def _add_words_to_document(self):
        # 	knowing self._curr_doc_id and the list of all words and their
        #       font sizes (in self._curr_words), add all the words into the
        #       database for this document	
        
	#word is the word id and font size,  we use word[0] to access just the word id

        for word in self._curr_words:
            # this method is called for every url so find set if it exists otherwise it is created because of defaultdict
            self.c.execute("INSERT OR IGNORE INTO inverted_index (word_id, doc_id) VALUES (?, ?)", (word[0], self._curr_doc_id))
            self.db_conn.commit()

            wordset = self._inverted_index[word[0]]			
            #only add url if it does not exist in inverted index 
            if self._curr_doc_id not in wordset:
                self._inverted_index[word[0]].add(self._curr_doc_id)

    def _increase_font_factor(self, factor):
        """Increade/decrease the current font size."""
        def increase_it(elem):
            self._font_size += factor
        return increase_it

    def _visit_ignore(self, elem):
        """Ignore visiting this type of tag"""
        pass

    def _add_text(self, elem):
        """Add some text to the document. This records word ids and word font sizes
        into the self._curr_words list for later processing."""
        words = WORD_SEPARATORS.split(elem.string.lower())
        for word in words:
            word = word.strip()
            if word in self._ignored_words:
                continue
            self._curr_words.append((self.word_id(word), self._font_size))

    def _text_of(self, elem):
        """Get the text inside some element without any tags."""
        if isinstance(elem, Tag):
            text = [ ]
            for sub_elem in elem:
                text.append(self._text_of(sub_elem))

            return " ".join(text)
        else:
            return elem.string

    def get_inverted_index(self):
        return self._inverted_index

    def get_resolved_inverted_index(self):
        _res_inv_ind = defaultdict(set)

        for word_id in self._inverted_index:
            doc_set = Set([])
            for doc in self._inverted_index[word_id]:
                #find url matching doc id from document_index db
                self.c.execute("SELECT url from document_index where doc_id = (?)", (doc,))
                doc_string = self.c.fetchone()[0]
                #add it to new wordset 
                doc_set.add(doc_string)
            #find the word which maps to word_id using the lexicon db
            self.c.execute("SELECT word from lexicon where word_id = (?)", (word_id,))
            word = self.c.fetchone()[0]
            _res_inv_ind[word] = doc_set
        return _res_inv_ind

    def _index_document(self, soup):
        """Traverse the document in depth-first order and call functions when entering
        and leaving tags. When we come accross some text, add it into the index. This
        handles ignoring tags that we have no business looking at."""
        class DummyTag(object):
            next = False
            name = ''

        class NextTag(object):
            def __init__(self, obj):
                self.next = obj

        tag = soup.html
        stack = [DummyTag(), soup.html]

        while tag and tag.next:
            tag = tag.next

            # html tag
            if isinstance(tag, Tag):

                if tag.parent != stack[-1]:
                    self._exit[stack[-1].name.lower()](stack[-1])
                    stack.pop()

                tag_name = tag.name.lower()


                # ignore this tag and everything in it
                if tag_name in self._ignored_tags:
                    if tag.nextSibling:
                        tag = NextTag(tag.nextSibling)
                    else:
                        self._exit[stack[-1].name.lower()](stack[-1])
                        stack.pop()
                        tag = NextTag(tag.parent.nextSibling)

                    continue

                # enter the tag
                self._enter[tag_name](tag)
                stack.append(tag)

            # text (text, cdata, comments, etc.)
            else:
                self._add_text(tag)

    def crawl(self, depth=2, timeout=3):
        """Crawl the web!"""
        seen = set()

        while len(self._url_queue):

            url, depth_ = self._url_queue.pop()

            # skip this url; it's too deep
            if depth_ > depth:
                continue

            doc_id = self.document_id(url)

            # we've already seen this document
            if doc_id in seen:
                continue

            seen.add(doc_id) # mark this document as haven't been visited

            socket = None
            try:
                socket = urllib2.urlopen(url, timeout=timeout)
                soup = BeautifulSoup(socket.read())

                self._curr_depth = depth_ + 1
                self._curr_url = url
                self._curr_doc_id = doc_id
                self._font_size = 0
                self._curr_words = [ ]
                self._index_document(soup)
                self._add_words_to_document()

            except Exception as e:
                print e
                pass
            finally:
                if socket:
                    socket.close()

        resv_inv_index = self.get_resolved_inverted_index()	
        #put in db word to link, default rank 0
        for word in resv_inv_index:
            for word_url in resv_inv_index[word]:
                intodb = (word,word_url)
                self.c.execute("INSERT OR IGNORE INTO wordtolink (word, url) VALUES (?,?)", intodb)

        #CALL PAGE RANK	
        links_list = []
        self.c.execute('SELECT * FROM linktolink')	
        for row in self.c.fetchall():
            links_list.append((row[0],row[1]))

        #get ranks for pages	
        page_rank_list = page_rank(links_list)

        #populate page rank scores into DB
        for item in page_rank_list:
            doc_id = item
            score = page_rank_list[item]
            self.c.execute("SELECT url from document_index where doc_id = (?)", (doc_id,))
            for row in self.c.fetchall():
                url = row[0]
                self.c.execute("UPDATE wordtolink set score = (?) where url = (?)",(score,url))
                self.db_conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect('csc326.db')
    bot = crawler(conn, "urls.txt")
    bot.crawl(depth=1)
