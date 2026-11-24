#!/usr/bin/env python3
"""
VelaOra site builder.  Run from the repo root:   python3 tools/build.py

What it does
  1. Builds the new pages from tools/pages/*.html (a small header block + body)
     into full pages at the repo root (index.html, menopause.html, quiz.html ...).
  2. Puts the shared header + footer (partials/) into every other page,
     replacing each page's old nav/footer the first time, then just refreshing
     between the <!--VO:HEADER--> / <!--VO:FOOTER--> markers after that.
  3. Fills article lists between <!--VO:ARTICLES ...--> markers from
     tools/articles.json  (add a new article there and re-run).
  4. Rewrites sitemap.xml.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
HEADER = (ROOT / 'partials/header.html').read_text()
FOOTER = (ROOT / 'partials/footer.html').read_text()
ARTICLES = json.loads((TOOLS / 'articles.json').read_text())
SITE = 'https://velaora.co.nz'
SKIP = {'restora.html', 'velaora-article-13-fertility.html', 'velaora-article-bloating.html', 'velaora-article-plastics.html'}
CSS_LINK = '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/vo.css"><!--vo-css-->'

TOPIC_NAMES = {'perimenopause': 'Perimenopause', 'menopause': 'Menopause', 'fertility': 'Fertility', 'anxiety': 'Anxiety & Stress',
               'sleep': 'Brain & Sleep', 'nutrition': 'Nutrition', 'supplements': 'Supplements', 'community': 'Community'}

esc = lambda s: html.escape(s, quote=True)


def card(a, lazy=True):
    mins = f'<span>{a["mins"]} min read</span>' if a.get('mins') else ''
    return (f'<a class="vo-card" href="/{a["slug"]}" data-topics="{" ".join(a["topics"])}" data-text="{esc((a["title"]+" "+a["blurb"]+" "+a["tag"]).lower())}">'
            f'<img src="{esc(a["img"])}" alt="{esc(a["alt"])}"{" loading=\"lazy\"" if lazy else ""} width="600" height="380">'
            f'<div class="vo-card-body"><div class="vo-card-meta"><span>{esc(a["tag"])}</span>{mins}</div>'
            f'<h3>{esc(a["title"])}</h3><p>{esc(a["blurb"])}</p><span class="vo-card-link">Read article →</span></div></a>')


def article_block(spec):
    """spec like 'latest 6' or 'topic perimenopause 6' or 'all'"""
    parts = spec.split()
    if parts[0] == 'all':
        items = ARTICLES
    elif parts[0] == 'latest':
        items = ARTICLES[:int(parts[1])]
    elif parts[0] == 'topic':
        items = [a for a in ARTICLES if parts[1] in a['topics']][:int(parts[2]) if len(parts) > 2 else 99]
    else:
        raise ValueError(spec)
    return '<div class="vo-grid">' + ''.join(card(a) for a in items) + '</div>'


def fill_articles(s):
    return re.sub(r'(<!--VO:ARTICLES ([^>]*?)-->).*?(<!--/VO:ARTICLES-->)',
                  lambda m: m.group(1) + article_block(m.group(2)) + m.group(3), s, flags=re.S)


def matching_close(s, start, tag):
    """index just after the tag that closes the element opening at s[start]"""
    pat = re.compile(rf'<{tag}\b|</{tag}\s*>', re.I)
    depth = 0
    for m in pat.finditer(s, start):
        depth += 1 if not m.group(0).startswith('</') else -1
        if depth == 0:
            return m.end()
    raise ValueError(f'unclosed <{tag}>')


ANCHOR_MAP = {'perimenopause': '/perimenopause', 'menopause': '/menopause', 'fertility': '/fertility', 'anxiety': '/anxiety',
              'separation': '/separation', 'articles': '/articles', 'wellness-club': '/wellness-club', 'wellness': '/wellness-club',
              'about': '/about', 'contact': '/about#contact', 'news': '/resources', 'resources': '/resources',
              'subscribe': '#vo-join', 'home': '/', 'pillars': '/#topics'}


def fix_links(s):
    """Old one-page links (index.html#wellness, /#articles, fertility.html) -> new pages."""
    s = re.sub(r'href="(?:index\.html|/|https://velaora\.co\.nz/?)#([\w-]+)"',
               lambda m: f'href="{ANCHOR_MAP.get(m.group(1), "/#" + m.group(1))}"', s)
    s = s.replace('href="perimenopause.html#menopause"', 'href="/menopause"')
    s = re.sub(r'href="(perimenopause|menopause|fertility|anxiety|articles|privacy|terms)\.html(#[\w-]+)?"',
               lambda m: f'href="/{m.group(1)}{m.group(2) or ""}"', s)
    return s.replace('href="index.html"', 'href="/"')


def apply_layout(s, name):
    s = fix_links(s)
    if '<!--vo-css-->' in s and 'favicon.svg' not in s:
        s = s.replace('<link rel="stylesheet" href="/assets/vo.css"><!--vo-css-->', CSS_LINK, 1)
    if '<!--vo-css-->' not in s:
        s = s.replace('</head>', CSS_LINK + '\n</head>', 1)
    hdr = '<!--VO:HEADER-->\n' + HEADER + '<!--/VO:HEADER-->'
    ftr = '<!--VO:FOOTER-->\n' + FOOTER + '<!--/VO:FOOTER-->'
    if '<!--VO:HEADER-->' in s:
        s = re.sub(r'<!--VO:HEADER-->.*?<!--/VO:HEADER-->', lambda m: hdr, s, flags=re.S)
    else:
        i = s.find('<nav')
        if i < 0:
            raise ValueError(f'{name}: no <nav>')
        j = matching_close(s, i, 'nav')
        m = re.match(r'\s*(<!--[^>]*-->\s*)*<div[^>]*mobile-menu[^>]*>', s[j:])
        if m:
            k = j + m.end() - len(re.search(r'<div[^>]*>$', m.group(0)).group(0))
            j = matching_close(s, k, 'div')
        s = s[:i] + hdr + s[j:]
    if '<!--VO:FOOTER-->' in s:
        s = re.sub(r'<!--VO:FOOTER-->.*?<!--/VO:FOOTER-->', lambda m: ftr, s, flags=re.S)
    else:
        i = s.find('<footer')
        if i < 0:
            s = s.replace('</body>', ftr + '\n</body>', 1)
        else:
            j = matching_close(s, i, 'footer')
            s = s[:i] + ftr + s[j:]
    if 'id="main"' not in s:
        s = s.replace('<!--/VO:HEADER-->', '<!--/VO:HEADER-->\n<span id="main"></span>', 1)
    return fill_articles(s)


HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="VelaOra">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{image}">
<meta property="og:locale" content="en_NZ">
<meta name="twitter:card" content="summary_large_image">
{extra_head}
<script async src="https://www.googletagmanager.com/gtag/js?id=G-WS37E8T1E5"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-WS37E8T1E5');</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Nunito:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/vo-base.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/vo.css"><!--vo-css-->
</head>
<body>
'''


def build_page(src):
    text = src.read_text()
    meta, body = text.split('\n---\n', 1)
    m = dict(l.split(':', 1) for l in meta.strip().splitlines() if ':' in l)
    m = {k.strip(): v.strip() for k, v in m.items()}
    slug = src.stem
    url = SITE + ('/' if slug == 'index' else '/' + slug)
    extra = (TOOLS / 'pages' / m['head']).read_text() if m.get('head') else ''
    page = HEAD.format(title=esc(m['title']), desc=esc(m['description']), url=url,
                       image=m.get('image', SITE + '/og-image.png'), extra_head=extra)
    page += '<!--VO:HEADER-->\n<!--/VO:HEADER-->\n<main id="main">\n' + body.strip() + '\n</main>\n<!--VO:FOOTER-->\n<!--/VO:FOOTER-->\n</body>\n</html>\n'
    out = ROOT / (slug + '.html')
    out.write_text(apply_layout(page, out.name))
    return out.name


def sitemap(pages):
    core = ['index', 'perimenopause', 'menopause', 'fertility', 'anxiety', 'separation', 'articles', 'quiz', 'gp-guide',
            'picks', 'wellness-club', 'about', 'resources']
    rows = []
    for p in core:
        loc = SITE + ('/' if p == 'index' else '/' + p)
        rows.append(f'  <url><loc>{loc}</loc><lastmod>2026-11-25</lastmod><priority>{"1.0" if p == "index" else "0.8"}</priority></url>')
    for a in ARTICLES:
        rows.append(f'  <url><loc>{SITE}/{a["slug"]}</loc><lastmod>{a["date"]}</lastmod><priority>0.7</priority></url>')
    for p in ['privacy', 'terms']:
        rows.append(f'  <url><loc>{SITE}/{p}</loc><priority>0.2</priority></url>')
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + '\n'.join(rows) + '\n</urlset>\n')


def main():
    built = [build_page(p) for p in sorted((TOOLS / 'pages').glob('*.html'))]
    for f in sorted(ROOT.glob('*.html')):
        if f.name in built or f.name in SKIP:
            continue
        s = f.read_text()
        new = apply_layout(s, f.name)
        if new != s:
            f.write_text(new)
    sitemap(built)
    print('built:', ', '.join(built))


if __name__ == '__main__':
    main()
