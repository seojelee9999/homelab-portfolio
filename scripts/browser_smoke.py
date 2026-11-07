#!/usr/bin/env python3
"""Browser QA for the work-note dashboard, optionally with login JSON on stdin."""
import argparse
import base64
import json
from pathlib import Path
import struct
import sys
import termios
import urllib.parse
import zlib

from playwright.sync_api import sync_playwright


def image_fixture():
    """Tiny valid PNG with editable diagrams.net source, only for upload testing."""
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    drawing = '<mxfile><diagram name="Test"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel></diagram></mxfile>'
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 2, 2, 8, 2, 0, 0, 0))
            + chunk(b'tEXt', b'mxfile\x00' + urllib.parse.quote(drawing).encode())
            + chunk(b'IDAT', zlib.compress((b'\x00' + b'\x35\x68\xd4' * 2) * 2)) + chunk(b'IEND', b''))


def credentials_from_stdin():
    previous = None
    if sys.stdin.isatty():
        previous = termios.tcgetattr(sys.stdin)
        hidden = termios.tcgetattr(sys.stdin)
        hidden[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, hidden)
    print('Ready for login JSON on stdin (input is hidden).', flush=True)
    try:
        return json.loads(sys.stdin.readline())
    finally:
        if previous:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://akibaha.shop/portfolio')
    parser.add_argument('--authenticated', action='store_true')
    parser.add_argument('--screenshots', type=Path, default=Path('/tmp/portfolio-ui'))
    args = parser.parse_args()
    login = credentials_from_stdin() if args.authenticated else None
    base = args.base_url.rstrip('/')
    args.screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1100}, locale='ko-KR')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = page.goto(base + '/', wait_until='networkidle')
        assert response.status == 200
        page.locator('[data-notes-dashboard]').wait_for()
        assert page.locator('.notes-topic').count() > 0
        assert page.locator('.notes-template-list a').count() == 4
        assert page.locator('.notes-write-menu').count() == 0, 'Guest sees write actions'
        assert page.locator('text=최근에 읽은 책').count() == 0
        assert page.locator('.notes-hero').evaluate("e => getComputedStyle(e).display") == 'grid', 'Theme stylesheet missing'
        for width in (1440, 390, 320):
            page.set_viewport_size({'width': width, 'height': 1000 if width == 1440 else 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow at {width}px'
            page.screenshot(path=str(args.screenshots / f'home-{width}.png'), full_page=True)
        page.set_viewport_size({'width': 1440, 'height': 1100})
        page.evaluate("document.documentElement.classList.add('dark-mode')")
        page.screenshot(path=str(args.screenshots / 'home-dark.png'), full_page=True)
        page.evaluate("document.documentElement.classList.remove('dark-mode')")
        print('PASS: public dashboard, theme assets, templates, 1440/390/320px layouts and dark styles.', flush=True)
        if login:
            page.goto(base + '/login')
            page.locator('input[name=email]').fill(login['email'])
            page.locator('input[name=password]').fill(login['password'])
            page.locator('button[type=submit]').click()
            login.clear()
            page.wait_for_url(base + '/')
            page.locator('.notes-write-menu').first.locator('summary').click()
            assert page.locator('.notes-write-options a:visible').count() >= 4
            assert page.locator('.notes-write-options a').first.get_attribute('href').endswith('/create-page')
            page.screenshot(path=str(args.screenshots / 'home-author.png'), full_page=True)
            # Existing template editor: verify controls without creating/changing a note.
            template = page.locator('.notes-template-list a').first.get_attribute('href')
            page.goto(template + '/edit', wait_until='networkidle')
            assert page.locator('textarea[name=markdown]').count() == 1
            assert page.locator('button[data-action=insertImage]').is_visible()
            assert page.locator('button[data-action=insertDrawing]').is_visible()
            assert 'embed.diagrams.net' in page.locator('[drawio-url]').get_attribute('drawio-url')
            page.screenshot(path=str(args.screenshots / 'editor.png'), full_page=True)
            csrf = page.locator('meta[name=token]').get_attribute('content')
            page_id = page.locator('#markdown-editor').get_attribute('option:markdown-editor:page-id')
            headers = {'X-CSRF-TOKEN': csrf, 'Accept': 'application/json'}
            png = image_fixture()
            created = []
            try:
                gallery = context.request.post(base + '/images/gallery', headers=headers, multipart={
                    'uploaded_to': page_id,
                    'file': {'name': 'portfolio-ui-check.png', 'mimeType': 'image/png', 'buffer': png},
                })
                assert gallery.ok, f'Image upload failed ({gallery.status})'
                uploaded = gallery.json()
                assert isinstance(uploaded.get('id'), int), 'Upload did not return an image'
                created.append(uploaded['id'])
                assert context.request.get(uploaded['url']).body().startswith(b'\x89PNG')
                drawing = context.request.post(base + '/images/drawio', headers=headers, form={
                    'uploaded_to': page_id, 'image': 'data:image/png;base64,' + base64.b64encode(png).decode(),
                })
                assert drawing.ok, f'Drawing save failed ({drawing.status})'
                saved = drawing.json()
                assert isinstance(saved.get('id'), int), 'Drawing did not return an image'
                created.append(saved['id'])
                drawing_source = context.request.get(base + '/images/drawio/base64/' + str(saved['id']))
                assert b'mxfile' in base64.b64decode(drawing_source.json()['content'])
            finally:
                for image_id in created:
                    deleted = context.request.delete(base + '/images/' + str(image_id), headers=headers)
                    assert deleted.ok, f'Test image cleanup required: {image_id}'
            print('PASS: login, author shortcuts, Markdown editor, image upload/read/delete and editable drawing save/read/delete. No note content changed.', flush=True)
        assert not errors, f'Browser JavaScript errors: {errors}'
        browser.close()
    print('Screenshots:', args.screenshots)


if __name__ == '__main__':
    main()
