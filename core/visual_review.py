"""HTML for the Visual Review page: baseline vs actual vs diff, with one-click approval."""
import html
from urllib.parse import quote

from core import visual_compare

_STATUS_LABEL = {"failed": "Mismatch", "new": "New baseline", "updated": "Updated", "passed": "Match"}


def _image_url(item: dict, kind: str) -> str:
    stamp = quote(str(item.get("timestamp", "")))
    return f"/visual-image/{quote(item['profile'])}/{quote(item['name'])}/{kind}.png?t={stamp}"


def _card(item: dict) -> str:
    status = item.get("status", "passed")
    name, profile = html.escape(item.get("name", "")), html.escape(item.get("profile", ""))
    can_approve = status in ("failed", "new")
    show_diff = status == "failed"
    data_name = html.escape(item.get("name", ""), quote=True)
    data_profile = html.escape(item.get("profile", ""), quote=True)
    pct = item.get("mismatch_pct", 0)
    meta = [f"{profile}", html.escape(item.get("timestamp", ""))]
    if item.get("test"):
        meta.append(html.escape(item["test"]))
    modes = '<button class="mode active" data-mode="side">Side by side</button><button class="mode" data-mode="slider">Slider</button>'
    if show_diff:
        modes += '<button class="mode" data-mode="diff">Diff</button>'
    approve = (f'<button class="approve" onclick="approve(this)">✓ Approve as baseline</button>' if can_approve else "")
    diff_cell = (f'<figure><figcaption>Difference</figcaption><img src="{_image_url(item, "diff")}"></figure>' if show_diff else "")
    return f"""
<section class="card {status}" data-status="{status}" data-name="{data_name}" data-profile="{data_profile}">
  <header>
    <span class="badge {status}">{_STATUS_LABEL.get(status, status)}</span>
    <h3>{name}</h3>
    <span class="pct">{pct}% different</span>
    <span class="meta">{' · '.join(meta)}</span>
  </header>
  <p class="msg">{html.escape(item.get('message', ''))}</p>
  <div class="bar"><div class="modes">{modes}</div>{approve}</div>
  <div class="view side">
    <figure><figcaption>Baseline</figcaption><img src="{_image_url(item, 'baseline')}"></figure>
    <figure><figcaption>Actual</figcaption><img src="{_image_url(item, 'actual')}"></figure>
    {diff_cell}
  </div>
  <div class="view slider" hidden>
    <div class="slide"><img src="{_image_url(item, 'baseline')}"><div class="top"><img src="{_image_url(item, 'actual')}"></div>
    <input type="range" min="0" max="100" value="50" oninput="slide(this)"><span class="handle"></span></div>
    <p class="hint">Drag: left = actual, right = baseline</p>
  </div>
  <div class="view diff" hidden><figure><img src="{_image_url(item, 'diff')}"></figure></div>
</section>"""


def render_page() -> str:
    items = visual_compare.list_results()
    counts = {key: sum(1 for i in items if i.get("status") == key) for key in ("failed", "new", "updated", "passed")}
    cards = "".join(_card(item) for item in items) or (
        '<div class="empty"><h2>No visual results yet</h2><p>Run a test that uses <code>verify visual match</code>; '
        'the first run creates the baseline and later runs show up here.</p></div>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>ICICI Nirikshan - Visual Review</title>
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link href="https://fonts.googleapis.com/css2?family=Mulish:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{ --red:#C23029; --orange:#E77817; --dark:#97291E; --ink:#0A192F; --slate:#5C6E89; --line:#E5E8EB; --bg:#F9F9F9; --green:#1E7A4C; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:'Mulish',Arial,sans-serif; }}
.top {{ }}
.hdr {{ display:flex; align-items:center; gap:14px; padding:14px 28px; background:#fff; border-bottom:3px solid var(--orange); position:sticky; top:0; z-index:5; }}
.hdr img {{ height:42px; }}
.hdr h1 {{ font-size:20px; margin:0; flex:1; }}
.hdr h1 small {{ display:block; font-size:12px; color:var(--slate); font-weight:600; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; }}
.chip {{ border:1.5px solid var(--line); background:#fff; border-radius:20px; padding:6px 14px; font-size:12px; font-weight:800; cursor:pointer; font-family:inherit; color:var(--slate); }}
.chip.active {{ border-color:var(--orange); background:#FCEEE2; color:var(--dark); }}
.btn {{ border:none; border-radius:8px; padding:9px 16px; font-size:12px; font-weight:800; cursor:pointer; color:#fff; background:linear-gradient(90deg,var(--red),#EA761B); font-family:inherit; }}
.btn:hover {{ filter:brightness(.92); }}
main {{ max-width:1400px; margin:22px auto; padding:0 24px 60px; }}
.card {{ background:#fff; border:1px solid var(--line); border-left:5px solid var(--green); border-radius:12px; padding:16px 20px; margin-bottom:18px; box-shadow:0 2px 10px rgba(10,25,47,.04); }}
.card.failed {{ border-left-color:#DC3434; }} .card.new {{ border-left-color:var(--orange); }} .card.updated {{ border-left-color:#4F6DD0; }}
.card header {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
.card h3 {{ margin:0; font-size:16px; }}
.badge {{ border-radius:6px; padding:3px 10px; font-size:11px; font-weight:800; }}
.badge.failed {{ background:#FBDADA; color:#B3261E; }} .badge.passed {{ background:#DEE7DA; color:var(--green); }}
.badge.new {{ background:#F7DCC5; color:var(--dark); }} .badge.updated {{ background:#E3E8FA; color:#3B52A8; }}
.pct {{ font-size:12px; font-weight:800; color:var(--dark); }} .meta {{ font-size:11px; color:var(--slate); margin-left:auto; }}
.msg {{ font-size:12px; color:var(--slate); margin:6px 0 10px; }}
.bar {{ display:flex; align-items:center; gap:10px; margin-bottom:12px; }}
.modes {{ display:flex; gap:6px; flex:1; }}
.mode {{ border:1.5px solid var(--line); background:#fff; border-radius:8px; padding:5px 12px; font-size:11px; font-weight:800; cursor:pointer; font-family:inherit; color:var(--slate); }}
.mode.active {{ border-color:var(--orange); background:#FCEEE2; color:var(--dark); }}
.approve {{ border:1.5px solid var(--orange); background:#fff; color:var(--red); border-radius:8px; padding:6px 14px; font-size:12px; font-weight:800; cursor:pointer; font-family:inherit; }}
.approve:hover {{ background:#FCEEE2; }}
.view.side {{ display:flex; gap:14px; }}
.view figure {{ flex:1; margin:0; min-width:0; }}
.view figcaption {{ font-size:11px; font-weight:800; color:var(--slate); text-transform:uppercase; margin-bottom:6px; }}
.view img {{ width:100%; display:block; border:1px solid var(--line); border-radius:6px; background:#fff; }}
.slide {{ position:relative; max-width:900px; margin:0 auto; line-height:0; }}
.slide .top {{ position:absolute; inset:0; clip-path:inset(0 50% 0 0); }}
.slide input {{ position:absolute; left:0; right:0; bottom:-26px; width:100%; accent-color:var(--orange); }}
.slide .handle {{ position:absolute; top:0; bottom:0; left:50%; width:2px; background:var(--orange); pointer-events:none; }}
.hint {{ text-align:center; font-size:11px; color:var(--slate); margin-top:34px; }}
.empty {{ text-align:center; padding:80px 20px; color:var(--slate); }}
.empty code {{ background:#FCEEE2; padding:2px 6px; border-radius:4px; color:var(--dark); }}
.toast {{ position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:var(--dark); color:#fff; padding:10px 20px; border-radius:24px; font-size:13px; opacity:0; transition:.25s; pointer-events:none; }}
.toast.show {{ opacity:1; }}
</style></head><body>
<div class="hdr"><img src="/logo.png" alt="ICICI Nirikshan"><h1>Visual Review<small>Compare each build with its approved baseline</small></h1>
  <div class="chips">
    <button class="chip active" data-filter="all">All ({len(items)})</button>
    <button class="chip" data-filter="failed">Mismatch ({counts['failed']})</button>
    <button class="chip" data-filter="new">New ({counts['new']})</button>
    <button class="chip" data-filter="passed">Match ({counts['passed']})</button>
  </div>
  <button class="btn" onclick="approveAll()">✓ Approve all mismatches &amp; new</button>
</div>
<main>{cards}</main>
<div id="toast" class="toast"></div>
<script>
function toast(m) {{ var t=document.getElementById('toast'); t.textContent=m; t.classList.add('show'); setTimeout(function(){{t.classList.remove('show');}},2200); }}
document.querySelectorAll('.chip').forEach(function(c) {{ c.onclick=function() {{
  document.querySelectorAll('.chip').forEach(function(x){{x.classList.remove('active');}}); c.classList.add('active');
  var f=c.dataset.filter; document.querySelectorAll('.card').forEach(function(card){{ card.style.display=(f==='all'||card.dataset.status===f)?'':'none'; }}); }}; }});
document.querySelectorAll('.card').forEach(function(card) {{
  card.querySelectorAll('.mode').forEach(function(btn) {{ btn.onclick=function() {{
    card.querySelectorAll('.mode').forEach(function(x){{x.classList.remove('active');}}); btn.classList.add('active');
    card.querySelectorAll('.view').forEach(function(v){{ v.hidden = !v.classList.contains(btn.dataset.mode); }}); }}; }}); }});
function slide(input) {{ var box=input.parentNode; box.querySelector('.top').style.clipPath='inset(0 '+(100-input.value)+'% 0 0)'; box.querySelector('.handle').style.left=input.value+'%'; }}
function post(items) {{
  return fetch('/visual/approve', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{items:items}})}})
    .then(function(r){{return r.json();}});
}}
function approve(btn) {{
  var card=btn.closest('.card');
  post([{{profile:card.dataset.profile, name:card.dataset.name}}]).then(function(d) {{
    if (d.error) {{ toast('⚠ '+d.error); return; }} toast('Baseline approved'); setTimeout(function(){{location.reload();}},700); }});
}}
function approveAll() {{
  var items=[]; document.querySelectorAll('.card').forEach(function(card) {{
    if (card.dataset.status==='failed'||card.dataset.status==='new') items.push({{profile:card.dataset.profile,name:card.dataset.name}}); }});
  if (!items.length) {{ toast('Nothing to approve'); return; }}
  if (!confirm('Approve '+items.length+' screenshot(s) as the new baseline?')) return;
  post(items).then(function(d) {{ if (d.error) {{ toast('⚠ '+d.error); return; }} toast(d.approved+' baseline(s) approved'); setTimeout(function(){{location.reload();}},700); }});
}}
</script></body></html>"""
