HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bàrdachd</title>
<style>
:root{
  --paper:#f3 efe3; --paper:#f3efe3; --ink:#1c2231; --ink-soft:#5a6072;
  --rule:#d8cfbd; --accent:#2f4a6b; --accent-warm:#9a5b3b;
  --stress:#9a5b3b; --unstress:#bdb6a6; --card:#fbf8f0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1100px;margin:0 auto;padding:0 20px 80px}
header.top{padding:38px 0 22px;border-bottom:1px solid var(--rule);
  display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:10px}
.brand{font-size:34px;letter-spacing:.02em;font-weight:600}
.brand .sub{display:block;font-size:13px;font-weight:400;color:var(--ink-soft);
  letter-spacing:.16em;text-transform:uppercase;margin-top:4px;
  font-family:ui-sans-serif,system-ui,sans-serif}
nav.tabs{display:flex;gap:4px;margin:18px 0 26px;flex-wrap:wrap}
nav.tabs button{font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;
  letter-spacing:.08em;text-transform:uppercase;border:1px solid transparent;
  background:none;color:var(--ink-soft);padding:8px 14px;cursor:pointer;border-radius:2px}
nav.tabs button:hover{color:var(--ink)}
nav.tabs button.on{color:var(--ink);border-color:var(--rule);background:var(--card)}
.panel{display:none;animation:fade .3s ease}
.panel.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
h2{font-weight:600;font-size:22px;margin:0 0 4px}
.hint{color:var(--ink-soft);font-size:14px;margin:0 0 20px;
  font-family:ui-sans-serif,system-ui,sans-serif}

/* editor + scansion */
.editor{display:grid;grid-template-columns:1fr 320px;gap:28px}
@media(max-width:840px){.editor{grid-template-columns:1fr}}
textarea#draft{width:100%;min-height:300px;background:var(--card);
  border:1px solid var(--rule);border-radius:3px;padding:18px 20px;
  font-family:inherit;font-size:18px;line-height:1.9;color:var(--ink);resize:vertical}
textarea#draft:focus{outline:none;border-color:var(--accent)}
.titlerow{display:flex;gap:10px;margin-bottom:12px}
.titlerow input,.titlerow select{font-family:ui-sans-serif,system-ui,sans-serif;
  border:1px solid var(--rule);background:var(--card);padding:9px 11px;
  border-radius:3px;color:var(--ink);font-size:14px}
.titlerow input{flex:1;font-size:16px;font-family:inherit}
.btn{font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;letter-spacing:.06em;
  border:1px solid var(--accent);background:var(--accent);color:#fff;padding:9px 16px;
  border-radius:3px;cursor:pointer}
.btn:hover{background:#26405e}
.btn.ghost{background:none;color:var(--accent)}
.btn.ghost:hover{background:var(--card)}
.toolbar{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}

/* scansion readout */
.scan{font-family:ui-sans-serif,system-ui,sans-serif}
.scanline{margin:0 0 16px;padding-bottom:14px;border-bottom:1px dotted var(--rule)}
.sylrow{display:flex;flex-wrap:wrap;gap:2px;align-items:flex-end;margin-bottom:4px}
.sylrow.with-ghost{padding-top:4px}
.syl{display:flex;flex-direction:column;align-items:center;min-width:14px}
.dot{font-size:13px;line-height:1;color:var(--unstress);height:14px}
.dot.s{color:var(--stress);font-weight:700}
.dot.miss{color:#c0392b}            /* actual stress contradicts the form */
.dot.extra{color:#c79100}           /* syllable beyond the form's length */
.dot.off-missing{color:#c0392b;opacity:.5}  /* form wants a beat that isn't there */
.ghost{font-size:10px;line-height:1;height:11px;color:rgba(47,74,107,.22)}
.ghost.gs{color:rgba(47,74,107,.5)}  /* target stressed beat */
.ghost.empty-slot{color:rgba(0,0,0,.12)}
.syl .w{font-family:inherit;font-size:11px;color:var(--ink-soft);
  margin-top:3px;max-width:60px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.meta{font-size:12px;color:var(--ink-soft)}
.meta b{color:var(--accent);font-weight:600}
.warn{color:var(--accent-warm);font-size:12px}
.legend{font-family:ui-sans-serif,system-ui,sans-serif;font-size:12px;
  color:var(--ink-soft);margin-bottom:14px}
.legend .stress{color:var(--stress)} .legend .unstress{color:var(--unstress)}
.badge{font-family:ui-sans-serif,system-ui,sans-serif;font-size:10px;letter-spacing:.04em;
  padding:2px 7px;border-radius:10px;margin-left:6px;white-space:nowrap}
.badge.good{background:#e3efe2;color:#2f6b3a}
.badge.mid{background:#f3ecd9;color:#8a6a1f}
.badge.low{background:#f3e0dc;color:#a3372a}

/* forms */
.formgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}
.formcard{background:var(--card);border:1px solid var(--rule);border-radius:3px;padding:18px 20px}
.formcard h3{margin:0 0 2px;font-size:18px}
.formcard .meta{font-family:ui-sans-serif,system-ui,sans-serif;font-size:12px;
  color:var(--ink-soft);margin:0 0 10px}
.formcard dl{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px}
.formcard dt{color:var(--ink-soft);text-transform:uppercase;letter-spacing:.06em;
  font-size:10px;margin-top:8px}
.formcard dd{margin:1px 0 0}
.scheme{display:flex;gap:3px;flex-wrap:wrap;margin-top:8px}
.scheme span{font-family:ui-monospace,monospace;font-size:11px;width:20px;height:20px;
  display:grid;place-items:center;background:var(--paper);border:1px solid var(--rule);border-radius:2px}
.formcard .note{font-size:13px;color:var(--ink-soft);margin-top:12px;font-style:italic}
.usebtn{margin-top:14px}

/* rhyme + exercises */
.rhyme-search{display:flex;gap:8px;margin-bottom:20px;max-width:420px}
.rhyme-search input{flex:1;font-family:inherit;font-size:18px;padding:10px 14px;
  border:1px solid var(--rule);background:var(--card);border-radius:3px}
.rhyme-search input:focus{outline:none;border-color:var(--accent)}
.rhyme-group h4{font-family:ui-sans-serif,system-ui,sans-serif;font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);margin:18px 0 8px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:15px;padding:4px 10px;background:var(--card);border:1px solid var(--rule);
  border-radius:14px;cursor:default}
.exlist{display:grid;gap:14px}
.ex{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--accent);
  border-radius:3px;padding:16px 20px}
.ex .skill{font-family:ui-sans-serif,system-ui,sans-serif;font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--accent-warm)}
.ex h3{margin:3px 0 6px;font-size:18px}
.ex p{margin:0;color:var(--ink-soft);font-size:15px}
.reslist{display:grid;gap:14px}
.res{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--accent-warm);
  border-radius:3px;padding:16px 20px}
.res .kind{font-family:ui-sans-serif,system-ui,sans-serif;font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--accent-warm)}
.res h3{margin:3px 0 2px;font-size:18px}
.res h3 a{color:var(--accent);text-decoration:none}
.res h3 a:hover{text-decoration:underline}
.res .by{font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;color:var(--ink-soft);margin:0 0 6px}
.res p{margin:0;color:var(--ink-soft);font-size:15px}
.res .link{font-family:ui-sans-serif,system-ui,sans-serif;font-size:12px;
  word-break:break-all;margin-top:8px}
.res .link a{color:var(--accent)}
.res .added{font-family:ui-sans-serif,system-ui,sans-serif;font-size:10px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);margin-left:8px}
.res .del{font-family:ui-sans-serif,system-ui,sans-serif;font-size:12px;
  border:1px solid var(--rule);background:none;color:var(--accent-warm);
  padding:3px 9px;border-radius:3px;cursor:pointer;margin-top:10px}
.res .del:hover{background:var(--paper)}
.addbox{margin-top:22px;border-top:1px dotted var(--rule);padding-top:14px}
.addbox summary{font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;
  letter-spacing:.04em;color:var(--accent);cursor:pointer;list-style:none}
.addbox summary::-webkit-details-marker{display:none}
.addbox summary:hover{color:var(--ink)}
.addform{display:grid;gap:8px;margin-top:14px;max-width:520px}
.addform input,.addform textarea{font-family:inherit;font-size:15px;
  border:1px solid var(--rule);background:var(--card);padding:9px 11px;
  border-radius:3px;color:var(--ink)}
.addform input:focus,.addform textarea:focus{outline:none;border-color:var(--accent)}
.addform textarea{min-height:64px;resize:vertical}
.addform .btn{justify-self:start}
.poemlist{display:grid;gap:8px;margin-top:6px}
.poemrow{display:flex;justify-content:space-between;align-items:center;
  background:var(--card);border:1px solid var(--rule);border-radius:3px;padding:10px 16px}
.poemrow .t{font-size:17px} .poemrow .m{font-family:ui-sans-serif,system-ui,sans-serif;
  font-size:11px;color:var(--ink-soft)}
.poemrow .acts button{margin-left:6px}
.empty{color:var(--ink-soft);font-style:italic;padding:20px 0}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
  background:var(--ink);color:#fff;padding:10px 20px;border-radius:4px;
  font-family:ui-sans-serif,system-ui,sans-serif;font-size:14px;opacity:0;
  transition:opacity .3s;pointer-events:none}
.toast.show{opacity:1}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">Bàrdachd<span class="sub">a workshop in metre &amp; rhyme</span></div>
  </header>

  <nav class="tabs">
    <button data-tab="write" class="on">Write</button>
    <button data-tab="forms">Forms</button>
    <button data-tab="rhyme">Rhyme</button>
    <button data-tab="exercises">Exercises</button>
    <button data-tab="reading">Further reading</button>
    <button data-tab="websites">Websites</button>
    <button data-tab="media">Media</button>
    <button data-tab="saved">Saved</button>
  </nav>

  <!-- WRITE -->
  <section class="panel on" id="write">
    <div class="titlerow">
      <input id="title" placeholder="Title" value="Untitled">
      <select id="form"></select>
    </div>
    <div class="editor">
      <div>
        <textarea id="draft" placeholder="Type a line and watch the beat appear…
Shall I compare thee to a summer's day"></textarea>
        <div class="toolbar">
          <button class="btn" id="save">Save poem</button>
          <button class="btn ghost" id="newp">New</button>
          <button class="btn ghost" id="export">Export .txt</button>
        </div>
      </div>
      <div>
        <div class="legend">Stress map &nbsp;
          <span class="stress">●</span> stressed &nbsp;
          <span class="unstress">●</span> unstressed
          <span id="ghostkey" style="display:none">&nbsp;·&nbsp;
          <span style="color:rgba(47,74,107,.5)">●</span> form's target beat &nbsp;
          <span style="color:#c0392b">●</span> off the metre</span></div>
        <div class="scan" id="scan"><p class="empty">Lines appear here as you type.</p></div>
      </div>
    </div>
  </section>

  <!-- FORMS -->
  <section class="panel" id="forms">
    <h2>Form library</h2>
    <p class="hint">Lock the metre first, then chase the rhyme. Pick a form to load its skeleton into the editor.</p>
    <div class="formgrid" id="formgrid"></div>
  </section>

  <!-- RHYME -->
  <section class="panel" id="rhyme">
    <h2>Rhyme finder</h2>
    <p class="hint">Perfect rhymes share the final stressed vowel and everything after it. Near rhymes share the vowel alone — looser, often fresher.</p>
    <div class="rhyme-search">
      <input id="rword" placeholder="Enter a word, e.g. light">
      <button class="btn" id="rgo">Find</button>
    </div>
    <div id="rhymeout"></div>
  </section>

  <!-- EXERCISES -->
  <section class="panel" id="exercises">
    <h2>Guided exercises</h2>
    <p class="hint">Short drills that build the ear before the eye. Work them in order or dip in.</p>
    <div class="exlist" id="exlist"></div>
  </section>

  <!-- FURTHER READING -->
  <section class="panel" id="reading">
    <h2>Further reading</h2>
    <p class="hint">Books on metre, rhyme and form — from quick practical guides to fuller studies. Pair any of them with the scansion tool: read a principle, then test it on a line.</p>
    <div class="reslist" id="readinglist"></div>
    <details class="addbox">
      <summary>+ Add a book</summary>
      <div class="addform">
        <input id="r_reading_title" placeholder="Title (required)">
        <input id="r_reading_detail" placeholder="Author">
        <input id="r_reading_kind" placeholder="Kind (e.g. Practical guide)">
        <input id="r_reading_url" placeholder="Link (optional)">
        <textarea id="r_reading_note" placeholder="A note on why it's useful"></textarea>
        <button class="btn" onclick="addResource('reading')">Add to list</button>
      </div>
    </details>
  </section>

  <!-- WEBSITES -->
  <section class="panel" id="websites">
    <h2>Useful websites</h2>
    <p class="hint">Free references and archives. Glossaries explain the terms; the reading and listening archives train the ear.</p>
    <div class="reslist" id="websiteslist"></div>
    <details class="addbox">
      <summary>+ Add a website</summary>
      <div class="addform">
        <input id="r_websites_title" placeholder="Site name (required)">
        <input id="r_websites_url" placeholder="Link (e.g. https://…)">
        <textarea id="r_websites_note" placeholder="A note on why it's useful"></textarea>
        <button class="btn" onclick="addResource('websites')">Add to list</button>
      </div>
    </details>
  </section>

  <!-- MEDIA -->
  <section class="panel" id="media">
    <h2>Media</h2>
    <p class="hint">Podcasts and videos. Hearing poems read aloud is the fastest way to feel where the stresses really fall.</p>
    <div class="reslist" id="medialist"></div>
    <details class="addbox">
      <summary>+ Add a podcast or video</summary>
      <div class="addform">
        <input id="r_media_title" placeholder="Name (required)">
        <input id="r_media_kind" placeholder="Kind (e.g. Podcast, Video)">
        <input id="r_media_detail" placeholder="By / host / channel">
        <input id="r_media_url" placeholder="Link (e.g. https://…)">
        <textarea id="r_media_note" placeholder="A note on why it's useful"></textarea>
        <button class="btn" onclick="addResource('media')">Add to list</button>
      </div>
    </details>
  </section>

  <!-- SAVED -->
  <section class="panel" id="saved">
    <h2>Saved poems</h2>
    <p class="hint">Stored on this Pi. Click a title to load it back into the editor.</p>
    <div class="poemlist" id="poemlist"></div>
  </section>
</div>
<div class="toast" id="toast"></div>

<script>
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let currentId=null, scanTimer=null;

// ---- API base prefix ----
// The app is served at "/" in local dev (localhost:8200/) but under a path
// prefix in production (…ts.net/bardachd/). The backend is the same either way
// — Tailscale strips the prefix before the request reaches it — but the browser
// must send fetches to the prefixed path or they 404. So we derive the prefix
// from where the page itself was loaded and build every fetch URL from it.
//   at "/"          -> API === "/"          -> fetch(API+"api/scan") = /api/scan
//   at "/bardachd/" -> API === "/bardachd/" -> fetch(API+"api/scan") = /bardachd/api/scan
// The regex strips any trailing filename (e.g. /bardachd/index.html) back to
// its directory, so it works whether the URL ends in "/" or a page name.
const API = location.pathname.replace(/[^/]*$/, '') || '/';

function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),1800);}

// tabs
$$('nav.tabs button').forEach(b=>b.onclick=()=>{
  $$('nav.tabs button').forEach(x=>x.classList.remove('on'));
  $$('.panel').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); $('#'+b.dataset.tab).classList.add('on');
  if(b.dataset.tab==='saved') loadPoems();
});

// ---- scansion ----
async function scan(){
  const text=$('#draft').value;
  if(!text.trim()){$('#scan').innerHTML='<p class="empty">Lines appear here as you type.</p>';return;}
  const r=await fetch(API+'api/scan',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text,form:$('#form').value})});
  const d=await r.json();
  $('#ghostkey').style.display = d.has_target ? 'inline' : 'none';
  $('#scan').innerHTML=d.lines.map(renderLine).join('')||'<p class="empty">—</p>';
}
function renderLine(l){
  const hasTarget = !!l.target;
  const marks = l.diff ? l.diff.marks : null;
  const n = hasTarget ? Math.max(l.syllables.length, l.target.length) : l.syllables.length;
  let cols='';
  for(let i=0;i<n;i++){
    const a = l.syllables[i];          // actual stress char or undefined
    const t = hasTarget ? l.target[i] : undefined;  // target stress char
    const mark = marks ? marks[i] : 'ok';
    // ghost (target) dot sits above; faint, shows the ideal beat
    let ghost='';
    if(hasTarget){
      ghost = (t!==undefined)
        ? `<span class="ghost ${t==='1'?'gs':''}">●</span>`
        : `<span class="ghost empty-slot">·</span>`;
    }
    // actual dot, coloured by how it compares
    let actual;
    if(a===undefined){
      actual = `<span class="dot off-missing">○</span>`;   // metre wants a syllable here
    }else{
      const stressed = a==='1';
      let cls = stressed?'s':'';
      if(mark==='off') cls += ' miss';
      if(mark==='extra') cls += ' extra';
      actual = `<span class="dot ${cls}">${a==='?'?'◌':'●'}</span>`;
    }
    const w=l.syllable_words[i]||'';
    cols += `<div class="syl">${ghost}${actual}`+
            `<span class="w">${esc(w)}</span></div>`;
  }
  const m=l.metre;
  const warn=l.unknown_words.length?
    `<span class="warn"> · not in dictionary: ${l.unknown_words.map(esc).join(', ')}</span>`:'';
  let badge='';
  if(l.diff){
    const pct = l.diff.match===null ? '—' : Math.round(l.diff.match*100)+'%';
    const gap = l.diff.syllable_gap;
    let gaptxt = gap===0 ? '' : (gap>0?` · ${gap} over`:` · ${-gap} short`);
    const cls = (l.diff.match!==null && l.diff.match>=0.85) ? 'good'
              : (l.diff.match!==null && l.diff.match>=0.6) ? 'mid' : 'low';
    badge = `<span class="badge ${cls}">${pct} on form${gaptxt}</span>`;
  }
  return `<div class="scanline"><div class="sylrow ${hasTarget?'with-ghost':''}">${cols}</div>`+
    `<div class="meta"><b>${esc(m.name)}</b> · ${l.syllable_count} syllables${warn} ${badge}</div></div>`;
}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
$('#draft').addEventListener('input',()=>{clearTimeout(scanTimer);scanTimer=setTimeout(scan,400);});
$('#form').addEventListener('change',scan);

// ---- save / load / export ----
function poemPayload(){return {title:$('#title').value||'Untitled',
  form:$('#form').value, body:$('#draft').value};}
$('#save').onclick=async()=>{
  const p=poemPayload();
  if(currentId){await fetch(API+'api/poems/'+currentId,{method:'PUT',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});}
  else{const r=await fetch(API+'api/poems',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
    currentId=(await r.json()).id;}
  toast('Saved');
};
$('#newp').onclick=()=>{currentId=null;$('#title').value='Untitled';
  $('#draft').value='';scan();toast('New poem');};
$('#export').onclick=async()=>{
  if(!currentId){toast('Save first');return;}
  const r=await fetch(API+'api/poems/'+currentId+'/export');const d=await r.json();
  const blob=new Blob([d.content],{type:'text/plain'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=d.filename;a.click();
};
async function loadPoems(){
  const r=await fetch(API+'api/poems');const list=await r.json();
  $('#poemlist').innerHTML=list.length?list.map(p=>
    `<div class="poemrow"><div><div class="t">${esc(p.title)}</div>`+
    `<div class="m">${esc(p.form)} · ${p.updated}</div></div>`+
    `<div class="acts"><button class="btn ghost" onclick="openPoem(${p.id})">Open</button>`+
    `<button class="btn ghost" onclick="delPoem(${p.id})">Delete</button></div></div>`
  ).join(''):'<p class="empty">No poems yet.</p>';
}
async function openPoem(id){
  const r=await fetch(API+'api/poems/'+id);const p=await r.json();
  currentId=id;$('#title').value=p.title;$('#form').value=p.form;$('#draft').value=p.body;
  $$('nav.tabs button').forEach(x=>x.classList.remove('on'));
  $$('.panel').forEach(x=>x.classList.remove('on'));
  $('nav.tabs button[data-tab=write]').classList.add('on');$('#write').classList.add('on');
  scan();
}
async function delPoem(id){await fetch(API+'api/poems/'+id,{method:'DELETE'});loadPoems();toast('Deleted');}

// ---- forms ----
async function loadForms(){
  const r=await fetch(API+'api/forms');const f=await r.json();
  const sel=$('#form');sel.innerHTML='<option value="free">Free verse</option>';
  $('#formgrid').innerHTML=Object.entries(f).map(([k,v])=>{
    sel.innerHTML+=`<option value="${k}">${esc(v.name)}</option>`;
    const scheme=(v.rhyme_scheme&&v.rhyme_scheme.length)?
      `<dt>Rhyme map</dt><dd><div class="scheme">`+
      v.rhyme_scheme.map(s=>`<span>${esc(s)}</span>`).join('')+`</div></dd>`:'';
    return `<div class="formcard"><h3>${esc(v.name)}</h3>`+
      `<p class="meta">${v.lines} lines</p><dl>`+
      `<dt>Metre</dt><dd>${esc(v.metre)}</dd>`+
      `<dt>Rhyme</dt><dd>${esc(v.rhyme)}</dd>${scheme}</dl>`+
      `<p class="note">${esc(v.note)}</p>`+
      `<button class="btn usebtn" onclick="useForm('${k}',${JSON.stringify(v.lines)})">Load skeleton</button></div>`;
  }).join('');
}
function useForm(key,lines){
  $('#form').value=key;
  $('#draft').value=Array(lines).fill('').map((_,i)=>'').join('\n');
  currentId=null;$('#title').value='Untitled';
  $$('nav.tabs button').forEach(x=>x.classList.remove('on'));
  $$('.panel').forEach(x=>x.classList.remove('on'));
  $('nav.tabs button[data-tab=write]').classList.add('on');$('#write').classList.add('on');
  $('#draft').focus();toast('Form loaded — '+lines+' lines');
}

// ---- rhyme ----
async function findRhymes(){
  const w=$('#rword').value.trim();if(!w)return;
  const r=await fetch(API+'api/rhymes/'+encodeURIComponent(w));const d=await r.json();
  const group=(title,arr)=>arr.length?
    `<div class="rhyme-group"><h4>${title} (${arr.length})</h4><div class="chips">`+
    arr.map(x=>`<span class="chip">${esc(x)}</span>`).join('')+`</div></div>`:'';
  $('#rhymeout').innerHTML=(group('Perfect',d.perfect)+group('Near / slant',d.near))||
    '<p class="empty">No rhymes found — the word may not be in the dictionary.</p>';
}
$('#rgo').onclick=findRhymes;
$('#rword').addEventListener('keydown',e=>{if(e.key==='Enter')findRhymes();});

// ---- exercises ----
async function loadExercises(){
  const r=await fetch(API+'api/exercises');const ex=await r.json();
  $('#exlist').innerHTML=ex.map(e=>
    `<div class="ex"><div class="skill">${esc(e.skill)}</div>`+
    `<h3>${esc(e.title)}</h3><p>${esc(e.brief)}</p></div>`).join('');
}

// ---- resource helpers ----
// A delete control, shown only on user-added (non-builtin) items.
function delBtn(section,item){
  return item.builtin ? '' :
    `<div><span class="added">added</span></div>`+
    `<button class="del" onclick="deleteResource('${section}',${item.id})">Remove</button>`;
}
function linkRow(url){
  return url ? `<p class="link"><a href="${esc(url)}" target="_blank" rel="noopener">${esc(url)}</a></p>` : '';
}
function titleLink(name,url){
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(name)}</a>` : esc(name);
}

// ---- further reading ----
async function loadReading(){
  const r=await fetch(API+'api/reading');const items=await r.json();
  $('#readinglist').innerHTML=items.map(b=>
    `<div class="res"><div class="kind">${esc(b.kind)}</div>`+
    `<h3>${titleLink(b.title,b.url)}</h3>`+
    `<p class="by">${esc(b.author||'')}</p>`+
    `<p>${esc(b.note)}</p>`+
    linkRow(b.url)+
    delBtn('reading',b)+`</div>`).join('');
}

// ---- websites ----
async function loadWebsites(){
  const r=await fetch(API+'api/websites');const items=await r.json();
  $('#websiteslist').innerHTML=items.map(w=>
    `<div class="res"><div class="kind">Website</div>`+
    `<h3>${titleLink(w.name,w.url)}</h3>`+
    `<p>${esc(w.note)}</p>`+
    linkRow(w.url)+
    delBtn('websites',w)+`</div>`).join('');
}

// ---- media ----
async function loadMedia(){
  const r=await fetch(API+'api/media');const items=await r.json();
  $('#medialist').innerHTML=items.map(m=>
    `<div class="res"><div class="kind">${esc(m.kind)}</div>`+
    `<h3>${titleLink(m.name,m.url)}</h3>`+
    `<p class="by">${esc(m.by||'')}</p>`+
    `<p>${esc(m.note)}</p>`+
    linkRow(m.url)+
    delBtn('media',m)+`</div>`).join('');
}

// ---- add / delete a resource ----
const RELOADERS={reading:loadReading,websites:loadWebsites,media:loadMedia};
async function addResource(section){
  const g=id=>{const el=$('#r_'+section+'_'+id);return el?el.value.trim():'';};
  const payload={title:g('title'),detail:g('detail'),kind:g('kind'),
                 url:g('url'),note:g('note')};
  if(!payload.title){toast('A title or name is required');return;}
  const r=await fetch(API+'api/resources/'+section,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(!r.ok){toast('Could not add');return;}
  ['title','detail','kind','url','note'].forEach(id=>{
    const el=$('#r_'+section+'_'+id);if(el)el.value='';});
  const box=$('#'+section+' .addbox');if(box)box.removeAttribute('open');
  await RELOADERS[section]();toast('Added');
}
async function deleteResource(section,id){
  await fetch(API+'api/resources/'+section+'/'+id,{method:'DELETE'});
  await RELOADERS[section]();toast('Removed');
}

loadForms();loadExercises();loadReading();loadWebsites();loadMedia();
</script>
</body>
</html>"""
