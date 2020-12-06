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
    def __init__(self, source, categories, max_paragraphs):
        self.source = source
        self.categories = categories
        self.max_paragraphs = max_paragraphs

    def load_pages(self):
        data = urlopen(self.source).read()
        soup = BeautifulSoup(data, 'html.parser')
        pages = soup.findAll("pre", { "class" : "root" })

        return [page for page in [self.parse_page(p) for p in pages] if page]

    def parse_page(self, page):
        elem = page.find("span", { "class" : "W bgB"})
        if not elem:
            return None

        category = elem.text.strip().upper()
        category = re.compile("^[A-Z]*").findall(category)[0]

        if category in self.categories:
            title_elems = page.findAll("span", {"class" : "DH"})
            
            avoid_lines = page.findAll("span", {"class" : "bgB"})

            lines = page.findAll("span", {"class" : re.compile("[Y|W]")})

            # Remove all lines before and including title
            lines = lines[lines.index(title_elems[-1]) + 1:]

            # Remove unwanted lines
            lines = [line for line in lines if line not in avoid_lines]

            # Remove empty lines
            lines = [line for line in lines if line.get_text().strip()]

            paragraphs = self.make_paragraphs(lines)  

            title = " ".join([elem.get_text().strip() for elem in title_elems]).strip()

            paragraphs = paragraphs[0:self.max_paragraphs]

            description = "\n".join(["<p>{0}</p>\n\n".format(paragraph) for paragraph in paragraphs])

            return { 'title': title, 'description': description }
        else:
            return None

    def make_paragraphs(self, lines):
        current_class = None
        current_paragraph = None
        paragraphs = []

        for line in lines:
            c = line['class']
            text = line.get_text().strip()
            if not current_class or c != current_class:
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                current_class = c
                current_paragraph = text
            else:
                if not current_paragraph.endswith("-"):
                    current_paragraph = current_paragraph + " " + text
                else:
                    current_paragraph = current_paragraph[:-1] + text
        
        if current_paragraph:
            paragraphs.append(current_paragraph)   

        return paragraphs

    def to_item(self, page):
        return Item(title = page["title"], description = page["description"], pubDate=datetime.now(), link = self.source)

    def to_feed(self, pages):
        feed = Feed(title = "Nyheter från Text-TV", description = "RSS-flöde av nyheter från SVTs Text-TV", link = self.source)
        feed.items = [self.to_item(page) for page in unique_dict_list(pages)]
        return feed.rss()


def unique_dict_list(input):
    return list(map(dict, set(tuple(sorted(item.items())) for item in input)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parses SVT text tv news and creates a RSS-feed from it")
    parser.add_argument("--source", required=False, default="https://www.svt.se/svttext/web/pages/188.html", help="The source page to fetch data from")
    parser.add_argument("--categories", required=False, nargs="*", default=["INRIKES","UTRIKES"], help="The categories of news to fetch (e.g. INRIKES, FOTBOLL, SKIDOR)")
    parser.add_argument("--max-paragraphs", required=False, default=1, type=int, help="The amount of paragraphs that max should be included")

    args = parser.parse_args()
    texttv = TextTVParser(args.source, args.categories, args.max_paragraphs)
    print(texttv.to_feed(texttv.load_pages()))
