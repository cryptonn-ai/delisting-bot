from time import sleep
from datetime import datetime
import requests
import time
import re
from collections import deque


class BinanceDelistingTracker:
    CATALOG_ID = 161
    API_URL = 'https://www.binance.com/bapi/apex/v1/public/apex/cms/article/list/query'
    HEADERS = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15',
        'lang': 'en',
        'Referer': f"https://www.binance.com/en/support/announcement/list/{CATALOG_ID}",
        'Accept-Encoding': 'gzip, deflate, br',
        'clienttype': 'web'
    }
    DEQUE_LIMIT = 30

    def __init__(self):
        self.__title_pattern = re.compile(
            r"^Binance Will Delist ([A-Z0-9]+(?:,\s*[A-Z0-9]+)*(?:\sand\s[A-Z0-9]+)?) on (\d{4}-\d{2}-\d{2})$"
        )
        self.__seen_tokens = deque([], maxlen=self.DEQUE_LIMIT * 10)
        self.__seen_articles = deque([], maxlen=self.DEQUE_LIMIT)
        self.__pass_time_delta = 120000  # 120 sec
        self.__pass_time_delta = 7426192641  # test

    def __fetch_page(self, page: int = 1, size: int = 20, retry: int = 1) -> list | None:
        size = min(20, size)
        page = max(1, page)

        payload = {
            "type": 1,
            "catalogId": self.CATALOG_ID,
            "pageNo": page,
            "pageSize": size
        }

        response = None
        try:
            response = requests.get(self.API_URL, params=payload, headers=self.HEADERS, timeout=(5, 10))

            if response.status_code == 200:
                return response.json()['data']['catalogs'][0]['articles'][::-1]
            else:
                raise Exception(response.json())
        except Exception as e:
            log_data = [
                f"URL: {self.API_URL}",
                f"Request body: {payload}",
            ]
            if response is not None:
                log_data.extend([
                    f"Request headers: {response.request.headers}",
                    f"Status code: {response.status_code}",
                    f"Response headers: {response.headers}",
                    f"Response body: {response.text}",
                ])

            print('Ошибка запроса', e)
            print(log_data)

        if retry < 4:
            sleep(10)
            return self.__fetch_page(page=page, size=size, retry=retry + 1)
        return None

    def __parse_title(self, title: str) -> tuple:
        match = self.__title_pattern.match(title.strip())
        tokens_list = None
        delisting_date = None
        if match:
            tokens, delisting_date = match.groups()
            tokens_list = [token.strip() for token in re.split(r',\s*|\sand\s', tokens)]
            print(f"✅ Tokens to delist: {tokens_list} | On date: {delisting_date}")

        return tokens_list, delisting_date

    def __handle_article(self, article: dict) -> dict | None:
        title = article['title']
        tokens_list, delisting_date = self.__parse_title(title=title)

        if tokens_list is not None and delisting_date is not None:
            _id = article['id']
            article_date = article['releaseDate']
            return {
                "id": _id,
                "article_date": article_date,
                "tokens": tokens_list,
                "delisting_date": delisting_date,
            }

        return None

    # pages max 10
    def __collect_delisting_articles(self, pages: int = 3) -> None:
        pages = min(10, pages)

        for page in range(pages, 0, -1):
            articles = self.__fetch_page(page=page)
            if page > 1:
                sleep(5)

            if articles is not None:
                print('Page', page, 'fetched successfully')
                for article in articles:
                    delisting_article = self.__handle_article(article=article)
                    if delisting_article is not None:
                        self.__seen_articles.append(delisting_article)

    def run(self):
        self.__collect_delisting_articles(pages=10)

        for article in self.__seen_articles:
            for token in article['tokens']:
                if token in self.__seen_tokens:
                    continue
                self.__seen_tokens.append(token)

        while True:
            sleep(20)

            print("new cycle", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            last_article = self.__seen_articles[-1]
            current_time = int(time.time() * 1000)

            articles = self.__fetch_page(page=1)
            if articles is not None:
                for article in articles:
                    if article['releaseDate'] <= last_article['article_date']:
                        continue

                    delisting_article = self.__handle_article(article=article)
                    if delisting_article is None:
                        continue
                    self.__seen_articles.append(delisting_article)

                    new_tokens = []
                    for token in delisting_article['tokens']:
                        if token in self.__seen_tokens:
                            print("ALERT", token, "is in __seen_tokens")
                            continue
                        self.__seen_tokens.append(token)
                        new_tokens.append(token)

                    print(current_time, 'current_time')
                    print(delisting_article['article_date'], 'delisting_article')

                    print('delta', abs(current_time - delisting_article['article_date']), self.__pass_time_delta)
                    if abs(current_time - delisting_article['article_date']) <= self.__pass_time_delta:
                        print("Call event for tokens", new_tokens)
                        pass  # TODO call event
