from requests_html import *
if __name__ == '__main__':
    url = "http://localhost:3000/query"
    session = HTMLSession()
    r = session.get(url)
    html:HTML = r.html
    html.render()
    print(html.text)