import requests
from bs4 import BeautifulSoup


class Soup:
    def __init__(self, url: str) -> None:
        self.soup = self.fetch_soup(url)

    def fetch_soup(self, url: str):
        resp = requests.get(url)
        return BeautifulSoup(resp.text, "html.parser")

    def select(self, selector: str):
        return self.soup.select(selector)

    def select_one(self, selector: str):
        return self.soup.select_one(selector)
