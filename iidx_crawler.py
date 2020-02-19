# coding UTF-8
from selenium import webdriver
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import Select
from time import sleep
from bs4 import BeautifulSoup
import lxml.html
import sys
import json
import os
import re
from datetime import datetime
# import re
from enum import Enum, auto

from logging import getLogger, StreamHandler, FileHandler, Formatter, FileHandler, DEBUG, INFO
logger = getLogger(__name__)

score_rank = {
    "---": 0,
    "F": 1,
    "E": 2,
    "D": 3,
    "C": 4,
    "B": 5,
    "A": 6,
    "AA": 7,
    "AAA": 8
}

ID = 'ids'
PLAYER_DATA = 'player_data'


class Target(Enum):  # クロールページの対象
    LEVEL = auto()
    SERIES = auto()
    NAME = auto()


class IIDXCrawler:

    def __init__(self, site_data, key, headless=True):
        options = ChromeOptions()
        options.set_headless(headless=headless)
        self.driver = Chrome(options=options)
        self.data = site_data
        self.is_login = False
        self.key = key
        self.headless = headless
        logger.info("Google Chrome was invoked.")

    def login(self):
        '''
        ログイン処理
        '''
        if self.is_login:
            logger.info("Crawler has already logined.")
            return
        data = self.data["login_data"]
        login_url, ID, PASS = data["login_url"], data["ID"], data["PASS"]
        ID_form, pass_form, submit_button = data["ID_form"], data["pass_form"], data["submit_button"]

        driver = self.driver
        driver.get(login_url)

        sleep(1)
        self.screenshot('img/login_page.png')
        # ログイン時スクリーン画像に従って、左からチェックする箇所に1,それ以外に0と入力する。
        logger.info(
            "Input 5 values (0 or 1) according to the image file img/login_page.png")
        kcaptcha = input().split()
        while len(kcaptcha) != 5:
            logger.info("set 5 values (0 or 1)")
            kcaptcha = input().split()
        for i in range(5):
            if kcaptcha[i] == "1":
                driver.find_element_by_id("id_kcaptcha_c"+str(i)).click()

        tmp = driver.find_element_by_xpath(ID_form)
        tmp.send_keys(ID)
        tmp = driver.find_element_by_xpath(pass_form)
        tmp.send_keys(PASS)
        sleep(1)
        driver.find_element_by_xpath(submit_button).click()

        sleep(1)
        self.screenshot('img/after_login.png')
        logger.debug('login success.')
        self.is_login = True
        return

    def get_ranking_id(self, ranking_name, url):
        '''
        ランキングからidを取得。
        '''
        self.driver.get(url)
        self.get_iidx_id('./ids/'+ranking_name+'_sp')

    def get_dani_id(self):
        '''
        段位からidを取得。
        '''
        for dani in self.data["dani"]:
            url = "https://p.eagate.573.jp/game/2dx/27/p/ranking/dani.html?page=0&play_style=0&grade_id="+dani+"&display=1"
            self.driver.get(url)

            self.get_iidx_id('./ids/'+dani+'_sp')

    def get_iidx_id(self, file_path):
        driver = self.driver
        ids = []
        sleep(1)
        dom = lxml.html.fromstring(driver.page_source)
        daniurls = dom.xpath(
            "//*[@class='play-tab' and @class!='no-show']//*[@class='navi-page']//a/@href")
        daniurls = self.unique_list(daniurls)
        sp_dani = [url for url in daniurls if url.find('play_style=1') < 0]
        # dp_dani = [url for url in daniurls if url.find('play_style=0') < 0]
        iidx_id = dom.xpath(
            "//*[@class='play-tab' and @class != 'no-show']//*[@class='dj-id']/text()")
        iidx_id = [x for x in iidx_id if x.find("-") != -1]
        if(len(iidx_id) > 200):
            iidx_id = iidx_id[:200]
        ids.extend(iidx_id)
        # sp段位取得者id取得
        count = 1
        for sp_url in sp_dani:
            logger.info(count)
            driver.get(self.data["top_url"]+sp_url)
            dom = lxml.html.fromstring(driver.page_source)
            iidx_id = dom.xpath(
                "//*[@class='play-tab' and @class != 'no-show']//*[@class='dj-id']/text()")
            iidx_id = [x for x in iidx_id if x.find("-") != -1]
            ids.extend(iidx_id)
            sleep(1)
            count = count+1
        ids_unq = self.unique_list(ids)
        logger.info("obtain {} ids.(unq : {})".format(len(ids), len(ids_unq)))
        with open(file_path+'.json', 'w') as f:
            json.dump(ids, f, indent=4, ensure_ascii=False)
        return

    def get_all_player_data(self, path):
        '''
        pathに指定されたjsonのユーザーデータをすべて取得。
        '''
        with open(path, 'r') as f:
            ids = json.loads(f.read())
        player_data = []
        count = 1
        json_count = 1
        num_id = len(ids)
        try:
            for id in ids:
                player_data.append(self.get_player_data(id.replace('-', '')))
                print("player_data {} / {}".format(count, num_id))
                count = count+1
                if len(player_data) >= 500:
                    export_path = re.sub(
                        r'.*(/.*)(\.json)$', PLAYER_DATA+r'\1_'+str(json_count)+r'\2', path)
                    with open(export_path, 'w') as f:
                        json.dump(player_data, f, indent=4, ensure_ascii=False)
                    logger.debug("json dump : {}".format(json_count))
                    player_data = []
                    json_count = json_count + 1
        except:
            import traceback
            traceback.print_exc()
        finally:
            if player_data:
                export_path = re.sub(
                    r'.*(/.*)(\.json)$', PLAYER_DATA+r'\1_'+str(json_count)+r'\2', path)
                with open(export_path, 'w') as f:
                    json.dump(player_data, f, indent=4, ensure_ascii=False)
                # player_data = []
                logger.debug("json dump : {}".format(json_count))

    def get_player_data(self, iidx_id):
        '''
        指定したidの詳細プレイヤーデータを取得。
        '''
        logger.debug(iidx_id)
        driver = self.driver
        result = True
        while(result):
            self.goto_page(
                "https://p.eagate.573.jp/game/2dx/27/p/rival/rival_search.html")
            try:

                driver.find_element_by_name("iidxid").send_keys(iidx_id)
                driver.find_element_by_class_name("submit_btn").click()
                sleep(1)
            except Exception as e:
                logger.warning(e)
                logger.warning("Crawler will retry after 1 minute.")
                sleep(60)
                continue
            result = False
        crawler.screenshot("img/result.png")
        dom = lxml.html.fromstring(driver.page_source)
        info = dom.xpath("//*[@id = 'result']/tbody/tr[2]/td")
        player_page = info[0].xpath("./a/@href")[0]
        dj_name = info[0][0].text
        dani = info[2].text.split('/')
        spdani = dani[0]
        dpdani = dani[1]
        area = info[3].text
        player_data = {
            "iidx_id": iidx_id,
            "page": player_page,
            "name": dj_name,
            "spdani": spdani,
            "dpdani": dpdani,
            "area": area
        }
        return player_data

    def goto_page(self, url):
        '''
        driver.getのラッパー
        '''
        roop = True
        while roop:
            try:
                self.driver.get(url)
                sleep(1)
                roop = False
            except Exception as e:
                logger.warning(e)
                logger.warning("crawler will retry after 1 minute.")
                sleep(60)

    def get_scores(self, player_data, target, level=12):
        '''
        対象ユーザーのスコアを取得。
        player_data : dict
        前段階で取得したプレイヤー情報。
        target : Target 
        取得場所（レベル別、シリーズ別、名前別）
        level : int
        '''
        # レベル別一覧からの取得のみ実装。
        if target == Target.LEVEL:
            self.from_level(player_data, level)

    def get_player_page(self, iidx_id):  # プレイヤーページのurlを抽出
        driver = self.driver
        result = True
        while(result):
            self.goto_page(
                "https://p.eagate.573.jp/game/2dx/27/rival/rival_search.html")
            try:

                driver.find_element_by_name("iidxid").send_keys(iidx_id)
                driver.find_element_by_class_name("submit_btn").click()
                sleep(1)
            except Exception as e:
                logger.warning(e)
                logger.warning("Crawler will retry after 1 minute.")
                sleep(60)
                continue
            result = False
        dom = lxml.html.fromstring(driver.page_source)
        info = dom.xpath("//*[@id = 'result']/tbody/tr[2]/td")
        return info[0].xpath("./a/@href")[0]

    def from_level(self, player_data, level):
        print("level {} extraction start".format(level,))
        length = len(player_data)
        i = 1
        for d in player_data:
            print(''.join([str(i), "/", str(length)]))
            self.get_score(d, level)
            i = i + 1

    def get_score(self, player_data, level):
        '''
        指定したプレイヤーidの、指定したレベルの曲スコアを取得する。
        player_data :
        {
            "iidx_id" : string
        }
        プレイヤー情報。前段階で取得したユーザーデータを引数として受け取っているが、現状使用しているのはiidx_idのみ。
        level : int
        取得するレベル。1から12を指定。
        '''
        iidx_id = player_data["iidx_id"]
        extraction_time = datetime.strftime(datetime.now(), "%Y%m%d")
        if os.path.exists(''.join(["./score_data/", extraction_time, "/", str(iidx_id), "_", str(level), ".json"])):
            logger.info("already exits. : {}".format(iidx_id))
            return
        try:
            player_page = self.abs_url(
                self.get_player_page(player_data["iidx_id"]))
        except IndexError:
            logger.warning("indexerror")
            crawler.screenshot("img/error.png")
            return
        url = re.sub("rival/rival_status", "music/difficulty_rival",
                     player_page)
        logger.debug(url)

        self.goto_page(url)
        Select(self.driver.find_element_by_name(
            "difficult")).select_by_value(str(level-1))
        self.driver.find_element_by_class_name("submit_btn").click()
        sleep(1)
        rank = re.compile(r".*icon/([A-F\-]*)\.gif")
        ramp = re.compile(r'.*clflg([0-7]).*')
        driver = self.driver
        flg = True
        score_data_all = []
        while flg:

            dom = lxml.html.fromstring(driver.page_source)
            table = dom.xpath("//*[@class='series-difficulty']//tr")
            # スコアテーブルの各行からデータ取得。
            for tr in table:
                score_data = {}
                td = tr.xpath("./td")
                if len(td) != 5:
                    continue
                score_data["title"] = td[0].xpath(".//text()")[0]
                score_data["difficulty"] = td[1].text
                score_data["rank"] = score_rank[re.sub(
                    rank, r'\1', td[2].xpath("./img/@src")[0])]
                score_data["iidx_id"] = iidx_id
                score_data["level"] = level
                score_data["score"] = td[3].text
                score_data["ramp"] = int(
                    re.sub(ramp, r'\1', td[4].xpath("./img/@src")[0]))
                score_data_all.append(score_data)
            next_page = dom.xpath("//*[@class='navi-next']")
            if next_page:
                self.goto_page(self.abs_url(
                    next_page[0].xpath("./a/@href")[0]))
            else:
                flg = False

        if not os.path.exists("./score_data/"+extraction_time):
            os.mkdir("score_data/"+extraction_time)
        # jsonで出力
        with open(''.join(["./score_data/", extraction_time, "/", str(iidx_id), "_", str(level), ".json"]), "w") as f:
            json.dump(score_data_all, f, indent=4, ensure_ascii=False)

    def unique_list(self, seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if x not in seen and not seen_add(x)]

    def abs_url(self, path):
        if self.is_leaf(path):
            return self.data["top_url"]+path
        else:
            return path

    def is_leaf(self, st):
        return not st.startswith(self.data["top_url"])

    def quit(self):
        logger.info("driver quit")
        self.driver.quit()
        return

    def screenshot(self, path):
        if self.headless == True:
            self.driver.save_screenshot(path)


if __name__ == "__main__":

    handler = StreamHandler()
    handler.setLevel(DEBUG)
    handler.setFormatter(Formatter(
        "%(asctime)s %(levelname)8s %(message)s"))
    logger.setLevel(DEBUG)
    logger.addHandler(handler)
    handler2 = FileHandler(filename="log/iidx_crawler.log")  # handler2はファイル出力
    handler2.setLevel(INFO)  # handler2はLevel.WARN以上
    handler2.setFormatter(Formatter(
        "%(asctime)s %(levelname)8s %(message)s"))
    logger.addHandler(handler2)
    logger.propagate = False

    args = sys.argv
    try:
        with open("./config/config.json", 'r') as f:
            data = json.loads(f.read())
            if args[1] in data:
                site = data[args[1]]
            else:
                print("ERROR target not found : "+str(args[1]))
                exit()
    except FileNotFoundError:
        print("ERROR file not found : ./config/config.json")
        exit()
    try:
        crawler = IIDXCrawler(site, args[1])
        crawler.login()
        # crawler.get_dani_id()
        # crawler.get_ranking_id(
        #     'arena', 'https://p.eagate.573.jp/game/2dx/27/p/ranking/arena/top_ranking.html?page=0&play_style=0&display=1')
        # print(crawler.get_player_data("29834714"))
        # crawler.get_all_player_data('ids/sample.json')
        with open("player_data/sample.json") as f:
            player_data = json.loads(f.read())
        # for i in range(1, 13):
        crawler.from_level(player_data, 12)
    except:
        import traceback
        traceback.print_exc()
    finally:
        page_width = crawler.driver.execute_script(
            'return document.body.scrollWidth')
        page_height = crawler.driver.execute_script(
            'return document.body.scrollHeight')
        crawler.driver.set_window_size(page_width, page_height)
        crawler.screenshot("img/finally.png")
        crawler.quit()

    # crawler.screenshot("img/logintest.png")
