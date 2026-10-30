# Akdeinz Motion

Website for **Akdeinz Motion**, a motion design studio and an East Marketing brand.

- Live: https://akdeinzmotion.com
- Hosting: Netlify (static, no build step; publish directory is the repo root)

## For automated tools (Pinterest)

Read [`pinterest.json`](pinterest.json) first. It holds the brand facts, links (with UTM tags), colour and logo rules, pin format, tone of voice and keywords. Only use facts from that file.

Project tiles on the site are placeholders until real work is uploaded (`status.projects_are_placeholders`), so don't describe specific client projects.

## Structure

```
index.html        single page: hero, showreel, work, contact
styles.css        brand tokens and layout
main.js           logo sting, 60° motion studies, scroll effects, form
thanks.html       form fallback page
404.html
sitemap.xml       list of public pages (add new top-level pages here)
robots.txt
netlify.toml      headers and caching
assets/           logos, favicon, social image, work/ for project videos
pinterest.json    machine-readable brand and content brief
```

## Updating files

When `styles.css` or `main.js` change, raise the `?v=` number where they are linked in `index.html`, `thanks.html` and `404.html`, so returning visitors get the new version.

## Adding work

1. Put clips in `assets/work/` (short, compressed MP4).
2. On each tile in `index.html`, set `data-video="/assets/work/01.mp4"` and update the title and type.
3. Showreel: add `assets/reel.mp4` and set `data-src="/assets/reel.mp4"` on the reel video.

## Brand

Black and white base, Akdeniz Blue `#2E6BFF` in small doses, 60° bands, one easing curve: `cubic-bezier(0.2, 0.8, 0.2, 1)`.
