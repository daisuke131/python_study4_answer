import math
from concurrent.futures.thread import ThreadPoolExecutor

import pandas as pd

from common.beutifulsoup import Soup
from common.csv import write_csv
from common.logger import set_logger

THREAD_COUNT = None  # スレッド数Noneで自動
SEARCH_QUERY_URL = "https://tenshoku.mynavi.jp/list/{query_word}"
PAGE_QUERY_URL = "https://tenshoku.mynavi.jp/list/{query_word}/" + "pg{page_count}"
log = set_logger()


class mainavi_scraping:
    def __init__(self, search_word: str) -> None:
        self.search_word = search_word
        self.query_word: str = self.formatting_query_word(self.search_word)
        self.page_count: int = self.fetch_page_count()
        self.df = pd.DataFrame()
        self.data_list: dict = []

    def formatting_query_word(self, search_word):
        # クエリパラメータの形に整形
        search_words = search_word.split()
        query_words = []
        for word in search_words:
            query_words.append("kw" + word)
        return "_".join(query_words)

    def fetch_page_count(self):
        # ページ数取得
        query_url = SEARCH_QUERY_URL.format(query_word=self.query_word)
        soup = Soup(query_url)
        data_count = int(
            soup.select_one(
                "body > div.wrapper > div:nth-child(5) > "
                + "div.result > div > p.result__num > em"
            ).get_text()
        )
        # 1ページ50件なので50で割って切り上げ
        return math.ceil(data_count / 50)

    def scraping(self):
        log.info("========スクレイピング開始========")
        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            for page_count in range(self.page_count):
                executor.submit(self.fetch_scraping_data, page_count + 1)
        # リストからdfに詰め直す
        for df_data in self.data_list:
            self.df = self.df.append(df_data, ignore_index=True)
        # ベージ数→インデックス（1ページ内の並び順）に降順でソート
        self.df = self.df.sort_values(["page", "index"])
        # 列削除
        self.df = self.df.drop(columns=["page", "index"])
        log.info("========スクレイピング終了========")

    def fetch_scraping_data(self, page_count):
        query_url = PAGE_QUERY_URL.format(
            query_word=self.query_word, page_count=page_count
        )
        soup = Soup(query_url)
        corps_list = soup.select(".cassetteRecruit__content")
        for data_count, corp in enumerate(corps_list):
            try:
                """
                中身が辞書型のリストを作る。
                list[辞書型, 辞書型, 辞書型]みたいな形。
                マルチスレッドで同時に同じdfに追加していくとうまく追加されないので、
                リストに詰め込んで、後からdfに詰め直す。
                """
                self.data_list.append(
                    {
                        "page": page_count,
                        "index": data_count,
                        "会社名": self.fetch_corp_name(corp),
                        "勤務地": self.find_table_target_word(corp, "勤務地"),
                        "給与": self.find_table_target_word(corp, "給与"),
                    }
                )
                log.info(f"{page_count}ページ目{data_count + 1}行目抽出完了")
            except Exception:
                log.info(f"{page_count}ページ目{data_count + 1}行目抽出失敗")

    def fetch_corp_name(self, soup):
        try:
            return soup.select_one("h3").get_text()
        except Exception:
            pass

    # テーブルからヘッダーで指定した内容を取得
    def find_table_target_word(self, soup, target):
        try:
            table_headers = soup.select(".tableCondition__head")
            table_bodies = soup.select(".tableCondition__body")
            for table_header, table_body in zip(table_headers, table_bodies):
                if table_header.get_text() == target:
                    return table_body.get_text()
        except Exception:
            pass

    def write_csv(self):
        # CSVに書き込み
        if len(self.df) > 0:
            file_name = self.query_word.replace("kw", "")
            if write_csv(file_name, self.df):
                log.info(f"{len(self.df)}件出力しました。")
            else:
                log.error("csv出力失敗しました。")
        else:
            log.info("検索結果は0件です。")


def main():
    # 検索ワード入力
    search_word = input("検索ワード>>")
    my_scraping = mainavi_scraping(search_word)
    my_scraping.scraping()
    my_scraping.write_csv()


if __name__ == "__main__":
    main()
