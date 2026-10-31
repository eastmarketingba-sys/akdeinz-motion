"""Builds the Work and Reels pages from content/projects.json.

Writes work/, reels/ and sitemap.xml, refreshes the marked blocks in index.html
and sets the ?v= number on every page. Never edit the generated files by hand:
change content/projects.json (or this script) and run

    python tools/build_pages.py
"""
import json
import re
import shutil
from datetime import date
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://akdeinzmotion.com"
BRAND = "Akdeinz Motion"
VERSION = 6  # raise when styles.css or main.js change, so visitors get the new files
DEFAULT_IMAGE = "/assets/og.png"

SECTIONS = {
    "work": {
        "path": "/work/", "label": "Work", "title": "Work", "kicker": "Selected work",
        "description": "Selected motion design work by Akdeinz Motion.",
    },
    "reel": {
        "path": "/reels/", "label": "Reels", "title": "Reels", "kicker": "Showreel and short pieces",
        "description": "Showreel and short motion pieces by Akdeinz Motion, built on the 60° axis.",
    },
}
FACTS = (("client", "Client"), ("year", "Year"), ("type", "Type"), ("time", "Time taken"), ("price", "Price"))
STORY = (("what", "What I did"), ("why", "Why I did it"), ("result", "Result"))
LISTS = (("deliverables", "Delivered"), ("tools", "Tools"))
STUDIES = {"rise", "shutter", "wave", "fold", "stack", "tunnel"}


def absolute(path):
    return path if path.startswith("http") else SITE + path


def page_path(p):
    return f"{SECTIONS[p['kind']]['path']}{p['slug']}/"


def is_ready(p):
    """A page goes into Google only once the real story is written."""
    return bool(p.get("what") and p.get("why"))


def json_ld(graph):
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + text.replace("<", "\\u003c") + "</script>"


def breadcrumbs(*trail):
    items = [{"@type": "ListItem", "position": i + 1, "name": name, "item": SITE + path}
             for i, (name, path) in enumerate(trail)]
    return {"@type": "BreadcrumbList", "itemListElement": items}


def head(title, description, path, *, image=DEFAULT_IMAGE, og_type="website", noindex=False, graph=()):
    url, img = SITE + path, absolute(image)
    card = "summary" if image == DEFAULT_IMAGE else "summary_large_image"
    robots = '\n  <meta name="robots" content="noindex, follow">' if noindex else ""
    ld = f"\n  {json_ld(list(graph))}" if graph else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}">{robots}
  <link rel="canonical" href="{url}">
  <meta name="theme-color" content="#000000">
  <meta property="og:site_name" content="{BRAND}">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:image" content="{e(img)}">
  <meta property="og:url" content="{url}">
  <meta property="og:type" content="{og_type}">
  <meta name="twitter:card" content="{card}">
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/og.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles.css?v={VERSION}">{ld}
</head>
<body>
"""


def nav(section=None, here=None, home=False, progress=False):
    def link(kind):
        s = SECTIONS[kind]
        current = f' aria-current="{here}"' if kind == section else ""
        return f'<a href="{s["path"]}"{current}>{s["label"]}</a>'

    up = " data-up" if home else ""
    bar = '\n    <span class="nav__progress" data-progress aria-hidden="true"></span>' if progress else ""
    return f"""  <header class="nav" data-nav>
    <a class="nav__logo" href="/"{up} aria-label="{BRAND} — home">
      <img src="/assets/logo-horizontal-white.svg" alt="{BRAND}" width="176" height="25">
    </a>
    <nav class="nav__links" aria-label="Primary">
      {link("reel")}
      {link("work")}
      <a href="/#contact" class="nav__cta"><span class="dot" aria-hidden="true"></span>Contact</a>
    </nav>{bar}
  </header>"""


def footer():
    return f"""  <footer class="footer">
    <img class="footer__mark" src="/assets/mark-white.svg" alt="" width="58" height="20">
    <nav class="footer__links" aria-label="Footer">
      <a class="caption" href="/reels/">Reels</a>
      <a class="caption" href="/work/">Work</a>
      <a class="caption" href="/#contact">Contact</a>
    </nav>
    <span class="caption">An East Marketing brand</span>
    <span class="caption">© <span data-year>{date.today().year}</span></span>
    <a class="caption footer__top" href="/" data-up>Back up</a>
  </footer>"""


def closing():
    return """  <section class="contact contact--cta" aria-labelledby="cta-title">
    <h2 id="cta-title" class="contact__title" data-split>Let’s make it move.</h2>
    <a class="send" href="/#contact">
      <span class="send__label">Contact</span>
      <span class="send__band" aria-hidden="true"></span>
    </a>
  </section>"""


def tail():
    return f"""
  <div class="cursor" data-cursor aria-hidden="true"><span data-cursor-label></span></div>

  <script src="/main.js?v={VERSION}" defer></script>
</body>
</html>
"""


def tile_media(p):
    still = p.get("image") or p.get("poster")
    if still:
        return f'<img src="{e(still)}" alt="{e(p.get("alt", ""))}" width="600" height="900" loading="lazy" decoding="async">'
    return f'<canvas class="study" data-study="{e(p["study"])}" aria-hidden="true"></canvas>'


def tile(p, i, level):
    layout = "tile--reel" if p["kind"] == "reel" else f"tile--{'abcdef'[i % 6]}"
    kind = f'<span class="tile__type">{e(p["type"])}</span>' if p.get("type") and p["kind"] == "work" else ""
    return f"""        <article class="tile {layout}" data-tile data-video="{e(p.get('video', ''))}">
          <a class="tile__link" href="{page_path(p)}" data-cursor-text="View">
            <div class="tile__media">{tile_media(p)}</div>
            <div class="tile__meta"><span class="tile__n">{i + 1:02d}</span><{level}>{e(p['title'])}</{level}>{kind}</div>
          </a>
        </article>"""


def reel_section(src, section_id, link):
    extra = '\n          <a class="reel__link" href="/reels/" aria-label="All reels" data-cursor-text="Reels"></a>' if link else ""
    return f"""    <section class="reel" id="{section_id}" data-reel aria-label="Showreel">
      <div class="reel__sticky">
        <div class="reel__window" data-reel-window>
          <canvas class="study" data-study="field" aria-hidden="true"></canvas>
          <video class="reel__video" data-reel-video data-src="{e(src)}" muted loop playsinline preload="none"></video>{extra}
          <button class="reel__sound" data-reel-sound type="button" hidden>
            <span data-sound-label>Sound on</span>
          </button>
        </div>
        <div class="reel__meta">
          <span class="caption">Showreel</span>
          <span class="caption reel__year">2026</span>
        </div>
      </div>
    </section>"""


def page_head(section, count):
    s = SECTIONS[section]
    return f"""    <header class="page-head">
      <canvas class="hero__field" data-field aria-hidden="true"></canvas>
      <div class="page-head__foot">
        <span class="caption">{s['kicker']}</span>
        <span class="caption">({count:02d})</span>
      </div>
      <h1 class="page-head__title" data-split>{s['title']}</h1>
      <div class="hero__band" aria-hidden="true"></div>
    </header>"""


def listing_page(section, items, showreel):
    s = SECTIONS[section]
    tiles = "\n".join(tile(p, i, "h2") for i, p in enumerate(items))
    if section == "reel":
        body = f"""{reel_section(showreel, "showreel", link=False)}

    <section class="work" aria-label="Short pieces">
      <div class="grid grid--reels">
{tiles}
      </div>
    </section>"""
    else:
        body = f"""    <section class="work work--list" aria-label="Projects">
      <div class="grid">
{tiles}
      </div>
    </section>"""

    graph = [
        {"@type": "CollectionPage", "name": f"{s['title']} — {BRAND}", "description": s["description"],
         "url": SITE + s["path"], "isPartOf": {"@id": f"{SITE}/#site"}, "inLanguage": "en"},
        breadcrumbs(("Home", "/"), (s["title"], s["path"])),
    ]
    return (
        head(f"{s['title']} — {BRAND}", s["description"], s["path"], graph=graph)
        + f"""
  <a class="skip" href="#main">Skip to content</a>

{nav(section, here="page")}

  <main id="main">
{page_head(section, len(items))}

{body}
  </main>

{closing()}

{footer()}
{tail()}"""
    )


def paragraphs(text):
    return "\n".join(f"<p>{e(part.strip())}</p>" for part in text.split("\n\n") if part.strip())


def case_media(p):
    if p.get("video"):
        poster = f' poster="{e(p["poster"])}"' if p.get("poster") else ""
        return f'<video src="{e(p["video"])}"{poster} controls playsinline preload="metadata"></video>'
    if p.get("image"):
        return f'<img src="{e(p["image"])}" alt="{e(p.get("alt", ""))}" width="600" height="900" decoding="async">'
    return f'<canvas class="study" data-study="{e(p["study"])}" role="img" aria-label="{e(p["title"])} animation"></canvas>'


def case_facts(p):
    rows = [f'<div><dt class="caption">{label}</dt><dd>{e(str(p[key]))}</dd></div>'
            for key, label in FACTS if p.get(key)]
    return f'<dl class="facts" data-rise>{"".join(rows)}</dl>' if rows else ""


def case_story(p):
    blocks = [f"""        <section class="block" data-rise>
          <h2 class="caption">{label}</h2>
          <div class="prose">{paragraphs(p[key])}</div>
        </section>""" for key, label in STORY if p.get(key)]
    for key, label in LISTS:
        if p.get(key):
            chips = "".join(f"<li>{e(v)}</li>" for v in p[key])
            blocks.append(f"""        <section class="block" data-rise>
          <h2 class="caption">{label}</h2>
          <ul class="chips">{chips}</ul>
        </section>""")
    return "\n".join(blocks)


def pager(items, i):
    if len(items) < 2:
        return ""
    before, after = items[i - 1], items[(i + 1) % len(items)]
    return f"""
    <nav class="pager" aria-label="More">
      <a class="pager__link" href="{page_path(before)}" rel="prev" data-prev>
        <span class="caption">Previous</span>
        <span class="pager__title">{e(before['title'])}</span>
      </a>
      <a class="pager__link" href="{page_path(after)}" rel="next" data-next>
        <span class="caption">Next</span>
        <span class="pager__title">{e(after['title'])}</span>
      </a>
    </nav>"""


def case_graph(p):
    url = SITE + page_path(p)
    s = SECTIONS[p["kind"]]
    description = p.get("summary", "")
    work = {
        "@type": "CreativeWork", "name": p["title"], "description": description, "url": url, "inLanguage": "en",
        "creator": {"@id": f"{SITE}/#org", "@type": "Organization", "name": BRAND, "url": f"{SITE}/"},
    }
    if p.get("year"):
        work["dateCreated"] = str(p["year"])
    if p.get("type"):
        work["genre"] = p["type"]
    if p.get("image") or p.get("poster"):
        work["image"] = absolute(p.get("poster") or p["image"])
    graph = [work, breadcrumbs(("Home", "/"), (s["title"], s["path"]), (p["title"], page_path(p)))]
    if p.get("video") and p.get("poster") and p.get("date"):  # all three are required by Google
        graph.append({"@type": "VideoObject", "name": p["title"], "description": description,
                      "contentUrl": absolute(p["video"]), "thumbnailUrl": absolute(p["poster"]), "uploadDate": p["date"]})
    return graph


def detail_page(p, items, i):
    s = SECTIONS[p["kind"]]
    path = page_path(p)
    summary = f'\n        <p class="case__summary">{e(p["summary"])}</p>' if p.get("summary") else ""
    description = p.get("summary") or s["description"]
    image = p.get("poster") or p.get("image") or DEFAULT_IMAGE
    return (
        head(f"{p['title']} — {BRAND}", description, path, image=image, og_type="article",
             noindex=not is_ready(p), graph=case_graph(p))
        + f"""
  <a class="skip" href="#main">Skip to content</a>

{nav(p["kind"], here="true", progress=True)}

  <main id="main">
    <article class="case case--{p['kind']}">
      <header class="case__head">
        <canvas class="hero__field" data-field aria-hidden="true"></canvas>
        <nav class="crumbs caption" aria-label="Breadcrumb">
          <a href="{s['path']}">{s['label']}</a><span aria-hidden="true">/</span><span aria-current="page">{e(p['title'])}</span>
        </nav>
        <h1 class="case__title">{e(p['title'])}</h1>{summary}
      </header>

      <div class="case__layout">
        <figure class="case__media">
          <div class="case__frame">{case_media(p)}</div>
        </figure>

        <div class="case__info">
        {case_facts(p)}
{case_story(p)}
          <p class="case__share">
            <button class="copy" type="button" data-copy="{SITE + path}"><span data-copy-label>Copy link</span></button>
          </p>
        </div>
      </div>
    </article>
{pager(items, i)}
  </main>

{closing()}

{footer()}
{tail()}"""
    )


def write(path, text):
    target = ROOT / path.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def fill(text, name, content):
    pattern = re.compile(rf"(<!-- build:{name}\b.*?-->).*?([ \t]*<!-- /build:{name} -->)", re.S)
    text, found = pattern.subn(lambda m: f"{m[1]}\n{content}\n{m[2]}", text)
    if found != 1:
        raise SystemExit(f"index.html: marker build:{name} not found")
    return text


def update_home(work, showreel):
    path = ROOT / "index.html"
    selected = work[:6]
    tiles = "\n".join(tile(p, i, "h3") for i, p in enumerate(selected))
    block = f"""      <header class="section-head">
        <h2 id="work-title" class="caption">Selected work</h2>
        <span class="caption section-head__count">({len(selected):02d})</span>
      </header>

      <div class="grid">
{tiles}
      </div>

      <a class="more" href="/work/">All work</a>"""
    text = path.read_text(encoding="utf-8")
    text = fill(text, "nav", nav(home=True))
    text = fill(text, "reel", reel_section(showreel, "reel", link=True))
    text = fill(text, "work", block)
    text = fill(text, "footer", footer())
    path.write_text(text, encoding="utf-8", newline="\n")


def bump_versions():
    for name in ("index.html", "thanks.html", "404.html"):
        path = ROOT / name
        text = re.sub(r"(styles\.css|main\.js)\?v=\d+", rf"\1?v={VERSION}", path.read_text(encoding="utf-8"))
        path.write_text(text, encoding="utf-8", newline="\n")


def write_sitemap(projects):
    today = date.today().isoformat()
    paths = ["/", "/work/", "/reels/"] + [page_path(p) for p in projects if is_ready(p)]
    urls = "\n".join(f"  <url>\n    <loc>{SITE}{path}</loc>\n    <lastmod>{today}</lastmod>\n  </url>" for path in paths)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8", newline="\n")
    return paths


def check(projects):
    slugs = [(p["kind"], p["slug"]) for p in projects]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("projects.json: two entries share a slug")
    for p in projects:
        if p["kind"] not in SECTIONS:
            raise SystemExit(f"{p['slug']}: kind must be work or reel")
        if not (p.get("video") or p.get("image") or p.get("poster") or p.get("study") in STUDIES):
            raise SystemExit(f"{p['slug']}: needs a video, image, poster or study")


def main():
    data = json.loads((ROOT / "content" / "projects.json").read_text(encoding="utf-8"))
    projects, showreel = data["projects"], data.get("showreel", "")
    check(projects)

    for folder in ("work", "reels"):  # both are fully generated, so removed jobs leave nothing behind
        shutil.rmtree(ROOT / folder, ignore_errors=True)

    groups = {kind: [p for p in projects if p["kind"] == kind] for kind in SECTIONS}
    for kind, items in groups.items():
        write(SECTIONS[kind]["path"], listing_page(kind, items, showreel))
        for i, p in enumerate(items):
            write(page_path(p), detail_page(p, items, i))

    update_home(groups["work"], showreel)
    bump_versions()
    paths = write_sitemap(projects)
    hidden = sum(not is_ready(p) for p in projects)
    print(f"Built {len(projects)} detail pages. In the sitemap: {len(paths)}. Waiting for details: {hidden}.")


if __name__ == "__main__":
    main()
