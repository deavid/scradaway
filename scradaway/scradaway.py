import os
import os.path
from optparse import OptionParser
import random
import threading
import time
import re
import json
import traceback
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# External dependencies:
import psycopg2
from lxml import etree
from lxml.html.clean import Cleaner
from lxml.cssselect import CSSSelector
import lxml.html
import requests

# Scradaway internal deps:
from utils import filedir, one, XMLStruct, XMLStructConfig

class XMLDatabase(XMLStruct):
    host = "127.0.0.1"
    port = 5432
    database = "scradaway"
    username = "postgres"
    password = "postgres"

class XMLProperty(XMLStruct):
    name = "name"
    css = XMLStructConfig(xmltype=str, fntype=lambda i: CSSSelector(i), default = None )

class XMLSite(XMLStruct):
    name = "mywebsite.com"
    start_url = "http://www.mywebsite.com"
    include = XMLStructConfig(xmltype=str, fntype=lambda i: [ re.compile(x.strip()) for x in i.split("\n") ] )
    exclude = XMLStructConfig(xmltype=str, fntype=lambda i: [ re.compile(x.strip()) for x in i.split("\n") ] )
    json_download = XMLStructConfig(xmltype=list, xmlsubtype=XMLProperty)

    
cleaner = Cleaner(page_structure=False, links=True, safe_attrs_only=True)


class Scradaway(object):
    
    def __init__(self, options):
        self.verbose = options.verbose
        self.conn = None
        configfile = options.configfile or filedir("../config.xml")
        self.loadconfig(configfile)
        self.setupDatabase()
        self.config_afterdb()
        
    
    def loadconfig(self, filename):
        if self.verbose: 
            print("Loading config from", filename)
        parser = etree.XMLParser(
                        ns_clean=True,
                        encoding="UTF-8",
                        remove_blank_text=True,
                        )
        self.tree = etree.parse(filename, parser)
        self.root = self.tree.getroot()
        self.xmldatabase = XMLDatabase(one(self.root.xpath("database")))
        if self.verbose: print("Database:", self.xmldatabase)
        self.sites = []
        self.threads = []
        
        for n,site in enumerate(one(self.root.xpath("sites"))):
            if site.tag != "site": continue
            xmlsite= XMLSite(site)
            self.sites.append(xmlsite)
            xmlsite.known_urls = {}
            xmlsite.urls_to_download = set([])
            xmlsite.urls_to_download.add(xmlsite.start_url)
            if self.verbose: print("Site %d:" % (n+1), xmlsite)
            
    def config_afterdb(self):
        cur = self.conn.cursor()
        for site in self.sites:
            try:
                cur.execute(
                """INSERT INTO downloaded_data (site_name, url, pending_download)
                    VALUES (%s, %s, true) ON CONFLICT DO NOTHING;""",
                (site.name, site.start_url))
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                print("Error inserting to download url %r: %r" % (link, e))

        
    def setupDatabase(self, on_thread=False):
        if self.conn and not on_thread: raise ValueError("already set up db")
        conn = psycopg2.connect(dbname=self.xmldatabase.database,
                        user=self.xmldatabase.username,
                        password =self.xmldatabase.password,
                        host=self.xmldatabase.host,
                        port=self.xmldatabase.port
                        )
        if not on_thread: self.conn = conn
        return conn
        
    def add_link(self, site, link):
        if link in site.known_urls: return False
        for r in site.include:
            if not r.search(link): return False
        for r in site.exclude:
            if r.search(link): return False
        return True
        
    def start_download_all(self):
        for i in range(4):
            for site in self.sites:
                thread1 = threading.Thread(target=self.do_work, kwargs={"site": site})
                self.threads.append(thread1)
                thread1.start()
            time.sleep(1)
            if len(self.threads) >= 8: break

            
        for thread in self.threads:
            thread.join()
        
    def do_work(self, site): 
        thread_dbconn = self.setupDatabase(on_thread=True)
        cur = thread_dbconn.cursor()
        while True:
            url = None
            for i in range(5):
                try:
                    cur.execute(
                        """SELECT url FROM downloaded_data 
                            WHERE site_name = %s AND pending_download AND random() < %s
                            FOR UPDATE SKIP LOCKED LIMIT 1;""",
                        (site.name,2**(-4+i)))
                    for pgurl, in cur:
                        url = pgurl
                        break
                except Exception as e:
                    print("Error trying to get new url's to download:", e)
                    thread_dbconn.rollback()
                if url is not None: break
                time.sleep(1)
            if url is None: break
            response = requests.get(url)
            content_response = response.content

            try:
                html = lxml.html.fromstring(content_response)
            except Exception:
                continue
            try:
                cur.execute(
                """UPDATE downloaded_data SET pending_download = FALSE WHERE site_name = %s AND url = %s;""",
                (site.name, url))
            except Exception as e:
                print("Error trying to update url %r as downloaded: %r" % (url, e))
            
            html.make_links_absolute(url)
            new_links = 0
            link_list = []
            process_json = True
            canonical_url = None
            for (element, attribute, link, pos) in html.iterlinks():
                if link:
                    if element.tag == "link":
                        rel = element.get("rel")
                        if rel == "stylesheet": continue
                        if rel == "canonical":
                            if link != url:
                                link_list.append(link)
                                canonical_url = link
                                process_json = False
                                continue
                        continue
                    hash_char = link.find("#")
                    if hash_char >= 0: link = link[:hash_char]
                    if self.add_link(site,link):
                        link_list.append(link)
                        new_links += 1
            if process_json:
                json_obj = {}
                for prop in site.json_download:
                    if prop.css:
                        for e in prop.css(html):
                            text1 = e.text_content().strip()
                            text2 = lxml.etree.tostring(e)
                            json_obj[prop.name] = str(text1)
            else:
                json_obj = None
       
            try:
                cur.execute("""SELECT url FROM downloaded_data 
                    WHERE site_name = %s AND url = %s FOR UPDATE NOWAIT;"""
                    , (site.name, url))
                json_text = json.dumps(json_obj) if json_obj else None
                cur.execute(
                    """UPDATE downloaded_data 
                        SET pending_download = FALSE, canonical_url = %s 
                        , timewhen = now(), jsondata = %s
                        WHERE site_name = %s AND url = %s;""",
                    (canonical_url, json_text, site.name, url))
                if json_obj:
                    print(site.name, repr(json_obj)[:64])
                thread_dbconn.commit()
            except Exception as e:
                thread_dbconn.rollback()
                print("Error updating downloaded data for %r: %r" % (url, e))
            if link_list:
                try:
                    args_str = b','.join(cur.mogrify("(%s,%s,true)", (site.name, link) ) for link in link_list)
                    cur.execute(b"""INSERT INTO downloaded_data (site_name, url, pending_download)
                                VALUES %s ON CONFLICT DO NOTHING;""" % args_str)             
                    thread_dbconn.commit()
                except Exception as e:
                    thread_dbconn.rollback()
                    print("Error inserting to download url %r: %r" % (link, e))
                    traceback.print_exc()
            if False:
                for link in link_list:
                    
                    try:
                        cur.execute(
                        """INSERT INTO downloaded_data (site_name, url, pending_download)
                            VALUES (%s, %s, true) ON CONFLICT DO NOTHING;""",
                        (site.name, link))
                        thread_dbconn.commit()
                    except Exception as e:
                        thread_dbconn.rollback()
                        print("Error inserting to download url %r: %r" % (link, e))
                
            #print("Ended work %d (+%d)" % (len(site.urls_to_download),new_links), url);
                    
            if len(self.threads) < 16:
                thread1 = threading.Thread(target=self.do_work,kwargs={'site':site})
                self.threads.append(thread1)
                thread1.start()
                time.sleep(0.5)
                

        



def main():
    parser = OptionParser()
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    parser.add_option("-c", "--config",
                      metavar="PATH", dest="configfile", default=None,
                      help="PATH to configuration file. By default config.xml in the app folder")

    (options, args) = parser.parse_args()
    print("Scradaway init.")
    myscradaway = Scradaway(options)
    myscradaway.start_download_all()
    

if __name__ == "__main__":
    main()
