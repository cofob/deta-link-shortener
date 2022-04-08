from uuid import uuid4
from traceback import format_exc
from flask import Flask, render_template, request, redirect
from deta import Deta
from typing import Union
from random import choices
from string import ascii_lowercase, digits
from time import time
from os import environ

app = Flask(__name__)
deta = Deta(environ["DETA_PROJECT_KEY"])
links = deta.Base("links")
views = deta.Base("views")
errors = deta.Base("errors")


def shorten(link: str, alias: Union[str, None]):
    if not alias.strip():
        alias = "".join(choices(ascii_lowercase + digits, k=5))

    if len(alias) > 10:
        raise ValueError("Alias too long.")

    if len(link) > 1024:
        raise ValueError("URL too long.")

    if not alias.isascii():
        raise ValueError("Alias must be ASCII.")
    if not link.isascii():
        raise ValueError("URL must be ASCII.")

    if alias in ["robots.txt", "favicon.ico", "sitemap.xml"]:
        raise ValueError("Pentester: detected")

    if links.get(alias) is not None:
        raise ValueError("Alias already exists.")

    links.put({"link": link, "key": alias})

    return alias


def get_link(alias: str):
    link = links.get(alias)["link"]
    views.put({"time": int(time()), "alias": alias})
    return link


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/", methods=["POST"])
def web_shorten():
    try:
        alias = shorten(request.form["link"], request.form.get("alias"))
        return render_template("index.html", shotened=True, alias=alias)
    except ValueError as e:
        return render_template("error.html", error=str(e))


@app.route("/api/shorten", methods=["GET"])
def api_shorten():
    try:
        alias = shorten(request.args["link"], request.args.get("alias"))
        return {"alias": alias}
    except ValueError as e:
        return {"error": str(e)}


@app.route("/<string:alias>")
def goto(alias):
    try:
        return redirect(get_link(alias))
    except TypeError:
        return render_template("error.html", error="Alias not found!")


@app.errorhandler(Exception)
def error_handler(e):
    error = errors.put(
        {"traceback": format_exc(), "time": int(time()), "key": str(uuid4())}
    )
    return render_template("error.html", error=str(e), code=error["key"])
