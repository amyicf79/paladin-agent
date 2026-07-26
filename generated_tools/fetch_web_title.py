def fetch_web_title(url: str) -> str:
    """从 URL 提取标题（自动生成，零依赖）"""
    from urllib.request import urlopen
    from html.parser import HTMLParser

    class _TitleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_title = False
            self._title = ""

        def handle_starttag(self, tag, attrs):
            if tag == "title":
                self._in_title = True

        def handle_endtag(self, tag):
            if tag == "title":
                self._in_title = False

        def handle_data(self, data):
            if self._in_title:
                self._title += data

    try:
        resp = urlopen(url, timeout=5)
        html = resp.read().decode("utf-8", errors="ignore")
        parser = _TitleParser()
        parser.feed(html)
        return parser._title.strip() or "无标题"
    except Exception as e:
        return f"提取失败: {e}"
