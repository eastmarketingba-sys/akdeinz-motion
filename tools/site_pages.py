"""Pricing, Guides, About, llms.txt and robots.txt. Called by build_pages.py; run that, not this file.

Sources: content/site.json, content/pricing.json, content/guides/*.json.
Never edit the generated pages by hand: change the sources (or this script) and run
    python tools/build_pages.py
"""
import json
import re
import shutil
from html import escape as e

bp = None  # the build_pages module, set by init()
VERIFY_COUNT = 0
PITCH = "Your time is valuable. Let me take care of it."
AREA = [{"@type": "Country", "name": "Belgium"}, {"@type": "Place", "name": "European Union"},
        {"@type": "Country", "name": "United States"}]
CRAWLERS = ("GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
            "PerplexityBot", "Google-Extended", "Bingbot", "Googlebot")


def init(module):
    global bp
    bp = module


def load(name):
    return json.loads((bp.ROOT / "content" / name).read_text(encoding="utf-8"))


# ---------- small helpers ----------

def inline(text):
    """Escape, then allow [text](/path/), **bold** and the [VERIFY] flag."""
    t = e(text)
    t = re.sub(r"\[([^\]]+)\]\((/[^)\s]*)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return t.replace("[VERIFY]", '<span class="verify" title="Not yet verified">[VERIFY]</span>')


def eur(n):
    return f"€{n:,.0f}" if float(n).is_integer() else f"€{n:,.2f}"


def table(headers, rows, label, ids=None, wide=False):
    head = "".join(f'<th scope="col">{inline(h)}</th>' for h in headers)
    body = []
    for i, row in enumerate(rows):
        rid = f' id="{ids[i]}"' if ids and ids[i] else ""
        cells = f'<th scope="row">{inline(row[0])}</th>' + "".join(f"<td>{inline(c)}</td>" for c in row[1:])
        body.append(f"            <tr{rid}>{cells}</tr>")
    cls = " table-wrap--wide" if wide else ""
    return f"""        <div class="table-wrap{cls}" tabindex="0" role="region" aria-label="{e(label)}">
          <table>
            <thead><tr>{head}</tr></thead>
            <tbody>
{chr(10).join(body)}
            </tbody>
          </table>
        </div>"""


def ul(items):
    return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"


def paras(items):
    return "\n".join(f"        <p>{inline(p)}</p>" for p in items)


def section(heading, inner, cls="", sid=""):
    c = f' class="{cls}"' if cls else ""
    i = f' id="{sid}"' if sid else ""
    return f"""      <section{c}{i}>
        <h2>{inline(heading)}</h2>
{inner}
      </section>"""


def faq_html(faq):
    return "\n".join(f"        <h3>{inline(f['q'])}</h3>\n        <p>{inline(f['a'])}</p>" for f in faq)


def faq_node(faq):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]}


def quote_block():
    email = bp.SITEDATA["email"]
    links = [f'<li>Email: <a href="mailto:{email}">{email}</a></li>']
    soc = bp.SITEDATA["socials"]
    if soc.get("contra"):
        links.append(f'<li>Contra: <a href="{e(soc["contra"])}" target="_blank" rel="noopener">{e(soc["contra"])}</a></li>')
    if soc.get("instagram"):
        links.append(f'<li>Instagram: <a href="{e(soc["instagram"])}" target="_blank" rel="noopener">{e(soc["instagram"])}</a></li>')
    return f"""  <section class="contact contact--cta quote" id="quote" aria-labelledby="quote-title">
    <h2 id="quote-title" class="contact__title">Get a quote</h2>
    <p class="quote__line">{PITCH}</p>
    <p class="quote__text">Tell me what you need, the length and the deadline. I reply with a fixed price in EUR (excl. VAT).</p>
    <a class="send" href="/contact/">
      <span class="send__label">Open the quote form</span>
      <span class="send__band" aria-hidden="true"></span>
    </a>
    <ul class="quote__links">{''.join(links)}</ul>
  </section>"""


def doc_page(path, title, description, h1, updated, body, graph, crumbs, section_key, og_type="website"):
    """Shared shell for the text pages. One h1, a visible 'Last updated', everything in the HTML."""
    global VERIFY_COUNT
    trail = " ".join(
        (f'<a href="{p}">{e(n)}</a><span aria-hidden="true">/</span>' if p else f'<span aria-current="page">{e(n)}</span>')
        for n, p in crumbs)
    html = (
        bp.head(title, description, path, og_type=og_type, graph=graph)
        + f"""
  <a class="skip" href="#main">Skip to content</a>

{bp.nav(section_key, here="page")}

  <main id="main">
    <article class="doc">
      <header class="doc__head">
        <nav class="crumbs caption" aria-label="Breadcrumb">{trail}</nav>
        <h1 class="doc__title">{inline(h1)}</h1>
        <p class="doc__meta caption">Last updated: <time datetime="{updated}">{bp.long_date(updated)}</time></p>
      </header>
      <div class="doc__body">
{body}
      </div>
    </article>
  </main>

{quote_block()}

{bp.footer(updated)}
{bp.tail()}"""
    )
    n = html.count('class="verify"')
    if n:
        VERIFY_BY_PAGE[path] = n
    bp.write(path, html)


VERIFY_BY_PAGE = {}


def capsule(text):
    return f"""      <section class="capsule" aria-labelledby="capsule-title">
        <h2 id="capsule-title" class="caption">Short answer</h2>
        <p>{inline(text)}</p>
      </section>"""


def breadcrumbs_node(*trail):
    return bp.breadcrumbs(("Home", "/"), *trail)


# ---------- pricing ----------

def lead_time(text):
    m = re.match(r"\+?(\d+)(?:–(\d+))? working days", text)
    if not m:
        return None
    lo, hi = int(m[1]), int(m[2] or m[1])
    return {"@type": "QuantitativeValue", "minValue": lo, "maxValue": hi, "unitText": "working days"}


def price_spec(amount, month=False):
    spec = {"@type": "UnitPriceSpecification" if month else "PriceSpecification",
            "price": f"{amount:.2f}", "priceCurrency": "EUR", "valueAddedTaxIncluded": False}
    if month:
        spec["unitCode"] = "MON"
        spec["unitText"] = "month"
    return spec


def service_nodes(pr):
    nodes = []
    for pk in pr["packages"]:
        url = f"{bp.SITE}/pricing/#{pk['id']}"
        offer = {"@type": "Offer", "url": url, "price": f"{pk['price']:.2f}", "priceCurrency": "EUR",
                 "priceSpecification": price_spec(pk["price"]), "description": f"{pk['length']}, {pk['turnaround']}"}
        lead = lead_time(pk["turnaround"])
        if lead:
            offer["deliveryLeadTime"] = lead
        nodes.append({"@type": "Service", "@id": url, "name": pk["name"], "serviceType": "Motion design",
                      "description": f"{pk['description']} Turnaround: {pk['turnaround']}.", "url": url,
                      "provider": bp.org_ref(), "areaServed": AREA, "offers": offer})
    for rt in pr["retainers"]:
        url = f"{bp.SITE}/pricing/#{rt['id']}"
        offer = {"@type": "Offer", "url": url, "price": f"{rt['price']:.2f}", "priceCurrency": "EUR",
                 "priceSpecification": price_spec(rt["price"], month=True),
                 "description": f"{rt['contents']}. Minimum {pr['retainer_minimum']}."}
        nodes.append({"@type": "Service", "@id": url, "name": rt["name"], "serviceType": "Motion design retainer",
                      "description": f"Monthly motion design retainer: {rt['contents']}. Minimum {pr['retainer_minimum']}.",
                      "url": url, "provider": bp.org_ref(), "areaServed": AREA, "offers": offer})
    return nodes


def pricing_faq(pr):
    pk = {p["id"]: p for p in pr["packages"]}
    ad = pk["social-motion-ad-s"]["price"]
    r4, r8 = pr["retainers"]
    x = pr["extra_length"]
    return [
        {"q": "How much does motion design cost at Akdeinz Motion?",
         "a": "Prices start at €390 for a Logo Sting (3–6 s) and go up to €2,400 for a Brand Film (up to 60 s). Social Motion Ad S (up to 15 s) is €490, Ad M (up to 30 s) is €790, Product Promo (30–45 s) is €1,290 and Explainer (up to 60 s) is €1,900. All prices are in EUR, excl. VAT."},
        {"q": "What is included in every package?",
         "a": "16:9, 9:16 and 1:1 versions, 1080p MP4, licensed music and sound design, 2 revision rounds, and a worldwide, perpetual commercial licence for your own channels and paid ads. Logo Sting also includes a transparent-background render."},
        {"q": "How does payment work?", "a": pr["payment"]},
        {"q": "Do I get the project files?",
         "a": "No. The deliverable is the rendered video file only. Project and source files are not offered with any package."},
        {"q": "How much does extra length cost?",
         "a": f"For Product Promo, Explainer and Brand Film, each extra 15 seconds is +{eur(x['price'])} and +2 working days."},
        {"q": "Can I get a monthly plan?",
         "a": f"Yes. Motion Monthly 4 is {eur(r4['price'])} per month for 4 × Social Motion Ad S and Motion Monthly 8 is {eur(r8['price'])} per month for 8 × Social Motion Ad S. Both have a {pr['retainer_minimum']} minimum."},
        {"q": "What does rush delivery cost?", "a": "Delivery in under 72 hours is +35%. 4K delivery is +20%."},
    ]


def build_pricing(pr):
    pk = {p["id"]: p for p in pr["packages"]}
    x = pr["extra_length"]
    rows = [[p["name"], p["length"], eur(p["price"]), p["turnaround"]] for p in pr["packages"]]
    ids = [p["id"] for p in pr["packages"]]
    rows.append([f"Extra length ({x['applies_to']})", x["length"], f"+{eur(x['price'])}", x["turnaround"]])
    ids.append("extra-length")

    ad = pk["social-motion-ad-s"]["price"]
    rrows, rids = [], []
    for rt in pr["retainers"]:
        per = rt["price"] / rt["ads"]
        saving = round((ad - per) / ad * 100)
        rrows.append([rt["name"], rt["contents"], eur(rt["price"]), eur(per), f"About {saving}% less than {eur(ad)}"])
        rids.append(rt["id"])

    faq = pricing_faq(pr)
    cheapest, dearest = pr["packages"][0], pr["packages"][-1]
    answer = (f"Akdeinz Motion motion design costs from {eur(cheapest['price'])} (Logo Sting, {cheapest['length']}, {cheapest['turnaround']}) "
              f"to {eur(dearest['price'])} (Brand Film, {dearest['length']}, {dearest['turnaround']}). Prices are in EUR, excl. VAT. "
              "Every package includes 16:9, 9:16 and 1:1 versions in 1080p MP4, licensed music and sound design, 2 revision rounds and a commercial licence.")
    body = "\n\n".join([
        capsule(answer),
        section("Packages", f"""        <p>{PITCH} Fixed prices in EUR, excl. VAT. Turnaround is in working days.</p>
{table(['Package', 'Length', 'Price (excl. VAT)', 'Turnaround'], rows, 'Packages and prices', ids)}"""),
        section("What every package includes", ul(pr["included"])),
        section("Add-ons", table(["Add-on", "Price"], [[a["name"], a["price"]] for a in pr["addons"]], "Add-ons")),
        section("Monthly retainers", f"""        <p>Minimum {pr['retainer_minimum']}. The per-ad price is the monthly price divided by the number of ads.</p>
{table(['Plan', 'Contents', 'Price per month (excl. VAT)', 'Per ad', 'Against a single ad'], rrows, 'Monthly retainers', rids, wide=True)}"""),
        section("Payment", f"        <p>{inline(pr['payment'])}</p>"),
        section("What you receive", paras([
            "The deliverable is the rendered video file. Source and project files are not part of any package.",
            "The licence is worldwide and perpetual for commercial use on your own channels and in paid ads."])),
        section("Time vs money", f"""        <p class="trade__line">Learning After Effects well enough for a brand video: ~55–110 hours <span class="verify">[VERIFY]</span>. Akdeinz Logo Sting: €390, 3 days.</p>
        <p>The full breakdown, with other tools and a cost table, is in the guide <a href="/guides/learn-after-effects-brand-video/">How long does it take to learn After Effects well enough for a brand video?</a> See also <a href="/guides/motion-design-cost-2026/">How much does motion design cost in 2026?</a></p>""", "trade"),
        section("Frequently asked questions", faq_html(faq), "faq"),
        section("Related guides", ul([
            "[How to animate your logo for Instagram and Reels](/guides/animate-logo-instagram-reels/)",
            "[How to make a product promo video without a designer](/guides/product-promo-video-without-designer/)",
            "[Canva or CapCut vs a professional motion designer](/guides/canva-capcut-vs-motion-designer/)"]), "related"),
    ])
    graph = [bp.org_node(),
             {"@type": "WebPage", "@id": f"{bp.SITE}/pricing/#page", "url": f"{bp.SITE}/pricing/", "name": "Motion design pricing",
              "inLanguage": "en", "dateModified": pr["updated"], "isPartOf": {"@id": f"{bp.SITE}/#site"}},
             *service_nodes(pr), faq_node(faq), breadcrumbs_node(("Pricing", "/pricing/"))]
    doc_page("/pricing/", "Motion design pricing in EUR, from €390 — Akdeinz Motion",
             "Fixed motion design prices in EUR excl. VAT: Logo Sting €390, social ads from €490, Product Promo €1,290, Explainer €1,900, Brand Film €2,400.",
             "Motion design pricing", pr["updated"], body, graph,
             [("Home", "/"), ("Pricing", None)], "pricing")


# ---------- guides ----------

def example_figure(projects, ex):
    p = next(x for x in projects if x["slug"] == ex["slug"])
    url = bp.page_path(p)
    if p.get("video"):
        poster = f' poster="{e(p["poster"])}"' if p.get("poster") else ""
        media = bp.video_tag(p, poster, 'controls playsinline preload="none"')
    else:
        media = f'<img src="{e(p["image"])}" alt="{e(p.get("alt", ""))}" width="600" height="900" loading="lazy" decoding="async">'
    html = f"""        <figure class="example{' example--clip' if p.get('video') else ''}">
          <div class="example__media">{media}</div>
          <figcaption>{inline(ex['caption'])} <a href="{url}">View this piece</a></figcaption>
        </figure>"""
    videos = [g for g in bp.case_graph(p) if g["@type"] == "VideoObject"]
    return html, videos


def build_guide(g, guides, projects, pr):
    path = f"/guides/{g['slug']}/"
    pk = next(p for p in pr["packages"] if p["id"] == g["package"])
    diy = g["diy"]
    cmp_ = g["compare"]
    columns = cmp_.get("columns") or [cmp_["diy_label"], "Freelancer marketplace", "Akdeinz Motion"]
    cmp_title = "Freelancer vs studio vs Akdeinz Motion" if cmp_.get("columns") else f"{cmp_['diy_label']} vs freelancer marketplace vs Akdeinz Motion"

    tools = "<ul>" + "".join(f"<li><strong>{e(t['name'])}</strong>: {inline(t['note'])}</li>" for t in diy["tools"]) + "</ul>"
    steps = "<ol>" + "".join(f"<li>{inline(s)}</li>" for s in diy["steps"]) + "</ol>"
    diy_html = section("Do it yourself", f"""        <p>{inline(diy['intro'])}</p>
        <h3>Tools</h3>
        {tools}
        <h3>Steps</h3>
        {steps}
        <p class="hours">{inline(diy['hours'])}</p>""")

    extra = []
    for s in g.get("sections", []):
        if s.get("token") == "packages":
            rows = [[p["name"], p["length"], eur(p["price"]), p["turnaround"]] for p in pr["packages"]]
            inner = table(["Package", "Length", "Price (excl. VAT)", "Turnaround"], rows, "Akdeinz Motion price list") + \
                '\n        <p><a href="/pricing/">See the full pricing page</a> for add-ons, retainers and what is included.</p>'
        else:
            inner = ""
            if s.get("p"):
                inner += paras(s["p"])
            if s.get("ul"):
                inner += "\n        " + ul(s["ul"])
        extra.append(section(s["h2"], inner))

    compare = section(cmp_title, table(["", *columns], cmp_["rows"], cmp_title, wide=True) +
                      f'\n        <p>Akdeinz Motion prices are fixed and published on the <a href="/pricing/">pricing page</a>.</p>')
    trade = section("Time vs money", f'        <p class="trade__line">{inline(g["time_line"])}</p>', "trade")
    fine = g["diy_fine"]
    fine_html = section("When DIY is fine", f"""        <p>{inline(fine['p'])}</p>
        {ul(fine['ul'])}
        <p>{inline(fine['not_fine'])}</p>""")
    fig, videos = example_figure(projects, g["example"])
    example = section("Example from the portfolio", fig)
    faq_ = section("Frequently asked questions", faq_html(g["faq"]), "faq")
    by_slug = {x["slug"]: x for x in guides}
    related = section("Keep reading", ul(
        [f"[Akdeinz Motion pricing: {eur(pk['price'])} for a {pk['name']}, {pk['turnaround']}](/pricing/)"] +
        [f"[{by_slug[s]['title']}](/guides/{s}/)" for s in g["related"]]), "related")

    body = "\n\n".join([capsule(g["answer"]), diy_html, *extra, compare, trade, fine_html, example, faq_, related])
    graph = [bp.org_node(),
             {"@type": "Article", "@id": f"{bp.SITE}{path}#article", "headline": g["title"], "description": g["description"],
              "inLanguage": "en", "datePublished": g["updated"], "dateModified": g["updated"],
              "mainEntityOfPage": f"{bp.SITE}{path}", "author": bp.org_ref(), "publisher": bp.org_ref()},
             faq_node(g["faq"]), breadcrumbs_node(("Guides", "/guides/"), (g["title"], path)), *videos]
    doc_page(path, g["meta_title"], g["description"], g["title"], g["updated"], body, graph,
             [("Home", "/"), ("Guides", "/guides/"), (g["title"], None)], "guides", og_type="article")


def build_guides_index(guides):
    items = "\n".join(
        f"""        <li><a class="guide__title" href="/guides/{g['slug']}/">{e(g['title'])}</a>
          <p>{e(g['description'])}</p></li>""" for g in guides)
    body = "\n\n".join([
        capsule("Six plain-language guides for founders and small brands who want motion content. Each one answers the question first, then compares doing it yourself, hiring from a freelancer marketplace and hiring Akdeinz Motion, with real tools, hours and prices in EUR."),
        section("All guides", f'        <ul class="guides">\n{items}\n        </ul>'),
        section("Prices", '        <p>Every guide ends with Akdeinz Motion’s fixed prices. See the <a href="/pricing/">pricing page</a> for the full list.</p>'),
    ])
    updated = max(g["updated"] for g in guides)
    graph = [bp.org_node(),
             {"@type": "CollectionPage", "name": "Motion design guides", "url": f"{bp.SITE}/guides/", "inLanguage": "en",
              "dateModified": updated, "isPartOf": {"@id": f"{bp.SITE}/#site"}},
             {"@type": "ItemList", "itemListElement": [
                 {"@type": "ListItem", "position": i + 1, "name": g["title"], "url": f"{bp.SITE}/guides/{g['slug']}/"}
                 for i, g in enumerate(guides)]},
             breadcrumbs_node(("Guides", "/guides/"))]
    doc_page("/guides/", "Motion Design Guides — Akdeinz Motion",
             "Plain-language guides on animating a logo, product promos, motion design costs, Canva vs a motion designer, learning After Effects and Kickstarter videos.",
             "Motion design guides", updated, body, graph, [("Home", "/"), ("Guides", None)], "guides")


# ---------- about ----------

def build_about(pr):
    soc = bp.SITEDATA["socials"]
    story = "The mark joins an A and an M into one continuous form, built from parallel bands cut at 60°. Where the bands overlap, a soft fold catches the light, like film or ribbon pulled through a frame."
    who = bp.SITEDATA["person"]
    portrait = f"""      <section class="person" aria-labelledby="person-title">
        <figure class="person__fig">
          <img src="{who['image']}" alt="Illustrated portrait of {e(who['name'])}, {e(who['jobTitle'])} at Akdeinz Motion" width="624" height="680" decoding="async" fetchpriority="high">
        </figure>
        <div class="person__text">
          <h2 id="person-title">{e(who['name'])}, {e(who['jobTitle'])}</h2>
          <p>{e(who['name'])} is the Creative Director at Akdeinz Motion.</p>
          <p>The studio’s promise: {PITCH} Every package has a fixed price and a set number of working days, so you know the cost and the date before you start.</p>
          <p><a href="/work/">See the work</a> or <a href="/contact/">get a quote</a>.</p>
        </div>
      </section>"""
    body = "\n\n".join([
        capsule(f"Akdeinz Motion is a motion design studio for founders and small brands that need video content but would rather not learn the tools. {PITCH} Packages start at €390 for a Logo Sting, delivered in 3 working days."),
        portrait,
        section("What we make", ul([
            "[Logo stings](/pricing/#logo-sting): 3–6 seconds, from €390.",
            "[Social motion ads](/pricing/#social-motion-ad-s): up to 15 s from €490, up to 30 s from €790.",
            "[Product promos](/pricing/#product-promo): 30–45 seconds, €1,290.",
            "[Explainers](/pricing/#explainer): up to 60 seconds, €1,900.",
            "[Brand films](/pricing/#brand-film): up to 60 seconds, €2,400.",
            "[Monthly retainers](/pricing/#motion-monthly-4): 4 or 8 social ads a month, 3-month minimum."])),
        section("Who it is for", paras([
            "Founders and small brands who are making motion content themselves, or thinking about it. We work with clients in Belgium and the EU first, the United States second, and anywhere else.",
            "The pitch is time. Learning After Effects well enough for a brand video is an estimated 55–110 hours [VERIFY]. A Logo Sting is €390 and 3 working days. The [guides](/guides/) show the numbers for each tool."])),
        section("How it works", "<ol>" + "".join(f"<li>{inline(s)}</li>" for s in [
            "Get a quote: tell us what you need, the length and the deadline.",
            "Pay 50% to start.",
            "Review a watermarked preview and send up to 2 rounds of revisions.",
            "Approve the preview and pay the remaining 50%.",
            "Receive the rendered video in 16:9, 9:16 and 1:1, 1080p MP4."]) + "</ol>"),
        section("What you get, and what you do not", paras([
            "You get the rendered video files, licensed music and sound design, and a worldwide, perpetual commercial licence for your own channels and paid ads.",
            "You do not get source or project files. The deliverable is the video."])),
        section("The mark", paras([story])),
        section("Short bio", f"        <p>{inline(bp.SITEDATA['bio'])}</p>"),
        section("Contact", f'        <p>Email: <a href="mailto:{bp.SITEDATA["email"]}">{bp.SITEDATA["email"]}</a>. Or use the <a href="/contact/">contact page</a>.</p>'),
    ])
    graph = [bp.org_node(), bp.person_node(),
             {"@type": "AboutPage", "name": "About Akdeinz Motion", "url": f"{bp.SITE}/about/", "inLanguage": "en",
              "dateModified": bp.UPDATED, "about": bp.org_ref(), "mainEntity": {"@id": f"{bp.SITE}/#esref"}, "isPartOf": {"@id": f"{bp.SITE}/#site"}},
             breadcrumbs_node(("About", "/about/"))]
    doc_page("/about/", "About Akdeinz Motion — motion design for small brands",
             "Akdeinz Motion is a motion design studio for founders and small brands: logo stings, social ads, product promos, explainers and brand films from €390.",
             "About Akdeinz Motion", bp.UPDATED, body, graph, [("Home", "/"), ("About", None)], "about")


# ---------- contact ----------

def build_contact():
    soc = bp.SITEDATA["socials"]
    email = bp.SITEDATA["email"]
    links = [f'<li><span class="caption">Email</span><a href="mailto:{email}">{email}</a></li>']
    if soc.get("instagram"):
        links.append(f'<li><span class="caption">Instagram</span><a href="{e(soc["instagram"])}" target="_blank" rel="noopener">@akdeinzmotion</a></li>')
    if soc.get("contra"):
        links.append(f'<li><span class="caption">Contra</span><a href="{e(soc["contra"])}" target="_blank" rel="noopener">Akdeinz Motion on Contra</a></li>')
    links.append('<li><span class="caption">Prices</span><a href="/pricing/">Packages and add-ons</a></li>')
    title = "Contact and quote — Akdeinz Motion"
    description = "Get a fixed-price motion design quote. Use the form or email hello@akdeinzmotion.com. Prices from €390, in EUR excl. VAT."
    graph = [bp.org_node(),
             {"@type": "ContactPage", "name": "Contact Akdeinz Motion", "url": f"{bp.SITE}/contact/", "inLanguage": "en",
              "isPartOf": {"@id": f"{bp.SITE}/#site"}, "about": bp.org_ref()},
             breadcrumbs_node(("Contact", "/contact/"))]
    html = (
        bp.head(title, description, "/contact/", graph=graph)
        + f"""
  <a class="skip" href="#main">Skip to content</a>

{bp.nav("contact", here="page")}

  <main id="main">
    <section class="contact contact--page" aria-labelledby="contact-title">
      <nav class="crumbs caption" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">Contact</span></nav>
      <h1 id="contact-title" class="contact__title">Get a quote</h1>
      <p class="quote__line">{PITCH}</p>
      <p class="quote__text">Tell me what you need, the length and the deadline. I reply with a fixed price in EUR (excl. VAT). Payment is 50% to start and 50% after you approve a watermarked preview.</p>

      <div class="contact__grid">
        <ul class="contact__links">{''.join(links)}</ul>

        <form class="form" name="contact" method="POST" action="/thanks.html"
              data-netlify="true" netlify-honeypot="bot-field" data-form>
          <input type="hidden" name="form-name" value="contact">
          <p class="visually-hidden"><label>Leave empty <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>

          <div class="field">
            <input id="f-name" name="name" type="text" autocomplete="name" required placeholder=" ">
            <label for="f-name">Name</label>
          </div>
          <div class="field">
            <input id="f-email" name="email" type="email" autocomplete="email" required placeholder=" ">
            <label for="f-email">Email</label>
          </div>
          <div class="field field--full">
            <textarea id="f-msg" name="message" rows="3" required placeholder=" "></textarea>
            <label for="f-msg">Project, timeline, budget</label>
          </div>

          <div class="form__foot">
            <button class="send" type="submit" data-send>
              <span class="send__label" data-send-label>Send</span>
              <span class="send__band" aria-hidden="true"></span>
            </button>
            <p class="form__status" data-status role="status" aria-live="polite"></p>
          </div>
        </form>
      </div>
    </section>
  </main>

{bp.footer()}
{bp.tail()}"""
    )
    bp.write("/contact/", html)


# ---------- text files ----------

def write_llms(pr, guides):
    soc = bp.SITEDATA["socials"]
    lines = [
        "# Akdeinz Motion", "",
        "> Motion design studio for founders and small brands. Logo stings, social motion ads, product promos, explainers, brand films and monthly retainers. Market: Belgium and the EU first, the US second, worldwide welcome. The deliverable is the rendered video file only (no source or project files).", "",
        f"Pitch: {PITCH}", "",
        f"Last updated: {bp.UPDATED}", "",
        "## Packages (EUR, excl. VAT)", ""]
    for p in pr["packages"]:
        lines.append(f"- {p['name']} ({p['length']}): {eur(p['price'])}, {p['turnaround']}")
    x = pr["extra_length"]
    lines += [f"- Extra length ({x['applies_to']}): {x['length']}, +{eur(x['price'])}, {x['turnaround']}", "",
              "## Retainers", ""]
    for r in pr["retainers"]:
        lines.append(f"- {r['name']}: {r['contents']}, {eur(r['price'])} per month, {pr['retainer_minimum']} minimum")
    lines += ["", "## Included in every package", ""] + [f"- {i}" for i in pr["included"]]
    lines += ["", "## Add-ons", ""] + [f"- {a['name']}: {a['price']}" for a in pr["addons"]]
    lines += ["", "## Payment", "", pr["payment"], "", "## Key pages", "",
              f"- [Pricing]({bp.SITE}/pricing/): all packages, add-ons, retainers and FAQ",
              f"- [Guides]({bp.SITE}/guides/): plain-language guides with tools, hours and costs"]
    lines += [f"  - [{g['title']}]({bp.SITE}/guides/{g['slug']}/)" for g in guides]
    lines += [f"- [Work]({bp.SITE}/work/): portfolio pieces",
              f"- [Reels]({bp.SITE}/reels/): short motion pieces",
              f"- [About]({bp.SITE}/about/): who we are, Creative Director {bp.SITEDATA['person']['name']}",
              f"- [Contact]({bp.SITE}/contact/): quote form, email and links", "", "## Contact", "",
              f"- Email: {bp.SITEDATA['email']}", f"- Contact and quote form: {bp.SITE}/contact/"]
    if soc.get("instagram"):
        lines.append(f"- Instagram: {soc['instagram']}")
    if soc.get("contra"):
        lines.append(f"- Contra: {soc['contra']}")
    (bp.ROOT / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_robots():
    blocks = [f"User-agent: {bot}\nAllow: /\n" for bot in CRAWLERS]
    text = "# AI assistants and search engines are welcome to read and cite this site.\n\n" + "\n".join(blocks) + \
        "\nUser-agent: *\nAllow: /\n\n" + f"Sitemap: {bp.SITE}/sitemap.xml\nSitemap: {bp.SITE}/sitemap-video.xml\n"
    (bp.ROOT / "robots.txt").write_text(text, encoding="utf-8", newline="\n")


# ---------- home blocks ----------

def home_offer():
    pr = load("pricing.json")
    rows = [[p["name"], p["length"], eur(p["price"]), p["turnaround"]] for p in pr["packages"]]
    return f"""      <header class="section-head">
        <h2 id="offer-title" class="caption">Prices at a glance</h2>
        <span class="caption section-head__count">EUR, excl. VAT</span>
      </header>
      <p class="offer__line">{PITCH}</p>
      <p class="offer__text">Motion design for founders and small brands who would rather not learn After Effects. Every package includes 16:9, 9:16 and 1:1 versions, licensed music and sound design, 2 revision rounds and a commercial licence.</p>
{table(['Package', 'Length', 'Price', 'Turnaround'], rows, 'Prices at a glance')}
      <a class="more" href="/pricing/">Full pricing</a>
      <a class="more more--sub" href="/guides/">Guides: tools, hours and costs</a>"""


def socials_block():
    soc = bp.SITEDATA["socials"]
    items = []
    if soc.get("instagram"):
        items.append(f'<li><a href="{e(soc["instagram"])}" target="_blank" rel="noopener">Instagram</a></li>')
    if soc.get("contra"):
        items.append(f'<li><a href="{e(soc["contra"])}" target="_blank" rel="noopener">Contra</a></li>')
    return f'          <ul class="socials" aria-label="Social">{"".join(items)}</ul>' if items else ""


# ---------- entry ----------

def build():
    global VERIFY_COUNT
    pr = load("pricing.json")
    guides = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((bp.ROOT / "content" / "guides").glob("*.json"))]
    guides.sort(key=lambda g: ORDER.index(g["slug"]))
    slugs = {g["slug"] for g in guides}
    projects = load("projects.json")["projects"]
    for g in guides:
        if len(g["related"]) != 2 or not set(g["related"]) <= slugs or g["slug"] in g["related"]:
            raise SystemExit(f"{g['slug']}: related must name 2 other guides")
        if not 4 <= len(g["faq"]) <= 6:
            raise SystemExit(f"{g['slug']}: FAQ needs 4–6 questions")

    shutil.rmtree(bp.ROOT / "guides", ignore_errors=True)
    for g in guides:
        build_guide(g, guides, projects, pr)
    build_guides_index(guides)
    build_pricing(pr)
    build_about(pr)
    build_contact()
    write_llms(pr, guides)
    write_robots()

    VERIFY_COUNT = sum(VERIFY_BY_PAGE.values())
    for path, n in sorted(VERIFY_BY_PAGE.items()):
        print(f"  {n:3d} [VERIFY] on {path}")
    extra = [("/pricing/", pr["updated"]), ("/guides/", max(g["updated"] for g in guides)), ("/about/", bp.UPDATED), ("/contact/", bp.UPDATED)]
    extra += [(f"/guides/{g['slug']}/", g["updated"]) for g in guides]
    return extra


ORDER = ["animate-logo-instagram-reels", "product-promo-video-without-designer", "motion-design-cost-2026",
         "canva-capcut-vs-motion-designer", "learn-after-effects-brand-video", "kickstarter-launch-video"]
