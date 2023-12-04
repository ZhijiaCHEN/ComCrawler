import re
from sys import prefix
from tkinter.messagebox import NO
from numpy.core.shape_base import block
from selenium import webdriver
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, InvalidSessionIdException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from os.path import isfile, join
from os import listdir
from postgres import Postgres
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from lxml import etree, html
from io import StringIO
from style import StyleDict, parser, structured_blocks, MyParser
from utility import *
from datetime import datetime
from fasttext_classification import gram_text_process
import time, json, os, random, sys, pickle, requests, psycopg2, fasttext
import pandas as pd
import numpy as np
from collections import deque
from requests import HTTPError
from univeral_tree import StructTree, ELEMENT_BLACK_LIST
from typing import List
import psutil

DATA_PATH = os.environ['CRAWLER_DATA_PATH']
HTML_PARSER = etree.HTMLParser(remove_blank_text=True, remove_comments=True,remove_pis=True, compact=False, huge_tree=True)
class BaseTask:
    """
    Base class for performing certain task.
    """
    def __init__(self, debug = False):
        self.DEBUG = debug
    #     self.worker = None
    #     self.workerArgs = None
    #     self.workerKwargs = None
    
    # def set_task_worker(self, workerFun, *args, **kwargs):
    #     self.worker = workerFun
    #     self.workerArgs = args
    #     self.workerKwargs = kwargs

    def request_task(self):
        raise NotImplementedError()

    def prepare_task(self):
        raise NotImplementedError()
        
    def perform_task(self):
        raise NotImplementedError()
        # self.worker(*self.workerArgs, **self.workerKwargs)

    def complete_task(self):
        raise NotImplementedError()

    def run_once(self):
        if (self.request_task()):
            if self.prepare_task():
                self.perform_task()
            self.complete_task()

    def end_task(self):
        raise NotImplementedError()

    def run(self):
        while 1:
            try:
                if self.request_task():
                    if self.prepare_task():
                        self.perform_task()
                    self.complete_task()
                else:
                    break
            except Exception as e:
                self.error(repr(e))

    def log(self, message):
        print(message)
    
    def debug(self, message):
        if self.DEBUG:
            self.log('Debug:\n{}'.format(message))

    def info(self, message):
        self.log('Info:\n{}'.format(message))
    
    def warn(self, message):
        self.log('Warn:\n{}'.format(message))
    
    def error(self, message):
        self.log('Error:\n{}'.format(message))

class SeleniumTask(BaseTask):
    def __init__(self, host:str='http://127.0.0.1:4444/wd/hub', windowWidth=1920, windowHeight=1080, **kwargs):
        super().__init__(**kwargs)
        self.url = None
        self.currentPagePath = None
        self.seleniumHost = host
        self.driver = None
        self.windowWidth = windowWidth
        self.windowHeight = windowHeight
        self.open_selenium()
    
    def open_selenium(self):
        self.close_selenium()

        if self.seleniumHost:
            self.driver = webdriver.Remote(command_executor='http://{}:4444/wd/hub'.format(self.seleniumHost), desired_capabilities=DesiredCapabilities.CHROME)
        else:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--headless')
            self.driver = webdriver.Chrome(chrome_options=options)

        self.driver.maximize_window()
        self.driverProcessID = self.driver.service.process.pid
        # self.driver.set_window_size(self.windowWidth, self.windowHeight)
    
    def close_selenium(self):
        if self.driver is not None:
            try:
                self.driver.quit()
                time.sleep(5)
            except Exception:
                pass
            self.force_kill()
            self.driver = None
            self.driverProcessID = None

    def open_page(self, url=None, markNewPage=True, openInNewTab=True, closeOldTabs=True, timeout=30):
        if self.url is None and url is None: return
        if openInNewTab:
            self.open_tab()

        self.driver.delete_all_cookies()
        self.driver.set_page_load_timeout(timeout)
        try:
            if url:
                self.driver.get(url)
            else:
                self.driver.get(self.url)
        except WebDriverException as e:
            pass

        if closeOldTabs:
            for i in range(0, len(self.driver.window_handles)-1):
                self.close_tab(0)

        if markNewPage:
            self.currentPagePath = self.driver.execute_script('return window.location.pathname;')

    def is_new_page(self):
        return self.currentPagePath != self.driver.execute_script('return window.location.pathname;')

    def click(self, elm, waitTime = 3):
        try:
            elm.click()
        except WebDriverException:
            self.driver.execute_script("arguments[0].click()", elm)
        time.sleep(waitTime)

    def save_screenshot(self, path: str = '/tmp/screenshot.png') -> None:
        # Ref: https://stackoverflow.com/a/52572919/
        original_size = self.driver.get_window_size()
        required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
        self.driver.set_window_size(original_size['width'], required_height)
        self.scroll_to_bottom()
        time.sleep(0.2)
        # driver.save_screenshot(path)  # has scrollbar
        try:
            self.driver.find_element_by_tag_name('html').screenshot(path)  # avoids scrollbar
        except WebDriverException:
            fullpage_screenshot(self.driver, path)
        #self.driver.set_window_size(original_size['width'], original_size['height'])
        #self.driver.maximize_window()
    
    def page_screenshot(self):
        try:
            return self.driver.find_element_by_tag_name('html').screenshot_as_png  # avoids scrollbar
        except WebDriverException:
            return None

    def open_tab(self):
        try:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.execute_script('window.open()')
            self.driver.switch_to.window(self.driver.window_handles[-1])
        except WebDriverException as e:
            self.error(repr(e))

    def close_tab(self, tabIdx = -1):
        wh = self.driver.window_handles[tabIdx]
        try:
            self.driver.switch_to.window(wh)
            self.driver.close()
            if len(self.driver.window_handles) > 0:
                self.driver.switch_to.window(self.driver.window_handles[0])
        except WebDriverException as e:
            self.error(repr(e))

    def scroll_to_bottom(self, simple = False, scrollInterval = 1):
        try:
            if simple:
                self.driver.execute_script("""window.scrollTo({
                                            top: document.body.scrollHeight,
                                            behavior: 'smooth'
                                            });""")
                time.sleep(scrollInterval)
            else:
                scrollCnt = 0
                oldScrollY = 0
                newScrollY = 0
                while(scrollCnt < 3 or (newScrollY != oldScrollY and scrollCnt < 20)):
                    scrollCnt += 1
                    oldScrollY = newScrollY
                    self.driver.execute_script("""window.scrollBy({
                                            top: window.innerHeight,
                                            behavior: 'smooth'
                                            });""")
                    time.sleep(scrollInterval)
                    newScrollY = self.driver.execute_script('return window.scrollY;')
                    if newScrollY == oldScrollY:
                        self.driver.execute_script("""window.scrollTo({
                                            top: document.body.scrollHeight,
                                            behavior: 'smooth'
                                            });""")
                        time.sleep(2 * scrollInterval)
                        newScrollY = self.driver.execute_script('return window.scrollY;')
        except WebDriverException as e:
            pass


        self.driver.execute_script('window.scrollTo(0, 0);')
    
    def prepare_task(self):
        self.open_page()
        return True

    def complete_task(self):
        pass

    def run_once(self):
        if (self.request_task()):
            try:
                self.prepare_task()
                self.perform_task()
            except (WebDriverException, InvalidSessionIdException) as e:
                self.error(repr(e))
                self.status = -1
                self.open_selenium()
            self.complete_task()

    def force_kill(self):
        parent = psutil.Process(os.getpid())
        # top down
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except:
                pass

        wildChrome = [p for p in psutil.process_iter() if 'chrome' in p.name().lower() and len(p.parents()) == 0]
        for chrome in wildChrome:
            for child in chrome.children(recursive=True):
                try:
                    child.kill()
                except:
                    pass
            try:
                chrome.kill()
            except:
                pass


class SeleniumDBTask(SeleniumTask, Postgres):
    def __init__(self, seleniumHost:str = 'http://127.0.0.1:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', **kwargs):
        SeleniumTask.__init__(self, host=seleniumHost, **kwargs)
        Postgres.__init__(self, host=databaseHost, user=user, password=password, database=database)

class CollectXPath(SeleniumDBTask):
    def __init__(self, seleniumHost: str='http://127.0.0.1:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.wid = None
        self.btnXpath = None
 
    def request_task(self):
        requestSQL = 'select tmp.wid, host, tmp.url from ((select distinct on(wid) wid, url, language from article join count_results on article.aid = count_results.aid where has_btn) union (select distinct on (wid) wid, url, language from webpage where has_btn)) tmp join website on tmp.wid = website.wid where tmp.wid not in (select wid from button_xpath) limit 1'
        self.cursor.execute(requestSQL)
        row = self.cursor.fetchone()
        if row is None:
            return False

        self.wid = row['wid']
        self.url = row['url']
        print('start working on wid: {}'.format(self.wid))
        return True
        

    def perform_task(self):
        # collect xpath
        self.xpath = None
        while self.xpath is None:
            self.xpath = input('Comment button xpath:')
            try:
                print('-'*100)
                for btn in self.driver.find_elements_by_xpath(self.xpath):
                    print(btn.get_attribute('outerHTML'))
                if len(input('Keep the xpath?')) > 0:
                    self.xpath = None
            except WebDriverException as e:
                print(repr(e))
        return True

    def complete_task(self):
        completeSQL = 'insert into button_xpath(wid, xpath) values ( %(wid)s, %(xpath)s);'
        self.cursor.execute(completeSQL, {'wid': self.wid, 'xpath': self.xpath})
    
    def end_task(self):
        endSQL = 'select tmp.wid, host, tmp.url from ((select distinct on(wid) wid, url, language from article join count_results on article.aid = count_results.aid where has_btn) union (select distinct on (wid) wid, url, language from webpage where has_btn)) tmp join website on tmp.wid = website.wid where tmp.wid not in (select wid from button_xpath) limit 1'
        self.cursor.execute(endSQL)
        row = self.cursor.fetchone()
        if row is None:
            return False

class ButtonCrawlerManual(SeleniumDBTask):
    def __init__(self, seleniumHost: str='http://127.0.0.1:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', output = '.', N=20, **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.N = N
        self.output = output
        requestSQL = 'select tmp.wid, host, tmp.url, tmp.language, xpath from ((select distinct on(wid) wid, url, language from article join count_results on article.aid = count_results.aid where has_btn) union (select distinct on (wid) wid, url, language from webpage where has_btn)) tmp join website on tmp.wid = website.wid join button_xpath on tmp.wid = button_xpath.wid order by wid;'
        self.cursor.execute(requestSQL)
        self.webpageRow = self.cursor.fetchall()
        if os.path.exists(os.path.join(output, 'existWid.pickle')):
            with open(os.path.join(output, 'existWid.pickle'), 'rb') as f:
                self.existWid = pickle.load(f)
        else:
            self.existWid = set()

    def request_task(self):
        for row in self.webpageRow:
            if row['wid'] not in self.existWid:
                self.wid = row['wid']
                self.url = row['url']
                self.language = row['language']
                print('start working on wid: {}'.format(self.wid))
                return True
        return False

    def perform_task(self):
        # collect negative buttons
        cnt = 1
        while cnt <= self.N:
            input('Open a new page to collect negative buttons.')
            allBtn = self.driver.find_elements_by_xpath("//button|//a")
            allBtn = random.sample(allBtn, len(allBtn))
            if len(allBtn) == 0:
                print('No button exist in the url: {}'.format(self.url))
            for btn in allBtn:
                try:
                    print('-'*100)
                    print(btn.get_attribute('outerHTML'))
                    if input('Is this negative').lower() not in ['y', '1', 'yes']:
                        fileName = 'negative-{}-{}-{}.html'.format(self.wid, self.language, cnt)
                        with open(join(self.output, fileName), 'w', encoding='utf-8') as f:
                            f.write(btn.get_attribute('outerHTML'))
                            print('{}/{} collected.'.format(cnt, self.N))
                            cnt += 1
                            if cnt > self.N:
                                break
                except WebDriverException as e:
                    print(repr(e))

        # collect positive buttons
        xpath = None
        btnNum = 0
        while xpath is None:
            xpath = input('Comment button xpath:')
            try:
                print('-'*100)
                
                for btn in self.driver.find_elements_by_xpath(xpath):
                    print(btn.get_attribute('outerHTML'))
                if len(input('Keep the xpath?')) > 0:
                    xpath = None
                else:
                    btnNum = int(input('input expected number of buttons per page'))
            except WebDriverException as e:
                print(repr(e))
        
        cnt = 1
        while cnt <= self.N:
            input('Open target pages...')
            for h in self.driver.window_handles:
                try:
                    self.driver.switch_to.window(h)
                    btnFound = self.driver.find_elements_by_xpath(xpath)

                    for btn in btnFound:
                        if len(btnFound) == btnNum:
                            keep = ''
                        else:
                            print('-'*100)
                            print(btn.get_attribute('outerHTML'))
                            keep = input('Keep the button?')
                        if len(keep) == 0:
                            fileName = 'positive-{}-{}-{}.html'.format(self.wid, self.language, cnt)
                            with open(join(self.output, fileName), 'w', encoding='utf-8') as f:
                                f.write(btn.get_attribute('outerHTML'))
                                print('{}/{} collected.'.format(cnt, self.N))
                                cnt += 1
                                if cnt > self.N:
                                    return True
                except WebDriverException as e:
                    print(repr(e))
        return True

    def complete_task(self):
        self.existWid.add(self.wid)
        print('{} website collected.'.format(len(self.existWid)))
        with open(os.path.join(self.output, 'existWid.pickle'), 'wb') as f:
            pickle.dump(self.existWid, f)
    
    def end_task(self):
        return len(self.existWid) >= len(self.webpageRow)

class ButtonCrawlerXpath(SeleniumDBTask):
    def __init__(self, seleniumHost: str='http://127.0.0.1:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', output = '.', N=20, **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.N = N
        self.output = output
        requestSQL = 'select tmp.wid, host, tmp.url, tmp.language, xpath from ((select distinct on(wid) wid, url, language from article join count_results on article.aid = count_results.aid where has_btn) union (select distinct on (wid) wid, url, language from webpage where has_btn)) tmp join website on tmp.wid = website.wid join button_xpath on tmp.wid = button_xpath.wid order by wid;'
        self.cursor.execute(requestSQL)
        self.seeds = self.cursor.fetchall()
        if os.path.exists(os.path.join(output, 'existWid.pickle')):
            with open(os.path.join(output, 'existWid.pickle'), 'rb') as f:
                self.existWid = pickle.load(f)
        else:
            self.existWid = set()
        self.success = False

    def request_task(self):
        self.success = False
        for row in self.seeds:
            if row['wid'] not in self.existWid:
                self.wid = row['wid']
                self.url = row['url']
                self.language = row['language']
                self.host = row['host']
                self.xpath = row['xpath']
                print('start working on wid: {}'.format(self.wid))
                return True
        return False

    def perform_task(self):
        # collect positive buttons
        # try:
        #     btn = self.driver.find_element_by_xpath(self.xpath)
        # except Exception as e:
        #     xpath = input('Failed to locate comment button with xpath: {} in wid: {}. Input new xpath if needed.'.format(self.xpath, self.wid))
        #     if len(xa)

        # collect negative buttons
        cnt = 1
        def collect_negative():
            nonlocal cnt
            allBtn = self.driver.find_elements_by_xpath("//button|//a")
            allBtn = random.sample(allBtn, len(allBtn))
            if len(allBtn) == 0:
                print('No button exist in the url: {}'.format(self.url))
            for btn in allBtn:
                try:
                    btnHTML = btn.get_attribute('outerHTML').lower()
                    if 'omment' not in btnHTML and 'reply' not in btnHTML and 'replies' not in btnHTML and 'response' not in btnHTML and 'react' not in btnHTML:
                        fileName = 'negative-{}-{}-{}.html'.format(self.wid, self.language, cnt)
                        with open(join(self.output, fileName), 'w', encoding='utf-8') as f:
                            f.write(btn.get_attribute('outerHTML'))
                            print('{}/{} negative buttons collected.'.format(cnt, self.N))
                            cnt += 1
                            if cnt > self.N:
                                break
                except WebDriverException as e:
                    print(repr(e))
        collect_negative()
        while cnt < self.N:
            input('Open new page to collect negative button.')
            collect_negative()
        import time
        cnt = 1
        q = deque([self.url])
        visited = set([self.url])
        start = time.time()
        while q and (time.time() - start) < 600:
            qLen = len(q)
            for batch in range(qLen//self.N + 1):
                for i in range(batch*self.N, min(qLen, (batch + 1)*self.N)):
                    url = q.popleft()
                    self.open_page(url=url, closeOldTabs=False, timeout=10, markNewPage=False)
                
                for h in self.driver.window_handles[1:]:
                    self.driver.switch_to.window(h)
                    try:
                        for btn in self.driver.find_elements_by_xpath(self.xpath):
                            fileName = 'positive-{}-{}-{}.html'.format(self.wid, self.language, cnt)
                            with open(join(self.output, fileName), 'w', encoding='utf-8') as f:
                                f.write(btn.get_attribute('outerHTML'))
                                print('{}/{} positive buttons collected.'.format(cnt, self.N))
                                cnt += 1
                                if cnt > self.N:
                                    self.success = True
                                    return True

                        for a in self.driver.find_elements_by_xpath("//a"):
                            try:
                                newUrl = a.get_attribute('href').split('?')[0].split('#')[0]
                                newUri = urlparse(newUrl)
                                if newUri.hostname != self.host or newUrl in visited:
                                    continue
                                q.append(newUrl)
                                visited.add(newUrl)
                            except WebDriverException:
                                pass
                    except WebDriverException:
                        pass
                    
                while len(self.driver.window_handles) > 1:
                    try:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.driver.close()
                    except WebDriverException as e:
                        print(repr(e))
        while not self.success:
            input('manual discovering')
            for h in self.driver.window_handles[1:]:
                self.driver.switch_to.window(h)
                try:
                    for btn in self.driver.find_elements_by_xpath(self.xpath):
                        fileName = 'positive-{}-{}-{}.html'.format(self.wid, self.language, cnt)
                        with open(join(self.output, fileName), 'w', encoding='utf-8') as f:
                            f.write(btn.get_attribute('outerHTML'))
                            print('{}/{} positive buttons collected.'.format(cnt, self.N))
                            cnt += 1
                            if cnt > self.N:
                                self.success = True
                                return True
                except WebDriverException:
                        pass
        return False

    def complete_task(self):
        if self.success:
            self.existWid.add(self.wid)
            print('{} website collected.'.format(len(self.existWid)))
            with open(os.path.join(self.output, 'existWid.pickle'), 'wb') as f:
                pickle.dump(self.existWid, f)
    
    def end_task(self):
        for row in self.seeds:
            if row['wid'] not in self.existWid:
                return False
        return True

class GetLanguageRegion(SeleniumDBTask):
    def __init__(self, seleniumHost:str = 'http://127.0.0.1:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.url = 'https://news.google.com/'

    def request_task(self):
        return True

    def perform_task(self):
        self.cursor.execute('select name from language_region')
        languageRegion = set([x[0] for x in self.cursor.fetchall()])
        languageRegionNum = 82
        while len(languageRegion) < languageRegionNum:
            try:
                languageEntry = self.driver.find_element_by_xpath('//div[@jsaction="click:Vl1baf;"]')
                self.driver.execute_script('arguments[0].click()', languageEntry)
            except WebDriverException as e:
                self.error(repr(e))
                break

            try:
                element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//ul[@class="sAloQd"]')))
            except WebDriverException as e:
                self.error('Lanugage panel loading failed. {}'.format(repr(e)))
                break

            languagetreeElms = self.driver.find_elements_by_xpath('//li[@class="LxUgAe"]')
            if len(languagetreeElms) != languageRegionNum:
                self.warn('Unexpected number of available language and region, {} other than {} found'.format(len(languagetreeElms), languageRegionNum))

            for lanIdx, lanSelected in enumerate(languagetreeElms):
                targetLan  = lanSelected.get_attribute('data-n-cess').split(' | ')[0]
                if targetLan in languageRegion:
                    continue
                else:
                    if lanIdx > 0:
                        try:
                            #select the language
                            radio = lanSelected.find_element_by_xpath('.//input[@type="radio"]')
                            radio.click()
                            #confirm
                            oldBody = self.driver.execute_script('return document.body')
                            confirmBtn = self.driver.find_element_by_xpath('//div[@jsname="dxgHv"]')
                            confirmBtn.click()
                            time.sleep(2)
                            WebDriverWait(self.driver, 3).until(EC.staleness_of(oldBody))
                        except WebDriverException as e:
                            self.error('Page dose not reload after selecting a new language and region.')
                            break
                    urlArgs = self.driver.current_url.split('?')[1].split('&')
                    hl = urlArgs[0].split('=')[1]
                    gl = urlArgs[1].split('=')[1]
                    ceid = urlArgs[2].split('=')[1]
                    self.cursor.execute('insert into language_region(name, hl, gl, ceid) values (%(name)s, %(hl)s, %(gl)s, %(ceid)s);', {'name': targetLan, 'hl':hl, 'gl': gl, 'ceid': ceid})
                    languageRegion.add(targetLan)
                    break

    def complete_task(self):
        pass

    def end_task(self):
        endSQL = 'select count(*) from language_region'
        self.cursor.execute(endSQL)
        return self.cursor.fetchone()[0] == 82

class ArticleCrawler(BaseTask, Postgres):
    def __init__(self, host: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', target:List[str] = None, interval:int = 10, **kwargs):
        BaseTask.__init__(self)
        Postgres.__init__(self, host=host, user=user, password=password, database=database, **kwargs)
        self.cursor.execute('select language_region, hl, gl, ceid from language_region')
        self.language_region = pd.DataFrame(self.cursor.fetchall(), columns = ["language_region", "hl", "gl", "ceid"])
        self.topic = ["WORLD", "NATION", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH"]
        self.targetCeid = target
        self.interval = interval

        self.urlSet = set()
        self.urlQueue = deque([])
        self.cacheSize = 1000

    def request_task(self):
        return True
    
    def prepare_task(self):
        return True
    
    def complete_task(self):
        pass
    
    def end_task(self):
        return True

    def perform_task(self):
        self.info('Start working on new round.')
        headers = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",\
                   "Accept-Encoding":"gzip, deflate, br",\
                   "Cache-Control": "max-age=0",\
                   "Connection":"close",\
                   "Referer":"https://www.google.com/",\
                   "TE":"Trailers",\
                   "Upgrade-Insecure-Requests":"1",\
                   "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"}
        for row in self.language_region.iloc:
            if self.targetCeid and row['ceid'] not in self.targetCeid:
                continue
            language_region = row.language_region.split(' (')
            language = language_region[0]
            region = language_region[1][:-1]
            for topic in self.topic:
                self.info(f'Crawling {topic} from {region} in {language}.')
                # self.cursor.execute('select count(*) from article where topic = %(topic)s and language = %(language)s and region = %(region)s', {'topic':topic.lower(), 'language': language, 'region': region})
                # itemCnt = self.cursor.fetchall()[0][0]
                # if itemCnt >= 20:
                #     continue
                feed = "https://news.google.com/news/rss/headlines/section/topic/{topic}?hl={hl}&gl={gl}&ceid={ceid}".format(topic=topic, hl=row.hl, gl=row.gl, ceid=row.ceid)
                response = requests.get(feed, headers = headers)
                if response.status_code != 200:
                    self.error("Failed to get rss feed: {}".format(response.text))
                    continue
                topicSoup = BeautifulSoup(response.content, 'lxml', from_encoding="utf-8")
                
                for item in topicSoup.select('rss channel item'):
                    try:
                        title = item.title.contents[0].split(' - ')[0]
                        pubTime = item.pubdate.contents[0]
                        link = item.link
                        if link.contens is None:
                            link = link.next
                        else:
                            link = link.contents[0]
                        response = requests.get(link, headers = headers, timeout = 5, allow_redirects = False)
                        
                        if response.status_code != 301:
                            self.error("Google does not redirect the link {}: {}".format(link, response.text))
                            continue
                        url = response.headers['Location']
                        host = urlparse(url).netloc
                        self.cursor.execute('select wid from website where host = %(host)s limit 1', {'host':host})
                        wid = self.cursor.fetchall()
                        if len(wid) == 0:
                            self.cursor.execute('insert into website (wid, host) values ((select coalesce(max(wid), 0)+1 from website), %(host)s) returning wid;', {'host': host})
                            wid = self.cursor.fetchall()[0][0]
                        else:
                            wid = wid[0][0]
                        try:
                            self.cursor.execute('select aid from article where url = %(url)s;', {'url': url})
                            aid = self.cursor.fetchall()
                            if len(aid) == 0:
                                self.cursor.execute('insert into article (wid, title, url, topic, language, region, pub_time) values (%(wid)s, %(title)s, %(url)s, %(topic)s, %(language)s, %(region)s, %(pub_time)s);', {'wid':wid, 'title': title, 'url':url, 'topic':topic.lower(), 'language': language, 'region': region, 'pub_time': pubTime})
                                self.info(f'Imported {topic} {language} {region} {url}')
                                # itemCnt += 1
                                # print('language: {}, region: {}, topic: {}, count: {}'.format(language, region, topic, itemCnt))
                            else:
                                self.debug(f'Skiping {topic} {language} {region} {url}')
                        except psycopg2.IntegrityError as e:
                            # self.error(repr(e))
                            continue
                        # if itemCnt == 20:
                        #     break
                        time.sleep(1)
                    except Exception as e:
                        self.error(repr(e))
        self.info(f'Finished this round. I am going to sleep for {self.interval} minutes.')
        time.sleep(60 * self.interval)
        
class CommentCrawler(SeleniumDBTask):
    def __init__(self, seleniumHost:str = 'http://localhost:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', take_screenshot=False, max_visit = 3, **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.buttonClf = fasttext.load_model(join('fasttext', 'button', '3gram.model'))
        self.commentClf = fasttext.load_model(join('fasttext', 'comment', '3gram.model'))
        self.MAX_VISIT = max_visit
        self.init_var()
        self.driver.maximize_window()
        self.takeScreenshot = take_screenshot

    def init_var(self):
        self.articleRow = None
        self.aid = None
        self.exitStage = None
        self.numClick = None
        self.numBtnCandidate = None
        self.numStruct = None
        self.numCmtCandidate = None
        self.numNoStruct = None # number of button candidates that do not produce any structured region 
        self.status = None
        self.reentry = None
        self.existingRecordRegionPath = set()
        self.existingRecordRegionID = set()

    def request_task(self)->bool:
        # requestSQL = \
        # """
        # UPDATE article SET status = 1, last_visit_time = now() WHERE aid = (SELECT aid FROM article WHERE 
        # (status IS NULL AND now()- pub_time > '24 HOUR'::INTERVAL) OR 
        # (status = 0 AND (now() - last_visit_time) > '24 HOUR'::INTERVAL)
        # LIMIT 1 FOR UPDATE skip locked) RETURNING *;
        # """
        requestSQL = \
        """
        UPDATE article SET status = 1, last_visit_time = now() WHERE aid = (SELECT aid FROM article WHERE 
        (status IS NULL) OR 
        (status = 0 AND (now() - last_visit_time) > '24 HOUR'::INTERVAL)
        LIMIT 1 FOR UPDATE skip locked) RETURNING *;
        """
        self.cursor.execute(requestSQL)
        self.articleRow = self.cursor.fetchone()
        if self.articleRow is None:
            self.info('No task available, I am going to sleep a while...')
            self.close_selenium()
            time.sleep(3)
            return False
        if self.driver is None:
            self.open_selenium()

        self.url = self.articleRow['url']
        self.aid = self.articleRow['aid']
        # if this article has not been visited before (has record in comment_crawler table), it should be visited again if no comment is found
        return True

    def prepare_task(self)->bool:
        try:
            if super().prepare_task():
                self.scroll_to_bottom()
                return True
            else:
                return False
        except Exception as e:
            self.error(f"Failed to open page: {repr(e)}")
            self.status = -1
            return False

    def perform_task(self):
        try:
            self.vist_page()
            self.status = 2
        except Exception as e:
            self.error(f"Failed to visit page: {repr(e)}")
            self.status = -1

    def detect_comments(self, clickCnt):
        # extract structured blocks, structWebElm is for screenshot purpose
        (structEtreeElm, structWebElm) = self.detect_record_region()
        if len(structEtreeElm) == 0:
            self.numNoStruct += 1

        # structured blocks classification
        # cmtHtml = [etree.tostring(elm, encoding='utf-8').decode('utf-8') for elm in structEtreeElm]
        # cmtX = [gram_text_process(extract_attributes(html)) for html in cmtHtml]
        cmtX = [gram_text_process(extract_attributes(x)) for x in structEtreeElm]
        cmtY = self.commentClf.predict(cmtX)
        cmtPredict = [l[0].split('_')[-1] for l in cmtY[0]]
        self.numStruct = len(cmtX)

        cmtSampleCnt = 0
        for cmtEtreeElm, cmtWebElm, label in zip(structEtreeElm, structWebElm, cmtPredict):
            cmtSampleCnt += 1
            try:
                with open(join(DATA_PATH, 'html', 'comment', '{}-{}-{}-{}.html'.format(self.aid, clickCnt, cmtSampleCnt, label)), 'wb') as f:
                    f.write(etree.tostring(cmtEtreeElm, encoding='utf-8'))
                if self.takeScreenshot:
                    cmtWebElm.screenshot(join(DATA_PATH, 'screenshot', 'comment', '{}-{}-{}-{}.png'.format(self.aid, clickCnt, cmtSampleCnt, label)))
                time.sleep(0.2)
            except WebDriverException as e:
                self.error(repr(e))
            if ('1' in label or 'positive' in label):
                self.info(f'Hit comment in aid {self.aid}: {self.url}')
                self.numCmtCandidate += 1

    def vist_page(self):
        print('working on page {}: {}'.format(self.articleRow['aid'], self.url))

        # open page
        pageHTML = '<html>{}</html>'.format(self.driver.execute_script('return document.body.outerHTML'))
        # pageEtree = etree.parse(StringIO(pageHTML), parser)
        pageEtree = html.parse(StringIO(pageHTML))

        # comment button classification
        clickables = pageEtree.xpath('//a|//button')
        #clickableHtml = [etree.tostring(elm, encoding='utf-8').decode('utf-8') for elm in clickables]
        self.numClick = len(clickables)
        attribs = []
        textContents = []
        clickableCandidates = []
        for click in clickables:
            text = ''.join(click.text_content().split()).lower()
            attrib = extract_attributes(click).lower()
            if len(text) > 30 or 'mailto' in attrib or 'print' in attrib or 'mailto' in text or 'print' in text:
                # a comment button is unlikely to have more than 30 characters
                # ignore print or email
                continue
            clickableCandidates.append(click)
            attribs.append(attrib)
            textContents.append(text)

        btnX = [gram_text_process(a + t) for a, t in zip(attribs, textContents)]
        btnY = self.buttonClf.predict(btnX)
        btnPredict = [l[0].split('_')[-1] for l in btnY[0]]
        score = [s[0] for s in btnY[1]]
        btnCandidates = [c for _,c,l,a,t in sorted(zip(score, clickableCandidates, btnPredict, attribs, textContents), key = lambda t:t[0], reverse = True) if (l in ['1', 'positive'] or ('comment' in a + t or 'conversation' in a + t or 'discuss' in a + t or 'komment' in a + t or 'response' in a + t))]

        # btnX = [a + t for a, t in zip(attribs, textContents)]
        # btnCandidates = [c for c, x in zip(clickableCandidates, btnX) if 'comment' in x]

        self.numBtnCandidate = len(btnCandidates)

        # count frequent positive buttons based on DOM tree structure
        def htp(node):
            path = []
            for x in node.xpath('./ancestor-or-self::*'):
                attrib = sorted(list(x.attrib.keys()))
                path.append(tuple([x.tag] + attrib))
            return tuple(path)

        def node_signature(node):
            attrib = []
            for k in sorted(list(node.attrib.keys())):
                v = node.attrib[k][:10]
                attrib.append((k, v))
            text = tuple(node.text_content().split())
            return (node.tag, text, tuple(attrib))
    
        # btnSig = [(tuple([x.tag for x in btn.xpath('./ancestor-or-self::*')]), tuple([x.tag for x in btn.xpath('./preceding-sibling::*')+btn.xpath('./following-sibling::*')])) for btn in btnCandidates]
        btnSig = [node_signature(btn) for btn in btnCandidates]
        simBtnCnt = {}
        for sig in btnSig:
            simBtnCnt[sig] = simBtnCnt.get(sig, 0) + 1

        # also make body a null button, so we can run the all the comment detection in a big loop
        btnSig.insert(0, tuple([]))
        btnCandidates.insert(0, None)

        # click each comment button candidates
        clickCnt = 0
        self.numNoStruct = 0
        self.numCmtCandidate = 0
        for (btnTreetreeElm, btnSig) in zip(btnCandidates, btnSig):
            # to speed up the process, let's stop if we have found comments. There could be a chance that we have a false positive and thus miss the true comment.
            if self.numCmtCandidate > 0:
                break

            if clickCnt >= 10: break

            # the body is stored as None
            if btnTreetreeElm is None:
                self.detect_comments(clickCnt)
            else:
                # if more than 3 similar button exit, they are unlikely to be comment buttons
                if simBtnCnt[btnSig] > 3: continue

                self.debug(f"checking button etree element:\n\t{' '.join(btnTreetreeElm.text_content().split())}\n\t{attribute_test(btnTreetreeElm.attrib, ignoreLongString=False)}\n")

                # find the corresponding DOM element in current page
                keyAttribs = {}
                for k in btnTreetreeElm.attrib:
                    if k in custom_attrib:
                        continue
                    else:
                        keyAttribs[k] = btnTreetreeElm.attrib[k]
                if len(keyAttribs) == 0:
                    continue

                btnDomElm = self.driver.find_elements_by_xpath('.//{}[{}]'.format(btnTreetreeElm.tag, attribute_test(keyAttribs, ignoreLongString=False)))
                if len(btnDomElm) > 5:
                    self.info('ignore frequent button: \n{}'.format(etree.tostring(btnTreetreeElm)))
                    continue
                else:
                    # if we find multiple elements match the signature, use the first one that we click successfully 
                    for b in btnDomElm:
                        try:
                            self.debug(f"clicking button Web element:\n\t{b.get_attribute('outerHTML')}\n")
                            # if the button is a tag pointing to a new page, let's open it in a new tab directly
                            if b.tag_name == 'a':
                                newUrl = b.get_attribute('href')
                                newUri = urlparse(newUrl)
                                currentUri = urlparse(self.driver.current_url)
                                if newUri.scheme == 'mailto': continue # this is a link to open email
                                if newUri.scheme in ['http', 'https'] and newUri.path != currentUri.path:
                                    self.open_page(url=newUrl, markNewPage=False, closeOldTabs=False)
                                    self.scroll_to_bottom()
                                else:
                                    touch_elements(self.driver)
                                    self.click(b)
                            else:
                                touch_elements(self.driver)
                                self.click(b)

                            # save button image and HTML source
                            if self.takeScreenshot:
                                try:
                                    b.screenshot(join(DATA_PATH, 'screenshot', 'button', '{}-{}-1.png'.format(self.aid, clickCnt)))
                                except WebDriverException:
                                    pass
                                time.sleep(0.5)
                            with open(join(DATA_PATH, 'html', 'button', '{}-{}-1.html'.format(self.aid, clickCnt)), 'wb') as f:
                                f.write(etree.tostring(btnTreetreeElm, encoding='utf-8'))

                        except WebDriverException as e:
                            self.error(repr(e))
                            continue
                        self.detect_comments(clickCnt)

                        # close new tab if exists
                        if len(self.driver.window_handles) > 1:
                            if len(self.driver.window_handles) > 2:
                                self.warn('More than 2 tabs exist after clicking a button.')
                            for _ in range(len(self.driver.window_handles)-1):
                                self.close_tab()
                        clickCnt += 1
                        break
                        # # open original page if the click lead to a new page
                        # if self.is_new_page():
                        #     self.open_page()
                        
        if self.is_new_page():
            self.open_page()
            self.scroll_to_bottom()
        try:
            if self.numCmtCandidate > 0:
                if self.takeScreenshot:
                    self.save_screenshot(join(DATA_PATH, 'screenshot', 'page', '{}-1.png'.format(self.aid)))
                pageEtree.write(join(DATA_PATH, 'html', 'page', '{}-1.html'.format(self.aid)), encoding='utf-8', pretty_print=True)
            else:
                if self.takeScreenshot:
                    self.save_screenshot(join(DATA_PATH, 'screenshot', 'page', '{}-0.png'.format(self.aid)))
                pageEtree.write(join(DATA_PATH, 'html', 'page', '{}-0.html'.format(self.aid)), encoding='utf-8', pretty_print=True)
        except WebDriverException as e:
            self.error(repr(e))
    
    def complete_task(self):
        if self.status == 2:
            self.cursor.execute("INSERT INTO comment_crawler(aid, num_click, num_btn_candidate, num_structure, num_cmt_candidate, num_no_struct, stime, etime) VALUES (%(aid)s, %(num_click)s, %(num_btn_candidate)s, %(num_structure)s, %(num_cmt_candidate)s, %(num_no_struct)s, %(stime)s, now());", {'aid': self.aid, 'stime': self.articleRow['last_visit_time'], 'num_click': self.numClick, 'num_btn_candidate': self.numBtnCandidate, 'num_structure': self.numStruct, 'num_cmt_candidate': self.numCmtCandidate, 'num_no_struct': self.numNoStruct})
        self.cursor.execute('SELECT count(*) FROM comment_crawler WHERE aid = {}'.format(self.aid))
        self.reentry = (self.cursor.fetchone()[0] < self.MAX_VISIT)
        if self.reentry and self.status == 2 and not self.numCmtCandidate:
            # reentry
            self.status = 0
        completeSQL = "UPDATE article SET status = %(status)s, btn_hit = %(btn_hit)s, cmt_hit = %(cmt_hit)s WHERE aid = %(aid)s;"
        self.cursor.execute(completeSQL, {'aid': self.aid, 'status': self.status, 'btn_hit': self.numBtnCandidate is not None and self.numBtnCandidate > 0, 'cmt_hit': self.numCmtCandidate is not None and self.numCmtCandidate > 0})

        super().complete_task()
        if self.status == -1:
            self.open_selenium()
        self.init_var()
    
    def end_task(self):
        endSQL = 'SELECT count(*) FROM article WHERE status IS NULL or status = 0;'
        self.cursor.execute(endSQL)
        return self.cursor.fetchone()[0] == 0
    
    def detect_record_region(self):
        
        def region_path(node):
            ret = []
            p = node
            while p:
                ret.append(p.nodeID)
                p = p.parent
            return tuple(ret)
        
        def get_container(node):
            # a node may be an element inside an iframe or a shadow DOM
            # use the nearest ancestor with assigned ID as the region
            while node is not None and SELF_ID not in node.attrib:
                node = node.getparent()
            if node is not None:
                return node
            return None

        try:
            javascript_init(self.driver)
            self.driver.execute_script('assign_myid();')
            pageHTML = '<html>{}</html>'.format(self.driver.execute_script('return document.body.outerHTML'))
            pageEtree = html.parse(StringIO(pageHTML))
            
            # get shadow DOM hosts
            shadowDOMHosts = self.get_shadow_doms()
            for hostWebElm in shadowDOMHosts:
                try:
                    hostTreetreeElm = None
                    shadowRootWebElm = None
                    id = hostWebElm.get_attribute(SELF_ID)
                    if id:
                        hostTreetreeElm = pageEtree.xpath(f'//*[@data-self-id="{id}"]')[0]
                    else:
                        continue
                    shadowRootWebElm = self.driver.execute_script("return arguments[0].shadowRoot", hostWebElm)
                    if shadowRootWebElm is None: 
                        continue
                    for elm in shadowRootWebElm.find_elements(By.CSS_SELECTOR, ':host > *'):
                        try:
                            if elm.tag_name in ELEMENT_BLACK_LIST:
                                continue
                            htmlDoc = elm.get_attribute('outerHTML')
                            for e in etree.parse(StringIO(htmlDoc), HTML_PARSER).getroot().xpath("/html/body/*"):
                                hostTreetreeElm.append(e)
                        except WebDriverException as e:
                            self.error(repr(e))
                except WebDriverException as e:
                    self.error(repr(e))
                
            # get iframe contents
            iframeTreetreeElms = pageEtree.xpath('//iframe')
            for frmTreetreeElm in iframeTreetreeElms:
                if SELF_ID in frmTreetreeElm.attrib:
                    try:
                        frmDOMelm = self.driver.find_element_by_xpath('//iframe[@{}="{}"]'.format(SELF_ID, frmTreetreeElm.attrib[SELF_ID]))
                    except WebDriverException as e:
                        frmDOMelm = None
                else:
                    frmTreetreeElm.getparent().remove(frmTreetreeElm)
                    continue
                if frmDOMelm is None: continue
                try:
                    self.driver.switch_to.frame(frmDOMelm)
                    frmHTML = self.driver.execute_script('return document.body.outerHTML')
                    for elm in etree.parse(StringIO(frmHTML), HTML_PARSER).getroot().xpath("/html/body/*"):
                        if elm.tag not in ELEMENT_BLACK_LIST:
                            frmTreetreeElm.append(elm)
                    self.driver.switch_to.default_content()
                except WebDriverException as e:
                    # print(repr(e))
                    frmTreetreeElm.getparent().remove(frmTreetreeElm)
                    self.driver.switch_to.default_content()
        
        except WebDriverException as e:
            print('structured_blocks: {}'.format(repr(e)))
            return ([], [])

        sTree = StructTree(pageEtree.getroot())
        regionDict = sTree.record_boundary(3, 5, 3, 5, 7)
        recordRegion = []
        recordRegionID = []
        recordRegionPath = []
        for idx in regionDict:
            node = sTree[idx]
            # container = get_container(node)
            # if container is None:
            #     continue
            regionID = node.structID
            regionPath = region_path(node)
            
            recordRegion.append(node.elm)
            recordRegionID.append(regionID)
            recordRegionPath.append(regionPath)
        
        structWebElm = []
        structEtreeElm = []
        for etreeElm, path, id in zip(recordRegion, recordRegionPath, recordRegionID):
            if (id in self.existingRecordRegionID) or path in self.existingRecordRegionPath:
                continue

            if etreeElm.tag == 'body': # over merged, discard
                    continue
                
            try:
                container = get_container(etreeElm)
                if container is None:
                    continue

                webElm = self.driver.find_element_by_xpath('//*[@{}="{}"]'.format(SELF_ID, container.attrib[SELF_ID]))
            except WebDriverException as e:
                self.warn(repr(e))
                webElm = None
            if webElm is not None:
                structWebElm.append(webElm)
                structEtreeElm.append(etreeElm)
                self.existingRecordRegionPath.add(path)
                self.existingRecordRegionID.add(id)

        return (structEtreeElm, structWebElm)

    def get_shadow_doms(self):
        script = """
        ret = [];
        var allNodes = document.getElementsByTagName('*');
        for (var i = 0; i < allNodes.length; i++) {
            if(allNodes[i].shadowRoot && allNodes[i].shadowRoot.mode == "open") {
                ret.push(allNodes[i]);
            }
        }
        return ret;
        """
        return self.driver.execute_script(script)

class NaiveCommentCrawler(SeleniumDBTask):
    def __init__(self, seleniumHost:str = 'http://localhost:4444/wd/hub', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment', **kwargs):
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database, **kwargs)
        self.buttonClf = fasttext.load_model(join('fasttext', 'button', '3gram.model'))
        self.commentClf = fasttext.load_model(join('fasttext', 'comment', '3gram.model'))
        self.cursor.execute('select language_region, hl, gl, ceid from language_region')
        self.language_region = pd.DataFrame(self.cursor.fetchall(), columns = ["language_region", "hl", "gl", "ceid"])
        self.topic = ["WORLD", "NATION", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH"]
        self.MAX_VISIT = 3
        self.topicPtr = 0
        self.regionPtr = 0
        self.visitCnt = 0
        self.init_var()

    def init_var(self):
        if self.visitCnt == 1:
            self.articleRow = None
            self.aid = None
            self.url = None
        self.exitStage = None
        self.numClick = None
        self.numBtnCandidate = None
        self.numStruct = None
        self.numCmtCandidate = None
        self.numNoStruct = None # number of button candidates that do not produce any structured region 
        self.status = None

    def advance_ptr(self):
        self.topicPtr = (self.topicPtr + 1)%len(self.topic)
        if self.topicPtr == 0:
            self.regionPtr = (self.regionPtr + 1)%len(self.language_region)

    def request_task(self)->bool:
        self.visitCnt %= self.MAX_VISIT
        self.visitCnt += 1
        if (self.numCmtCandidate is not None and self.numCmtCandidate > 0):
            self.visitCnt = 1
        self.init_var()
        if self.visitCnt == 1:
            language_region = self.language_region.iloc[self.regionPtr].language_region.split(' (')
            hl=self.language_region.iloc[self.regionPtr].hl
            gl=self.language_region.iloc[self.regionPtr].gl
            ceid=self.language_region.iloc[self.regionPtr].ceid
            language = language_region[0]
            region = language_region[1][:-1]
            topic = self.topic[self.topicPtr]
            self.advance_ptr()
        

            feed = "https://news.google.com/news/rss/headlines/section/topic/{topic}?hl={hl}&gl={gl}&ceid={ceid}".format(topic=topic, hl=hl, gl=gl, ceid=ceid)
            headers = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",\
                    "Accept-Encoding":"gzip, deflate, br",\
                    "Cache-Control": "max-age=0",\
                    "Connection":"close",\
                    "Referer":"https://www.google.com/",\
                    "TE":"Trailers",\
                    "Upgrade-Insecure-Requests":"1",\
                    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"}
            response = requests.get(feed, headers = headers)
            if response.status_code != 200:
                self.error("Failed to get rss feed: {}".format(response.text))
                return False
            topicSoup = BeautifulSoup(response.content, 'lxml', from_encoding="utf-8")

            for item in topicSoup.select('rss channel item'):
                try:
                    title = item.title.contents[0].split(' - ')[0]
                    pubTime = item.pubdate.contents[0]
                    link = item.link
                    if link.contens is None:
                        link = link.next
                    else:
                        link = link.contents[0]
                    response = requests.get(link, headers = headers, timeout = 5, allow_redirects = False)
                    
                    if response.status_code != 301:
                        self.error("Google does not redirect the link {}: {}".format(link, response.text))
                        continue
                    url = response.headers['Location']
                    host = urlparse(url).netloc
                    self.cursor.execute('select wid from website where host = %(host)s and allow_comment limit 1', {'host':host})
                    wid = self.cursor.fetchall()
                    if len(wid) == 0:
                        continue
                    else:
                        wid = wid[0][0]

                    self.cursor.execute('select aid from article where url = %(url)s', {'url': url})
                    
                    if self.cursor.fetchone() is not None:
                        continue

                    self.cursor.execute('insert into article (wid, title, url, topic, language, region, pub_time, last_visit_time, status) values (%(wid)s, %(title)s, %(url)s, %(topic)s, %(language)s, %(region)s, %(pub_time)s, now(), 1) returning *;', {'wid':wid, 'title': title, 'url':url, 'topic':topic.lower(), 'language': language, 'region': region, 'pub_time': pubTime})

                    self.articleRow = self.cursor.fetchone()
                    #self.articleRow['url'] = 'https://www.youtube.com/watch?v=45gwNKj2xVM'
                    self.url = self.articleRow['url']
                    self.aid = self.articleRow['aid']
                    return True

                except Exception as e:
                    self.error(repr(e))

            self.visitCnt = 0
            return False
        else:
            self.cursor.execute('update article set last_visit_time = now() where aid = %(aid)s returning *;', {'aid':self.aid})
            self.articleRow = self.cursor.fetchone()
            return True
    
    def prepare_task(self):
        if super().prepare_task():
            self.scroll_to_bottom(scrollInterval=1)
            return True
        else:
            return False

    def perform_task(self):
        # self.vist_page()
        # self.status = 2
        try:
            self.vist_page()
            self.status = 2
        except Exception as e:
            self.error(repr(e))
            self.status = -1
    
    def detect_comments(self, clickCnt):
        # extract structured blocks
        (structEtreeElm, structWebElm) = structured_blocks(self.driver)
        if len(structEtreeElm) == 0:
            self.numNoStruct += 1

        # structured blocks classification
        cmtHtml = [etree.tostring(elm, encoding='utf-8').decode('utf-8') for elm in structEtreeElm]
        cmtX = [gram_text_process(extract_attributes(htmlDoc)) for htmlDoc in cmtHtml]
        cmtY = self.commentClf.predict(cmtX)
        cmtPredict = [l[0].split('_')[-1] for l in cmtY[0]]
        self.numStruct = len(cmtHtml)

        cmtSampleCnt = 0
        for cmtEtreeElm, cmtWebElm, label in zip(structEtreeElm, structWebElm, cmtPredict):
            cmtSampleCnt += 1
            try:
                with open(join(DATA_PATH, 'html', 'comment', '{}-{}-{}-{}.html'.format(self.aid, clickCnt, cmtSampleCnt, label)), 'wb') as f:
                    f.write(etree.tostring(cmtEtreeElm, encoding='utf-8'))
                cmtWebElm.screenshot(join(DATA_PATH, 'screenshot', 'comment', '{}-{}-{}-{}.png'.format(self.aid, clickCnt, cmtSampleCnt, label)))
                time.sleep(0.2)
            except WebDriverException as e:
                self.error(repr(e))
            if ('1' in label or 'positive' in label):
                self.numCmtCandidate += 1

    def vist_page(self):
        screenShot = self.page_screenshot()
        print('working on page {}: {}'.format(self.aid, self.url))

        # open page
        pageHTML = '<html>{}</html>'.format(self.driver.execute_script('return document.body.outerHTML'))
        pageEtree = etree.parse(StringIO(pageHTML), parser)

        # comment button classification
        clickables = pageEtree.xpath('//a|//button')
        clickableHtml = [etree.tostring(elm, encoding='utf-8').decode('utf-8') for elm in clickables]
        self.numClick = len(clickables)
        btnX = [gram_text_process(extract_attributes(html_doc) + extract_text(html_doc)) for html_doc in clickableHtml]
        btnY = self.buttonClf.predict(btnX)
        btnPredict = [l[0].split('_')[-1] for l in btnY[0]]
        score = [s[0] for s in btnY[1]]
        btnCandidates = [c for _,c,l in sorted(zip(score, clickables, btnPredict), key = lambda t:t[0], reverse = True) if l in ['1', 'positive']]
        self.numBtnCandidate = len(btnCandidates)

        # count frequent positive buttons based on DOM tree structure
        btnSig = [(tuple([x.tag for x in btn.xpath('./ancestor-or-self::*')]), tuple([x.tag for x in btn.xpath('./preceding-sibling::*')+btn.xpath('./following-sibling::*')])) for btn in btnCandidates]
        simBtnCnt = {}
        for sig in btnSig:
            simBtnCnt[sig] = simBtnCnt.get(sig, 0) + 1

        # also make body a null button, so we can run the all the comment detection in a big loop
        btnSig.insert(0, None)
        btnCandidates.insert(0, None)

        # click each comment button candidates
        clickCnt = 0
        self.numNoStruct = 0
        self.numCmtCandidate = 0
        visited = set()
        for (btnTreetreeElm, btnSig) in zip(btnCandidates, btnSig):
            if clickCnt > 10: break

            # the body is stored as None
            if btnTreetreeElm is None:
                self.detect_comments(clickCnt)
            else:
                # if more than 3 similar button exit, they are unlikely to be comment buttons
                if simBtnCnt[btnSig] > 3: continue

                # find the corresponding DOM element in current page
                keyAttribs = {}
                for k in btnTreetreeElm.attrib:
                    if k in custom_attrib:
                        continue
                    else:
                        keyAttribs[k] = btnTreetreeElm.attrib[k]
                if len(keyAttribs) == 0:
                    continue

                btnDomElm = self.driver.find_elements_by_xpath('.//{}[{}]'.format(btnTreetreeElm.tag, attribute_test(keyAttribs, ignoreLongString=False)))
                if len(btnDomElm) > 3:
                    self.info('ignore frequent button: \n{}'.format(etree.tostring(btnTreetreeElm)))
                    continue
                else:
                    # if we find multiple elements match the signature, use the first one that we click successfully 
                    for b in btnDomElm:
                        try:
                            # if the button is a tag pointing to a new page, let's open it in a new tab directly
                            if b.tag_name == 'a':
                                newUrl = b.get_attribute('href')
                                if newUrl in visited:
                                    continue
                                else:
                                    visited.add(newUrl)
                                newUri = urlparse(newUrl)
                                currentUri = urlparse(self.driver.current_url)
                                if newUri.scheme == 'mailto': continue # this is a link to open email
                                if newUri.scheme in ['http', 'https'] and newUri.path != currentUri.path:
                                    self.open_page(url=newUrl, markNewPage=False, closeOldTabs=False, timeout=3)
                                    self.scroll_to_bottom(simple=True, scrollInterval=0)
                                else:
                                    touch_elements(self.driver)
                                    self.click(b)
                                    self.scroll_to_bottom(simple=True, scrollInterval=0)
                            else:
                                touch_elements(self.driver)
                                self.click(b)

                        except ElementNotInteractableException as e:
                            self.error(repr(e))
                            continue

                        self.detect_comments(clickCnt)

                        # close new tab if exists
                        if len(self.driver.window_handles) > 1:
                            if len(self.driver.window_handles) > 2:
                                self.warn('More than 2 tabs exist after clicking a button.')
                            for _ in range(len(self.driver.window_handles)-1):
                                self.close_tab()

                        # open original page if the click lead to a new page
                        if self.is_new_page():
                            self.open_page()
                            self.scroll_to_bottom(simple=True, scrollInterval=0)

        try:
            # if self.is_new_page():
            #     self.open_page(timeout=5)
            #     self.scroll_to_bottom(simple=True, scrollInterval=0)
            if self.numCmtCandidate > 0:
                if screenShot:
                    with open(join(DATA_PATH, 'screenshot', 'page', '{}-1.png'.format(self.aid)), 'wb') as f:
                        f.write(screenShot)
                #self.save_screenshot(join(DATA_PATH, 'screenshot', 'page', '{}-1.png'.format(self.aid)))
                pageEtree.write(join(DATA_PATH, 'html', 'page', '{}-1.html'.format(self.aid)), encoding='utf-8', pretty_print=True)
            else:
                if screenShot:
                    with open(join(DATA_PATH, 'screenshot', 'page', '{}-0.png'.format(self.aid)), 'wb') as f:
                        f.write(screenShot)
                #self.save_screenshot(join(DATA_PATH, 'screenshot', 'page', '{}-0.png'.format(self.aid)))
                pageEtree.write(join(DATA_PATH, 'html', 'page', '{}-0.html'.format(self.aid)), encoding='utf-8', pretty_print=True)
        except WebDriverException as e:
            self.error(repr(e))
    
    def complete_task(self):
        if self.status == 2:
            self.cursor.execute("INSERT INTO naive_comment_crawler(aid, num_click, num_btn_candidate, num_structure, num_cmt_candidate, num_no_struct, stime, etime) VALUES (%(aid)s, %(num_click)s, %(num_btn_candidate)s, %(num_structure)s, %(num_cmt_candidate)s, %(num_no_struct)s, %(stime)s, now());", {'aid': self.aid, 'stime': self.articleRow['last_visit_time'], 'num_click': self.numClick, 'num_btn_candidate': self.numBtnCandidate, 'num_structure': self.numStruct, 'num_cmt_candidate': self.numCmtCandidate, 'num_no_struct': self.numNoStruct})

        completeSQL = "UPDATE article SET status = %(status)s WHERE aid = %(aid)s;"
        self.cursor.execute(completeSQL, {'aid': self.aid, 'status': self.status})

        super().complete_task()
    
    def end_task(self):
        return False

class NewsMonitor(BaseTask, Postgres):
    def __init__(self, databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment'):
        Postgres.__init__(self, host=databaseHost, user=user, password=password, database=database)
        self.topic = ["WORLD", "NATION", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH"]
        self.cursor.execute('select language_region, hl, gl, ceid from language_region')
        self.language_region = pd.DataFrame(self.cursor.fetchall(), columns = ["language_region", "hl", "gl", "ceid"])
    
    def request_task(self):
        return True
    
    def prepare_task(self):
        return True
    
    def complete_task(self):
        pass
    
    def end_task(self):
        return False

    def perform_task(self):
        from collections import deque
        headers = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",\
                   "Accept-Encoding":"gzip, deflate, br",\
                   "Cache-Control": "max-age=0",\
                   "Connection":"close",\
                   "Referer":"https://www.google.com/",\
                   "TE":"Trailers",\
                   "Upgrade-Insecure-Requests":"1",\
                   "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"}
        linkSet = set()
        linkQueue = deque([])
        cacheSize = 100000
        while 1:
            for row in self.language_region.iloc:
                language_region = row.language_region.split(' (')
                language = language_region[0]
                region = language_region[1][:-1]
                for topic in self.topic:
                    feed = "https://news.google.com/news/rss/headlines/section/topic/{topic}?hl={hl}&gl={gl}&ceid={ceid}".format(topic=topic, hl=row.hl, gl=row.gl, ceid=row.ceid)
                    try:
                        response = requests.get(feed, headers = headers)
                    except Exception as e:
                        print(repr(e))
                        continue
        
                    if response.status_code != 200:
                        self.error("Failed to get rss feed: {}".format(response.text))
                        continue
                    topicSoup = BeautifulSoup(response.content, 'lxml', from_encoding="utf-8")
                    
                    for item in topicSoup.select('rss channel item'):
                        try:
                            title = item.title.contents[0].split(' - ')[0]
                            pubTime = item.pubdate.contents[0]
                            link = item.link
                            if link.contens is None:
                                link = link.next
                            else:
                                link = link.contents[0]
                            if link in linkSet:
                                continue
                            else:
                                response = requests.get(link, headers = headers, timeout = 5, allow_redirects = False)
                            
                                if response.status_code != 301:
                                    self.error("Google does not redirect the link {}: {}".format(link, response.text))
                                    continue
                                else:
                                    if len(linkQueue) >= cacheSize:
                                        linkSet.remove(linkQueue.popleft())
                                    linkSet.add(link)
                                    linkQueue.append(link)
                            url = response.headers['Location']
                            host = urlparse(url).netloc
                            try:
                                self.cursor.execute('insert into news_monitor (url, title, topic, language, region, pub_time) values (%(url)s, %(title)s, %(topic)s, %(language)s, %(region)s, %(pub_time)s);', {'url':url, 'title':title, 'topic':topic, 'language': language, 'region': region, 'pub_time': pubTime})
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print('{} inserted article:\n\tTitle: {}\n\tTopic: {}\n\tLanguage: {}\n\tRegion: {}\n\tURL: {}\n\tPublication time:{}'.format(now, title, topic, language, region, url, pubTime))
                            except psycopg2.IntegrityError:
                                continue
                            time.sleep(1)

                        except Exception as e:
                            self.error(repr(e))
            
            self.cursor.execute('select count(*) from news_monitor where discovered_time > current_date')
            count = self.cursor.fetchall()[0][0]
            #print('{} articles found today.'.format(count))
            print('{} articles found today, I am going to sleep for 10 minutes.'.format(count))

            for i in range(10, 0, -1):
                print('Remaining sleeping time: {} minutes'.format(i))
                time.sleep(60)

SUCCESS = 0 
BTN_CLF = 1
STRUCT_MISS = 2
CMT_CLF = 3
CMT_NUM = 4
BAD_EVENT = 5

class CheckCrawlerWithQueue(SeleniumDBTask):
    """
    Check comments recognition results.
    for each page:
        open the screenshot, tell if it has comments or comment button
        if the page has comments:
            decide if the result is correct
            if not:
                if the comment section is not loaded successfully or there is a full page covering:
                    blocked by bad Web event
                go through each detected structured section
                if the comment section structured is detected:
                    missed by the classifier
                else:
                    if there are more than 5 comments:
                        missed by structure
                    else:
                        missed by number
        elif the page has comment button:
            open page url in new tab
            select the comment button
            if the comment button is classified correctly:
                if the comment section is not loaded successfully or there is a full page covering:
                    blocked by bad Web event
                go through each detected structured section
                if the comment section structured is detected:
                    missed by the classifier
                else:
                    if there are more than 5 comments:
                        missed by structure
                    else:
                        missed by number
            else:
                missed by the button classifier
    
    database table:
    pid, hasButton, hitButton, hasComment, hitComment, failCode(0: success, 1: button classifier, 2: structure detection, 3: comment classifier, 4: comment number, 5: bad Web event)
    """
    def __init__(self, dataPath, seleniumHost:str = 'http://127.0.0.1:4444/wd/hub', browser:str = 'firefox', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment') -> None:
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database)
        self.init_var()
        self.dataPath = dataPath
        self.btnClf = fasttext.load_model(join('fasttext', 'button', '3gram.model'))
        self.import_data()
    
    def init_var(self):
        # ground truth
        self.hasBtn = None
        self.hasCmt = None

        # program output
        self.gotBtn = None
        self.gotCmt = None
        
        # human judge
        self.hitBtn = None
        self.hitCmt = None
        self.failureCode = None

        self.status = 1

    def import_data(self):
        pageShot = listdir(join(self.dataPath, 'screenshot', 'page'))
        self.pageShot = {}
        for s in pageShot:
            aid = int(s.split('-')[0])
            if aid not in self.pageShot or s.split('-')[-1].split('.')[0] == '1':
                self.pageShot[aid] = s
        
        structShot = listdir(join(self.dataPath, 'screenshot', 'comment'))
        self.structShot = {}
        for s in structShot:
            aid = int(s.split('-')[0])
            self.structShot.setdefault(aid, []).append(s)

        # we only need to check comment button at website level
        widSQL = \
        """
        SELECT DISTINCT ON (article.wid) wid, count_results.hit_btn FROM article INNER JOIN count_results ON article.aid = count_results.aid WHERE count_results.status = 2 and count_results.has_btn
        """
        self.cursor.execute(widSQL)
        self.btnWidChecked = {}
        for r in self.cursor.fetchall():
            self.btnWidChecked[r['wid']] = r['hit_btn']

    def request_task(self):
        self.init_var()
        requestSQL = \
        """
        UPDATE count_results SET status = 1 where aid = (SELECT aid FROM count_results WHERE status = 0 LIMIT 1 FOR UPDATE SKIP LOCKED) returning aid, (SELECT url FROM article WHERE aid = count_results.aid);
        """
        self.cursor.execute(requestSQL)
        row = self.cursor.fetchone()
        if row is None:
            return False
        self.url = row['url']
        self.aid = row['aid']

        self.cursor.execute("SELECT wid from article WHERE aid = {}".format(self.aid))
        self.wid = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT * FROM naive_comment_crawler WHERE aid = {}".format(self.aid))
        results = self.cursor.fetchall()
        self.gotBtn = sum([row['num_btn_candidate'] for row in results]) > 0
        self.gotCmt = sum([row['num_cmt_candidate'] for row in results]) > 0
        return True

    def prepare_task(self):
        if self.aid not in self.pageShot:
            self.error('Page {} does not have screenshot.'.format(self.aid))
            self.status = -1
            return False
        self.open_page(self.url, markNewPage=False, openInNewTab=True, closeOldTabs=True, timeout=1)
        self.open_page('file:///'+join(self.dataPath, 'screenshot', 'page', self.pageShot[self.aid]).replace('\\', '/'), markNewPage=False, openInNewTab=True, closeOldTabs=False)
        return True
        # if self.gotCmt:
        #     pageShot = join(self.dataPath, 'screenshot', 'page', '{}-1.png'.format(self.aid))
        # else:
        #     pageShot = join(self.dataPath, 'screenshot', 'page', '{}-0.png'.format(self.aid))
        # if isfile(pageShot):
        #     self.open_page('file:///'+pageShot, markNewPage=False, openInNewTab=True, closeOldTabs=False)

    def perform_task(self):
        #self.driver.switch_to.window(self.driver.window_handles[0])
        self.hasBtn = (input('Does this page has comment button?').lower() in ['1', 'y', 'yes'])
        if self.hasBtn:
            if self.wid not in self.btnWidChecked:
                self.driver.switch_to.window(self.driver.window_handles[0])
                btnHTML = None
                while btnHTML is None:
                    if input('Use comment button in console as temp0.') == '0':
                        self.hitBtn = False
                        break
                    try:
                        btnHTML = self.driver.execute_script('return temp0.outerHTML')
                    except WebDriverException as e:
                        self.info(repr(e))

                if btnHTML:
                    btnX = gram_text_process(extract_attributes(btnHTML))
                    btnY = self.btnClf.predict(btnX)[0][0]
                    if 'positive' in btnY:
                        self.hitBtn = True
                    else:
                        self.hitBtn = False
                        self.info('Missed comment button: \n\t{}'.format(btnHTML))
                
                self.btnWidChecked[self.wid] = self.hitBtn
            else:
                self.info("Skip checking button.")
                self.hitBtn = self.btnWidChecked[self.wid]

        self.open_tab() # for structure screenshot
        self.open_tab() # for structure html
        self.hasCmt = (input('Does this page has comments?').lower() in ['1', 'y', 'yes'])
        if self.hasCmt:
            self.hitCmt = False
            if self.gotCmt:
                for shot in self.structShot.get(self.aid, []):
                    if shot.split('-')[-1].split('.')[0] == '1':
                        htmlFile = join(self.dataPath, 'html', 'comment', shot.replace('png', 'html')).replace('\\', '/')
                        shot = join(self.dataPath, 'screenshot', 'comment', shot).replace('\\', '/')
                        self.driver.switch_to.window(self.driver.window_handles[-2])
                        self.open_page('file:///'+shot, markNewPage=False, openInNewTab=False, closeOldTabs=False)
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.open_page('file:///'+htmlFile, markNewPage=False, openInNewTab=False, closeOldTabs=False, timeout=0.1)
                        self.driver.switch_to.window(self.driver.window_handles[-2])
                        if input('Is this a comment section?').lower() in ['1', 'y', 'yes']:
                            self.hitCmt = True
                            break

            if not self.hitCmt:
                if input('Is this page blocked or comment loading timeout?').lower() in ['1', 'y', 'yes']:
                    self.failureCode = BAD_EVENT
                elif self.hasBtn and not self.hitBtn:
                    self.failureCode = BTN_CLF
                elif input('Number of comments < 5?').lower() in ['1', 'y', 'yes']:
                    self.failureCode = CMT_NUM
                else:
                    self.failureCode = STRUCT_MISS
                    for shot in self.structShot.get(self.aid, []):
                        if shot.split('-')[-1].split('.')[0] == '0':
                            htmlFile = join(self.dataPath, 'html', 'comment', shot.replace('png', 'html')).replace('\\', '/')
                            shot = join(self.dataPath, 'screenshot', 'comment', shot).replace('\\', '/')
                            self.driver.switch_to.window(self.driver.window_handles[-2])
                            self.open_page('file:///'+shot, markNewPage=False, openInNewTab=False, closeOldTabs=False)
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            self.open_page('file:///'+htmlFile, markNewPage=False, openInNewTab=False, closeOldTabs=False, timeout=0.1)
                            self.driver.switch_to.window(self.driver.window_handles[-2])
                            if input('Is this a comment section?').lower() in ['1', 'y', 'yes']:
                                self.failureCode = CMT_CLF
                                break
        self.status = 2
        return True

    def complete_task(self):
        completeSQL = "UPDATE count_results SET has_btn = %(has_btn)s, hit_btn = %(hit_btn)s, has_cmt = %(has_cmt)s, hit_cmt = %(hit_cmt)s, failure_code = %(failure_code)s, status = %(status)s WHERE aid = %(aid)s;"
        self.cursor.execute(completeSQL, {'aid': self.aid, 'has_btn': self.hasBtn, 'hit_btn':self.hitBtn, 'has_cmt': self.hasCmt, 'hit_cmt': self.hitCmt, 'failure_code': self.failureCode, 'status': self.status})
        super().complete_task()

        self.info('Finish article {}.'.format(self.aid))

class CheckCrawlerWithoutQueue(SeleniumDBTask):
    def __init__(self, dataPath, seleniumHost:str = 'http://127.0.0.1:4444/wd/hub', browser:str = 'firefox', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment') -> None:
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database)
        self.init_var()
        self.dataPath = dataPath
        self.btnClf = fasttext.load_model(join('fasttext', 'button', '3gram.model'))
        self.import_data()
    
    def init_var(self):
        # ground truth
        self.hasBtn = None
        self.hasCmt = None

        # program output
        self.gotBtn = None
        self.gotCmt = None
        
        # human judge
        self.hitBtn = None
        self.hitCmt = None
        self.failureCode = None

        self.status = 1

    def import_data(self):
        pageShot = listdir(join(self.dataPath, 'screenshot', 'page'))
        self.pageShot = {}
        for s in pageShot:
            try:
                aid = int(s.split('-')[0])
                if aid not in self.pageShot or s.split('-')[-1].split('.')[0] == '1':
                    self.pageShot[aid] = s
            except Exception as e:
                print(repr(e))
        
        structShot = listdir(join(self.dataPath, 'screenshot', 'comment'))
        self.structShot = {}
        for s in structShot:
            try:
                aid = int(s.split('-')[0])
                self.structShot.setdefault(aid, []).append(s)
            except Exception as e:
                print(repr(e))

    def request_task(self):
        self.init_var()
        requestSQL = \
        """
        UPDATE count_results SET status = 1 where id = (SELECT id FROM count_results WHERE status = 0 LIMIT 1 FOR UPDATE SKIP LOCKED) returning id, aid, (SELECT url FROM article WHERE aid = count_results.aid);
        """
        self.cursor.execute(requestSQL)
        row = self.cursor.fetchone()
        if row is None:
            return False
        self.id = row['id']
        self.url = row['url']
        self.aid = row['aid']

        self.cursor.execute("SELECT wid from article WHERE aid = {}".format(self.aid))
        self.wid = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT * FROM naive_comment_crawler WHERE id = {}".format(self.id))
        results = self.cursor.fetchall()
        self.gotBtn = sum([row['num_btn_candidate'] for row in results]) > 0
        self.gotCmt = sum([row['num_cmt_candidate'] for row in results]) > 0
        return True

    def prepare_task(self):
        if self.aid not in self.pageShot:
            self.error('Page {} does not have screenshot.'.format(self.aid))
            self.status = -1
            return False
        self.open_page(self.url, markNewPage=False, openInNewTab=True, closeOldTabs=True, timeout=1)
        self.open_page('file:///'+join(self.dataPath, 'screenshot', 'page', self.pageShot[self.aid]).replace('\\', '/'), markNewPage=False, openInNewTab=True, closeOldTabs=False)
        return True

    def perform_task(self):
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.hasCmt = (input('Does this page has comments?').lower() in ['1', 'y', 'yes'])
        if self.hasCmt:
            self.hitCmt = False
            if self.gotCmt:
                self.open_tab() # for structure screenshot
                self.open_tab() # for structure html
                for shot in self.structShot.get(self.aid, []):
                    if shot.split('-')[-1].split('.')[0] == '1':
                        htmlFile = join(self.dataPath, 'html', 'comment', shot.replace('png', 'html')).replace('\\', '/')
                        shot = join(self.dataPath, 'screenshot', 'comment', shot).replace('\\', '/')
                        self.driver.switch_to.window(self.driver.window_handles[-2])
                        self.open_page('file:///'+shot, markNewPage=False, openInNewTab=False, closeOldTabs=False)
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.open_page('file:///'+htmlFile, markNewPage=False, openInNewTab=False, closeOldTabs=False, timeout=0.1)
                        self.driver.switch_to.window(self.driver.window_handles[-2])
                        if input('Is this a comment section?').lower() in ['1', 'y', 'yes']:
                            self.hitCmt = True
                            break
        self.status = 2
        return True

    def complete_task(self):
        completeSQL = "UPDATE count_results SET has_cmt = %(has_cmt)s, hit_cmt = %(hit_cmt)s, status = %(status)s WHERE id = %(id)s;"
        self.cursor.execute(completeSQL, {'id': self.id, 'has_cmt': self.hasCmt, 'hit_cmt': self.hitCmt,  'status': self.status})
        super().complete_task()
        self.info('Finish article {}.'.format(self.aid))

class CountCommentNumber(SeleniumDBTask):
    def __init__(self, dataPath, seleniumHost:str = 'http://127.0.0.1:4444/wd/hub', browser:str = 'firefox', databaseHost: str='localhost', user: str='postgres', password: str='postgres', database: str='comment') -> None:
        super().__init__(seleniumHost=seleniumHost, databaseHost=databaseHost, user=user, password=password, database=database)
        self.init_var()
        self.dataPath = dataPath
        self.btnClf = fasttext.load_model(join('fasttext', 'button', '3gram.model'))
        self.import_data()
    
    def init_var(self):
        self.cmtNum = None
        self.status = 1

    def import_data(self):
        pageShot = listdir(join(self.dataPath, 'screenshot', 'page'))
        self.pageShot = {}
        for s in pageShot:
            aid = int(s.split('-')[0])
            if aid not in self.pageShot or s.split('-')[-1].split('.')[0] == '1':
                self.pageShot[aid] = s
        
        structShot = listdir(join(self.dataPath, 'screenshot', 'comment'))
        self.structShot = {}
        for s in structShot:
            aid = int(s.split('-')[0])
            self.structShot.setdefault(aid, []).append(s)


    def request_task(self):
        self.init_var()
        requestSQL = \
        """
        UPDATE count_results SET status = 1 where aid = (SELECT aid FROM count_results WHERE has_cmt and cmt_num = 0 LIMIT 1 FOR UPDATE SKIP LOCKED) returning aid, (SELECT url FROM article WHERE aid = count_results.aid);
        """
        self.cursor.execute(requestSQL)
        row = self.cursor.fetchone()
        if row is None:
            return False
        self.url = row['url']
        self.aid = row['aid']
        return True


    def prepare_task(self):
        if self.aid not in self.pageShot:
            self.error('Page {} does not have screenshot.'.format(self.aid))
            self.status = -1
            return False
        self.open_page(self.url, markNewPage=False, openInNewTab=True, closeOldTabs=True, timeout=1)
        self.open_page('file:///'+join(self.dataPath, 'screenshot', 'page', self.pageShot[self.aid]).replace('\\', '/'), markNewPage=False, openInNewTab=True, closeOldTabs=False)
        return True
        # if self.gotCmt:
        #     pageShot = join(self.dataPath, 'screenshot', 'page', '{}-1.png'.format(self.aid))
        # else:
        #     pageShot = join(self.dataPath, 'screenshot', 'page', '{}-0.png'.format(self.aid))
        # if isfile(pageShot):
        #     self.open_page('file:///'+pageShot, markNewPage=False, openInNewTab=True, closeOldTabs=False)

    def perform_task(self):
        #self.driver.switch_to.window(self.driver.window_handles[0])

        while self.cmtNum is None:
            try:
                self.cmtNum = int(input('Number of comments: '))
            except Exception as e:
                self.info(repr(e))


        self.status = 2
        return True

    def complete_task(self):
        completeSQL = "UPDATE count_results SET cmt_num = %(cmt_num)s, status = %(status)s WHERE aid = %(aid)s;"
        self.cursor.execute(completeSQL, {'aid': self.aid, 'cmt_num': self.cmtNum, 'status': self.status})
        super().complete_task()
        self.info('Finish article {}.'.format(self.aid))
        
class PageCollection(SeleniumTask):
    def __init__(self, URL, output, host: str = 'http://127.0.0.1:4444/wd/hub', windowWidth=1920, windowHeight=1080):
        super().__init__(host, windowWidth, windowHeight)
        self.URL = URL
        self.output = output
        self.i = -1
    
    def request_task(self):
        return self.i < len(self.URL)

    def prepare_task(self):
        self.open_page(self.URL[self.i])
        return True
    
    def perform_task(self):
        try:
            html = '<html>{}</html>'.format(self.driver.execute_script('return document.body.outerHTML'))
            with open(join(self.output, f'{self.i}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            self.i += 1
            return True
        except Exception as e:
            print(repr(e))
            return False
    
    def complete_task(self):
        pass