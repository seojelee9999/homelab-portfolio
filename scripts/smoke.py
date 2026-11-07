#!/usr/bin/env python3
"""Read-only HTTP checks after deployment; no credentials or document writes."""
import argparse
from html.parser import HTMLParser
from http.cookies import SimpleCookie
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Page(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.assets = []
        self.fields = set()
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.assets.append(attrs['href'])
        if tag == 'input' and attrs.get('name'):
            self.fields.add(attrs['name'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://akibaha.shop/portfolio')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    origin = urllib.parse.urlsplit(base)
    opener = urllib.request.build_opener(NoRedirect)

    def get(url):
        try:
            response = opener.open(urllib.request.Request(url, headers={'User-Agent': 'Portfolio-Verification/1'}), timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, response.headers, response.read().decode('utf-8', errors='replace')

    code, headers, _ = get(base)
    assert code == 302 and headers['Location'] in (base + '/', base.replace(origin.netloc, origin.netloc + ':443') + '/'), 'Missing HTTPS slash redirect'
    for path in ('/', '/books'):
        code, _, _ = get(base + path)
        assert code == 200, f'Anonymous reading failed: {path} ({code})'
    code, headers, body = get(base + '/login')
    assert code == 200
    page = Page(body)
    assert {'email', 'password', '_token'} <= page.fields, 'Login/CSRF form missing'
    session = None
    for value in headers.get_all('Set-Cookie', []):
        cookie = SimpleCookie()
        cookie.load(value)
        session = cookie.get('portfolio_session') or session
    assert session and session['path'] == origin.path and session['secure'] and session['httponly'], 'Session scope/security mismatch'
    assert page.assets, 'No application assets found'
    for asset in page.assets:
        url = urllib.parse.urljoin(base + '/login', asset)
        parsed = urllib.parse.urlsplit(url)
        assert (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc), f'Unexpected asset origin: {url}'
        assert parsed.path.startswith(origin.path + '/'), f'Asset escaped /portfolio: {url}'
        code, asset_headers, _ = get(url)
        assert code == 200 and 'text/html' not in asset_headers.get('Content-Type', ''), f'Broken asset: {url}'
    for path in ('/settings', '/create-book'):
        code, headers, _ = get(base + path)
        is_login = code in (301, 302, 303) and urllib.parse.urlsplit(headers.get('Location', '')).path == origin.path + '/login'
        assert code == 403 or is_login, f'Anonymous protected route unexpected: {path} ({code})'
    code, _, body = get(base + '/register')
    assert code in (302, 403, 404), f'Public registration unexpectedly available ({code})'
    print('PASS: public reading, login/CSRF form, scoped secure session, assets, protected routes, closed registration')


if __name__ == '__main__':
    main()
