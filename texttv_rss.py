#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.request import urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from rfeed import Item, Feed
from datetime import datetime
import re
import argparse

class TextTVParser:
    def __init__(self, source, index_pages, categories, max_paragraphs):
        self.source = source
        self.index_pages = index_pages
        self.categories = categories
        self.max_paragraphs = max_paragraphs

    def load_pages(self):
        page_cache = {}
        self.load_cached_pages(page_cache, self.index_pages)
        article_pages = self.parse_page_links(page_cache, self.index_pages)
        self.load_cached_pages(page_cache, article_pages)

        pages = [self.parse_page(page) for page in page_cache.values()]
        return [page for page in pages if page]

    def load_cached_pages(self, page_cache, pages):
        for page in pages:
            if not page in page_cache:
                try:
                    url = self.source + "/" + page
                    data = urlopen(url).read()
                    page_cache[page] = data
                except HTTPError as e:
                    print("Could not load " + url + ", got: " + str(e))

    def parse_page_links(self, page_cache, index_pages):
        article_pages = []

        for page in index_pages:
            soup = BeautifulSoup(page_cache[page], 'html.parser')
            for area in soup.find_all("area"):
                article_pages.append(area['href'])

        return article_pages

    def parse_page(self, page):
        soup = BeautifulSoup(page, 'html.parser')
        text = soup.find("div", {"class" : re.compile("^Content")}).text

        lines = text.splitlines(True)

        if not self.is_valid_page(lines):
            return None

        
        title = lines[5].strip()
        paragraphs = self.make_paragraphs(lines[6:])[0:self.max_paragraphs]
        description = "\n".join(["<p>{0}</p>\n\n".format(paragraph) for paragraph in paragraphs])
        link = soup.find("link", { "rel" : "canonical"})['href']
        
        return { 'title': title, 'description': description, 'link': link }


    def is_valid_page(self, lines):
        if len(lines) == 1:
            return False
        for category in self.categories:
            if lines[3].strip().startswith(category + " PUBLICERAD"):
                return True
        return False

    def make_paragraphs(self, lines):
        current_paragraph = None
        paragraphs = []

        for line in lines:
            line = line.strip()
            if not current_paragraph and line:
                if line.endswith("-"):
                    current_paragraph = line[:-1]
                else:
                    current_paragraph = line + " "
            elif current_paragraph and line:
                if line.endswith("-"):
                    current_paragraph += line[:-1]
                else:
                    current_paragraph += line + " "
            elif current_paragraph and not line:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = None

        return paragraphs

    def to_item(self, page):
        return Item(title = page["title"], description = page["description"], pubDate=datetime.now(), link = page["link"])

    def to_feed(self, pages):
        feed = Feed(title = "Nyheter från Text-TV", description = "RSS-flöde av nyheter från SVTs Text-TV", link = self.source)
        feed.items = [self.to_item(page) for page in pages]
        return feed.rss()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parses SVT text tv news and creates a RSS-feed from it")
    parser.add_argument("--source", required=False, default="https://www.svt.se/text-tv", help="The source page to fetch data from")
    parser.add_argument("--index-pages", required=False, nargs="*", default=["101", "102", "103", "104", "105"], help="The index pages which contains a list of pages with the articles")
    parser.add_argument("--categories", required=False, nargs="*", default=["INRIKES","UTRIKES"], help="The categories of news to fetch (e.g. INRIKES, FOTBOLL, SKIDOR)")
    parser.add_argument("--max-paragraphs", required=False, default=1, type=int, help="The amount of paragraphs that max should be included")

    args = parser.parse_args()
    texttv = TextTVParser(args.source, args.index_pages, args.categories, args.max_paragraphs)
    print(texttv.to_feed(texttv.load_pages()))
