import locale
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown
from pydantic import BaseModel, root_validator, validator
from slugify import slugify

LOCALE = "pt_BR.utf8"
TIMEZONE = "America/Recife"
DATE_FORMAT = "%d/%m/%Y"
RELATIVE_PATH = "articles"
OUTPUT = "data/data.json"

p = Path(__file__).parent / RELATIVE_PATH
locale.setlocale(locale.LC_ALL, LOCALE)


class Article(BaseModel):
    id: str
    title: str
    subtitle: str
    abstract: str
    text: str
    toc: str
    date: datetime
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
        date = values.get("date")[0]
        date = datetime.strptime(date, DATE_FORMAT)
        values["date"] = date
        values["dates"] = {"year": date.year, "month": date.month, "day": date.day}
        values["id"] = f"{date.year}-{date.month}-{date.day}-{slugify(title)}"
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

        breakpoint()
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
