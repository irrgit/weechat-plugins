import weechat
import re
import MySQLdb

weechat.register("irccloudsafelist", "IrccloudSafelist", "1.3", "GPL3", "Safelist for IRCCLOUD users connecting to your server.", "", "")

db_host = "localhost"
db_user = "YOURDBUSER"
db_pass = "YOURMYSQLPASS"
db_name = "ircuiddb"
db_table = "ircuids"

#connect to mysql and create database
def create_db_table():	
	dbconn = MySQLdb.connect(db_host,db_user,db_pass)
	cursor = dbconn.cursor()
	sql = "CREATE DATABASE IF NOT EXISTS ircuiddb"
	cursor.execute(sql)	
	dbconn.commit()
	cursor.close()
	dbconn.close()

	dbconn = MySQLdb.connect(db_host,db_user,db_pass,db_name)
	cursor = dbconn.cursor()
	sql = "CREATE TABLE IF NOT EXISTS `ircuids` (`requester` varchar(32) NOT NULL, `uid` varchar(15) NOT NULL,  PRIMARY KEY (`uid`));"
	cursor.execute(sql)
	dbconn.commit()
	cursor.close()
	dbconn.close()

create_db_table()

uids = []
pending = {}

irccloud = [
'highgate.irccloud.com', 	
'192.184.9.108',
'ealing.irccloud.com', 	
'192.184.9.110',
'charlton.irccloud.com ',	
'192.184.9.112',
'brockwell.irccloud.com', 	
'192.184.10.118',
'tooting.irccloud.com', 	
'192.184.10.9',
'richmond.irccloud.com', 	
'170.178.187.131',
'hathersage.irccloud.com', 	
'192.184.8.73',
'stonehaven.irccloud.com', 	
'192.184.8.103'
]


def connecting_cb(data,signal,signal_data):
	if "Client connecting" in signal_data:
		#choose a buffer for display purposes, usually a channel.
		buffer = weechat.info_get("irc_buffer","mynetwork,#Opers")
		notice = str(signal_data)
		hostname = re.findall(r": .*\((.*)\)",notice)[0]
		ident,ip = hostname.split('@')
		if((ident.startswith("sid") or ident.startswith("uid")) and ip in irccloud):
			dbconn = MySQLdb.connect(db_host,db_user,db_pass,db_name)
			cursor = dbconn.cursor()
			sql = "SELECT `uid` from `ircuids` WHERE `uid` LIKE '%s'" % ident
			cursor.execute(sql)

			#Below you can decide what to do with a specific ID if theyre on the list or not.
			#Usually you can ban all ones that are not on the list , or direct them to a #channel where they can get added.

			if not cursor.rowcount:				
				weechat.prnt(buffer,"NOT IN DB, ISSUE AKILL -> %s@*" % ident)
				#weechat.command("","/quote OS AKILL ADD +30d %s*@ BANNED")
			else:
				#Here the user joining is in our list so we can either display a message or do nothing.
				weechat.prnt(buffer,"USER IS IN DB -> UID : %s " % ident)
	else:
		pass
	return weechat.WEECHAT_RC_OK



def notice_cb(data,signal,signal_data):

	global pending
	nick = weechat.info_get("irc_nick_from_host", signal_data)
	notice = str(signal_data)
	#check if chanserv sent us a message	
	if nick == "ChanServ": 
		#check if the nick chanserv replies about is in our pending list
		#the way access level is checked on the server this is running on is
		#to issue a /cs why nick on a specific channel and then it responds
		#whether the person has access on that specific channel
		#Not sure if its a module that comes with UnrealIRCd or needs to be installed
		checked_nick = re.findall(r" \:(.*) \(",str(signal_data))[0]
		if (str(checked_nick) in pending and "ka access level" in notice):
			datalist = pending.pop(checked_nick)
			uid = datalist[0]
			action = datalist[1]
			dbconn = MySQLdb.connect(db_host,db_user,db_pass,db_name)
			cursor = dbconn.cursor()
			if str(action) == "add":				
				sql = "INSERT IGNORE INTO `%s`(`requester`,`uid`) VALUES ('%s','%s')" % (db_table,str(checked_nick),str(uid))
				cursor.execute(sql)
				dbconn.commit()
				cursor.close()
				dbconn.close()
			if str(action) == "del":
				sql = "DELETE FROM `%s` WHERE `uid` = '%s' " % (db_table,str(uid))
				cursor.execute(sql)
				dbconn.commit()
				cursor.close()
				dbconn.close()			

	return weechat.WEECHAT_RC_OK


def parse_cmd(data,signal,signal_data):
	global pending

	notice = str(signal_data)
	channel = re.findall(r"PRIVMSG (.*) :",notice)[0]
	nick = weechat.info_get("irc_nick_from_host", signal_data)
	
	if "!safelist " in notice:		
		action = "add"
		uid = re.findall(r":!.* (.*)",notice)[0].lower()
		if uid.startswith("uid") or uid.startswith("sid"):
			request = (uid,action)
			pending[nick] = request
			weechat.command("","/msg chanserv why #opers %s"%nick)


	elif "!remove " in notice:
		action = "del"
		uid = re.findall(r":!.* (.*)",notice)[0].lower()
		if uid.startswith("uid") or uid.startswith("sid"):
			request = (uid,action)
			pending[nick] = request
			weechat.command("","/msg chanserv why #opers %s"%nick)

	return weechat.WEECHAT_RC_OK

weechat.hook_signal("*,irc_in_NOTICE","connecting_cb","")
weechat.hook_signal("*,irc_in_NOTICE","notice_cb","")
weechat.hook_signal("*,irc_in_PRIVMSG","parse_cmd","")





