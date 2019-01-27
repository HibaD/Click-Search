#----For Bottle-----
import bottle
import re
import operator
from bottle import route, run, template, request, get, post, static_file, redirect, error
from collections import OrderedDict
#----For Google------
import httplib2
import urllib
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from oauth2client import tools
#----For Beaker------
from beaker.middleware import SessionMiddleware
#----For DB---------
import sqlite3
#----Spell Checker-----
from autocorrect import spell
#----Search Suggestions----
import nltk
nltk.download('wordnet')
from nltk.corpus import wordnet


#----connect to database-----
conn = sqlite3.connect('csc326.db')
c = conn.cursor()

#---Global variables-----
urllist = [] 		#for results
searchresult = []	#for pagination
page = -1		#results page number, -1 means no search made
wordtosearch = ''	#the word entered by user
autob = False		#a (potential) correct spelling of word exists
autow = ''		#a (potential) correct spelling of word
synonyms = []		#other search suggestions based on word

#----Session set up-----
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './data',
    'session.auto': True
}

app = SessionMiddleware(bottle.app(), session_opts)


#----Account things-------

#login, redirects to Google login
@bottle.route('/login','GET')
def login():	
	flow = flow_from_clientsecrets("client_secrets.json",
		scope=['https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/plus.me'],
		redirect_uri="http://localhost:8080/redirect")
	uri = flow.step1_get_authorize_url()
	bottle.redirect(str(uri))

#for logged in users
@bottle.route('/redirect')
def redirect_page():
	code = request.query.get('code','')
	flow = OAuth2WebServerFlow( client_id='758035687348-to1dchnhv9a240qc8vmpm1449pvb6g61.apps.googleusercontent.com',
		client_secret='6x5AIDpkH28PMV_LySZlwmsY',
		scope=['https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/plus.me'],
		redirect_uri='http://localhost:8080/redirect')
	credentials = flow.step2_exchange(code)
	token = credentials.id_token['sub']

	http = httplib2.Http()
	http = credentials.authorize(http)
	# Get user info
	users_service = build('oauth2', 'v2', http=http)
	user_document = users_service.userinfo().get().execute()
	
	#session stuff	
	session = request.environ.get('beaker.session')
	session['email'] = user_document['email']
	session.save()
	return bottle.redirect('/')

#logout
@route('/logout')
def logout():
	session = bottle.request.environ.get('beaker.session')
	session.delete()
	bottle.redirect('/')

#---Visiting unknown pages-----

#error handling
@error(404)
def error404(error):
	global page
	session = request.environ.get('beaker.session')
	if 'email' in session:
		email = session['email']	
	else:
		email = 'Guest'
	page = -1 	#set page num to not searched
	return (template('error', email=email), template('styles'))

#----User driven results------

#getting links and info for the given word
def pull_word_results(wordtosearch):
	urllist[:] = []
	searchresult[:] = []
	c.execute("SELECT wordtolink.url, document_index.title, wordtolink.score from wordtolink natural join document_index where wordtolink.word = (?) order by score DESC", (wordtosearch,))
	for link in c.fetchall():
		urllist.append(link)
	for link in urllist[page:(page+5)]:
		searchresult.append((link[0], link[1]))


#get existing synonyms for the word
def pull_synonyms(wordtosearch):
	global synonyms
	synonyms[:] = []
	synonymslist = []
	for syn in wordnet.synsets(wordtosearch): 
    		for l in syn.lemmas():
			synonymslist.append(l.name())
	myset = set(synonymslist) #unique values
	synonymslist = list(myset)
	if wordtosearch in synonymslist: synonymslist.remove(wordtosearch)
	count = 0
	for word in synonymslist:
		c.execute("SELECT EXISTS(select 1 from wordtolink where word = (?))", (word,))
		for link in c.fetchall():
			if link[0] == 1: 
				synonyms.append(word)
				count += 1
		if count >= 3: break				

#main landing page
@bottle.route('/','GET')
def home():
	global urllist
	global searchresult
	global page
	global wordtosearch
	global autob
	global autow
	#set up session if logged in	
	session = request.environ.get('beaker.session')
	email = 'Guest'
	if 'email' in session:
		loggedIn = True
		email = session['email']
	else:
		loggedIn = False
		
	
	#user clicks submit button
	if request.GET.keywords:		
		#capture word
		new = request.GET.keywords
		wordtosearch = new.split(' ',1)[0]
		autow = spell(wordtosearch)
		#spell check	
		if autow != wordtosearch:
			c.execute("SELECT EXISTS(select 1 from wordtolink where word = (?))", (autow,))
			for link in c.fetchall():
				if link[0] == 1:
					autob = True
				else:
					autob = False
		else:
			autob = False
		page = 0 # start at first page
		#call function to get results
		pull_word_results(wordtosearch)
		#synonyms
		pull_synonyms(wordtosearch)
		bottle.redirect('/')


		#user clicks submit button
	if request.GET.autovalue:
		autob = False
		new = request.GET.autovalue
		wordtosearch = new.split(' ',1)[0] 
		autow = wordtosearch
		page = 0 # start at first page
		#call function to get results
		pull_word_results(wordtosearch)
		#synonyms
		pull_synonyms(wordtosearch)
		bottle.redirect('/')


	#add previous and next results buttons
	#if page > 0 and len(urllist) > page:
	if request.GET.Prev:
		page = page - 5
		searchresult[:] = []
		for link in urllist[page:(page+5)]:
			searchresult.append((link[0], link[1]))
		bottle.redirect('/')
	#if len(urllist) > (page+5):
	if request.GET.Next:
		page = page + 5
		searchresult[:] = []
		for link in urllist[page:(page+5)]:
			searchresult.append((link[0], link[1]))
		bottle.redirect('/')
		
	
	#user clicks login button	
	if request.GET.Login:
		bottle.redirect('/login')
	#user clicks logout button	
	if request.GET.Logout:
		bottle.redirect('/logout')
	
	#views
	if loggedIn is True: #sending parameters to be processed by front-end pages
		output = (template('main', wordresult=searchresult, suggestions=synonyms, email=email, page=page, resnum=len(urllist), word=autow, auto=autob, wordsearched=wordtosearch), template('styles'))
	else:
		output = (template('main-anon', wordresult=searchresult, suggestions=synonyms, email=email, page=page, resnum=len(urllist), word=autow, auto=autob, wordsearched=wordtosearch), template('styles'))
	return output
	

bottle.run(app=app, host='0.0.0.0', port=8080)
