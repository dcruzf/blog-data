import locale
from datetime import datetime
from pathlib import Path
import os
from typing import Optional

import markdown
from pydantic import BaseModel, root_validator, validator
from slugify import slugify

LOCALE = os.getenv("LOCALE", "pt_BR.utf8")
TIMEZONE = os.getenv("TIMEZONE", "America/Recife")
DATE_FORMAT = os.getenv("DATE_FORMAT", "%d/%m/%Y")
RELATIVE_PATH = os.getenv("RELATIVE_PATH", "articles")
OUTPUT = os.getenv("OUTPUT", "data/data.json")

p = Path(__file__).parent / RELATIVE_PATH
locale.setlocale(locale.LC_ALL, LOCALE)


class Article(BaseModel):
    id: str
    title: str
    subtitle: str
    abstract: str
    text: str
    toc: str
    date: Optional[datetime]
    author: str
    tags: set[str]

    @validator("title", "subtitle", "abstract", "author", pre=True)
    def remove_list(cls, v):
        return v[0]

    @validator("tags", pre=True)
    def tag_list(cls, v):
        return v[0].split()

    @root_validator(pre=True)
    def define_id(cls, values):
        title = values.get("title")[0]
        date = values.get("date")[0] or None
        if date is not None:
            date = datetime.strptime(date, DATE_FORMAT)
            values["dates"] = {"year": date.year, "month": date.month, "day": date.day}
            values["id"] = f"{date.year}-{date.month}-{date.day}-{slugify(title)}"
        else:
            values["dates"] = {}
            values["id"] = f"{slugify(title)}"

        values["date"] = date

        return values


class Data(BaseModel):
    tags: list[str]
    history: list[dict]
    about: Article
    articles: list[Article]

    @root_validator(pre=True)
    def feed_data(cls, values):
        articles = values.get("articles")
        tags = set()
        dates = {}
        for article in articles:
            tags |= set(article.tags)
            dates[article.date.year] = dates.get(article.date.year, set())
            dates[article.date.year].add(article.date.month)

        history = [{"year": k, "months": v} for k, v in dates.items()]
        values["tags"] = tags
        values["history"] = history
        return values


md = markdown.Markdown(extensions=["extra", "meta", "toc"])


def get_articles(files=None):
    files = files or list(p.glob("*.md"))
    articles = []
    for f in files:
        html_res = md.convert(f.read_text())
        article = md.Meta.copy()
        article["text"] = html_res
        article["toc"] = md.toc
        articles.append(Article.parse_obj(article))
    return articles


def get_about():
    return get_articles([p.parent / "about.md"])[0]


data = Data(about=get_about(), articles=get_articles())
with open(OUTPUT, "w") as f:
    f.write(data.json())
