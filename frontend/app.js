var S = { tab: 'gf', apiBase: 'http://localhost:8000', neo4jUp: true, hist: [], bench: null, results: [] };

var TC = {
  gf: { label: 'Graph-first', cls: 's-gf', tc: 'tag-pu', color: '#a78bfa' },
  sf: { label: 'SQL-first',   cls: 's-sf', tc: 'tag-rd', color: '#f87171' },
  pg: { label: 'Pure Graph',  cls: 's-pg', tc: 'tag-am', color: '#fbbf24' },
  ps: { label: 'Pure SQL',    cls: 's-ps', tc: 'tag-cy', color: '#22d3ee' }
};

var LANGS = { gf: 'Cypher + SQL', sf: 'SQL + Cypher N\u00d7', pg: 'Cypher only', ps: 'Recursive CTE (SQL only)' };


function navTo(e, id) {
  e.preventDefault();
  document.querySelectorAll('.ni').forEach(function (n) { n.classList.remove('act') });
  document.getElementById('nav-' + id).classList.add('act');
}

// ── TAB SWITCH ──
function setTab(e, t) {
  S.tab = t;
  ['gf', 'sf', 'pg', 'ps'].forEach(function (k) {
    var el = document.getElementById('tab-' + k);
    el.className = 'stab' + (k === t ? ' ' + TC[k].cls : '');
  });
  var c = TC[t];
  var st = document.getElementById('strat-tag');
  st.textContent = c.label; st.className = 'tag ' + c.tc;
  var bd = document.getElementById('bd-tag');
  bd.textContent = c.label; bd.className = 'tag ' + c.tc;
  document.getElementById('qlang').textContent = LANGS[t];
  document.getElementById('qlang').style.color = c.color;
  document.getElementById('strat-note').style.borderLeftColor = c.color;
  updateQCode();
  if (S.bench) updateBreakdown(t, S.bench);
  if (S.bench) drawChart(S.bench);
}

// ── CONTROLS ──
function ctrl() {
  return {
    actor: document.getElementById('c-actor').value.trim() || 'Kevin Bacon',
    depth: document.getElementById('c-depth').value,
    rev: (parseInt(document.getElementById('c-rev').value) || 100) * 1000000,
    limit: document.getElementById('c-limit').value
  };
}

// ── QUERY CODE GENERATOR ──
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function kw(s) { return '<span class="kw">' + s + '</span>'; }
function fn(s) { return '<span class="fn">' + s + '</span>'; }
function st(s) { return '<span class="str">' + s + '</span>'; }
function nm(s) { return '<span class="num">' + s + '</span>'; }
function cm(s) { return '<span class="cm">' + s + '</span>'; }

function buildQuery(t, c) {
  var a = c.actor, d = c.depth, r = c.rev.toLocaleString(), l = c.limit;
  if (t === 'gf') return [
    cm('-- Step 1: Cypher (Neo4j) \u2014 BFS traversal'),
    kw('MATCH') + ' (kb:' + fn('Actor') + ' {' + st('name') + ': ' + st('"' + a + '"') + '})' +
    '\n      -[:' + kw('ACTED_IN') + '*' + nm('1..' + d) + ']->(co:' + fn('Actor') + ')',
    kw('RETURN') + ' ' + kw('DISTINCT') + ' co.actor_id ' + kw('AS') + ' id',
    cm('-- \u2192 returns ~100\u2013500 IDs only'),
    '',
    cm('-- Step 2: SQL (PostgreSQL) \u2014 revenue filter'),
    kw('SELECT') + ' a.name, m.title, m.revenue, bn.depth',
    kw('FROM') + ' actors a',
    kw('JOIN') + ' cast_rel cr  ' + kw('ON') + ' cr.actor_id = a.id',
    kw('JOIN') + ' movies   m   ' + kw('ON') + ' m.id = cr.movie_id',
    kw('WHERE') + ' a.id ' + kw('IN') + ' (:' + st('bacon_ids') + ')',
    '  ' + kw('AND') + ' m.revenue > ' + nm(r),
    kw('ORDER BY') + ' m.revenue ' + kw('DESC') + ' ' + kw('LIMIT') + ' ' + nm(l) + ';'
  ].join('\n');
  
  if (t === 'sf') return [
    cm('-- Step 1: SQL \u2014 scan qualifying actors (LARGE SET!)'),
    kw('SELECT') + ' ' + kw('DISTINCT') + ' cr.actor_id',
    kw('FROM') + ' cast_rel cr',
    kw('JOIN') + ' movies m ' + kw('ON') + ' m.id = cr.movie_id',
    kw('WHERE') + ' m.revenue > ' + nm(r) + ';',
    cm('-- \u2192 may return 5,000\u201315,000 actor candidates!'),
    '',
    cm('-- Step 2: Cypher called \u00d7N per actor (BOTTLENECK)'),
    kw('MATCH') + ' path = (:' + fn('Actor') + '{' + st('id') + ':' + st('$id') + '})' +
    '\n             -[:' + kw('ACTED_IN') + '*' + nm('1..' + d) + ']->' +
    '\n             (:' + fn('Actor') + '{' + st('name') + ':' + st('"' + a + '"') + '})',
    kw('RETURN') + ' ' + fn('length') + '(path) ' + kw('AS') + ' bacon_num',
    cm('-- O(N \u00d7 BFS): 10K actors \u00d7 0.04ms each = 400ms bottleneck')
  ].join('\n');
  
  if (t === 'pg') return [
    cm('-- Pure Graph: Cypher only in Neo4j (revenue as node property)'),
    kw('MATCH') + ' (kb:' + fn('Actor') + '{' + st('name') + ':' + st('"' + a + '"') + '})',
    '      -[:' + kw('ACTED_IN') + '*' + nm('1..' + d) + ']->(co:' + fn('Actor') + ')',
    '      -[:' + kw('ACTED_IN') + ']->(m:' + fn('Movie') + ')',
    kw('WHERE') + ' m.revenue > ' + nm(r),
    '  ' + kw('AND') + ' co <> kb',
    kw('RETURN') + ' ' + kw('DISTINCT'),
    '  co.name    ' + kw('AS') + ' actor_name,',
    '  m.title    ' + kw('AS') + ' movie_title,',
    '  m.revenue  ' + kw('AS') + ' revenue,',
    '  m.year     ' + kw('AS') + ' year,',
    '  ' + fn('length') + '(' + fn('shortestPath') + '((kb)-[:' + kw('ACTED_IN') + '*]->(co)))',
    '             ' + kw('AS') + ' bacon_num',
    kw('ORDER BY') + ' m.revenue ' + kw('DESC') + ' ' + kw('LIMIT') + ' ' + nm(l)
  ].join('\n');
  
  // ps
  return [
    cm('-- Pure SQL: Recursive CTE (PostgreSQL only, no Neo4j)'),
    kw('WITH RECURSIVE') + ' bacon_net ' + kw('AS') + '(',
    '  ' + cm('-- Anchor: direct co-actors of "'+a+'"'),
    '  ' + kw('SELECT') + ' cr2.actor_id, ' + nm('1') + ' ' + kw('AS') + ' depth,',
    '         ' + kw('ARRAY') + '[kb.id, cr2.actor_id] ' + kw('AS') + ' visited',
    '  ' + kw('FROM') + ' actors kb',
    '  ' + kw('JOIN') + ' cast_rel cr1 ' + kw('ON') + ' cr1.actor_id = kb.id',
    '  ' + kw('JOIN') + ' cast_rel cr2 ' + kw('ON') + ' cr2.movie_id  = cr1.movie_id',
    '  ' + kw('WHERE') + ' kb.name = ' + st("'" + a + "'"),
    '    ' + kw('AND') + ' cr2.actor_id <> kb.id',
    '  ' + kw('UNION ALL'),
    '  ' + cm('-- Recursive: extend network hop-by-hop'),
    '  ' + kw('SELECT') + ' cr4.actor_id, bn.depth+' + nm('1') + ',',
    '         bn.visited || cr4.actor_id',
    '  ' + kw('FROM') + ' bacon_net bn',
    '  ' + kw('JOIN') + ' cast_rel cr3 ' + kw('ON') + ' cr3.actor_id = bn.actor_id',
    '  ' + kw('JOIN') + ' cast_rel cr4 ' + kw('ON') + ' cr4.movie_id  = cr3.movie_id',
    '  ' + kw('WHERE') + ' bn.depth < ' + nm(d),
    '    ' + kw('AND NOT') + '(cr4.actor_id = ' + kw('ANY') + '(bn.visited))',
    ')',
    kw('SELECT') + ' a.name, m.title, m.revenue, bn.depth ' + kw('AS') + ' bacon_num',
    kw('FROM') + ' bacon_net bn',
    kw('JOIN') + ' actors    a  ' + kw('ON') + ' a.id = bn.actor_id',
    kw('JOIN') + ' cast_rel  cr ' + kw('ON') + ' cr.actor_id = a.id',
    kw('JOIN') + ' movies    m  ' + kw('ON') + ' m.id = cr.movie_id',
    kw('WHERE') + ' m.revenue > ' + nm(r),
    kw('ORDER BY') + ' m.revenue ' + kw('DESC') + ' ' + kw('LIMIT') + ' ' + nm(l) + ';'
  ].join('\n');
}

function updateQCode() { var c = ctrl(); document.getElementById('qcode').innerHTML = buildQuery(S.tab, c); }

// ── API HEALTH ──
async function checkHealth() {
  var base = document.getElementById('c-api').value.trim(); S.apiBase = base;
  try {
    var r = await fetch(base + '/health', { signal: AbortSignal.timeout(3000) });
    if (r.ok) { var d = await r.json(); setConn(true, d); } else setConn(false, null);
  } catch (e) { setConn(false, null); }
}

function setConn(ok, d) {
  var ad = document.getElementById('api-dot'), al = document.getElementById('api-lbl');
  var sysDot = document.getElementById('sys-dot'), sysSt = document.getElementById('sys-status');
  var apiNode = document.getElementById('dot-api2'), apiInf = document.getElementById('inf-api');
  if (ok) {
    ad.className = 'api-dot ok'; al.textContent = 'FastAPI connected';
    sysDot.className = 'ldot'; sysSt.textContent = 'All nodes healthy';
    apiNode.className = 'dot dot-g'; apiInf.textContent = '8000 \u00b7 healthy' + (d && d.version ? ' \u00b7 v' + d.version : '');
    if (d) {
      var neo = d.neo4j !== undefined ? d.neo4j : true;
      document.getElementById('dot-neo4j').className = 'dot ' + (neo ? 'dot-g' : 'dot-r');
      document.getElementById('inf-neo4j').textContent = neo ? ('7687 \u00b7 ' + (d.neo4j_nodes || 'ok')) : 'unreachable';
      var pg = d.postgres !== undefined ? d.postgres : true;
      document.getElementById('dot-pg').className = 'dot ' + (pg ? 'dot-g' : 'dot-r');
      document.getElementById('inf-pg').textContent = pg ? ('5432 \u00b7 ' + (d.pg_rows || 'ok')) : 'unreachable';
    }
  } else {
    ad.className = 'api-dot err'; al.textContent = 'API offline \u2014 mock data';
    sysSt.textContent = 'Demo mode'; apiNode.className = 'dot dot-a'; apiInf.textContent = 'offline \u00b7 mock mode';
  }
}

// ── RUN QUERY ──
async function runQuery() {
  var c = ctrl(), btn = document.getElementById('run-btn'); // lấy nhanh toàn bộ giá trị cấu hình hiện tại từ các ô nhập liệu
  btn.disabled = true; btn.classList.add('busy'); btn.textContent = 'Running\u2026';
  document.getElementById('spin').style.display = 'inline-block';
  var t0 = performance.now();
  try {
    var url = S.apiBase + '/query/bacon?' + new URLSearchParams({ actor: c.actor, depth: c.depth, min_revenue: c.rev, limit: c.limit, strategy: S.tab });
    var r = await fetch(url, { signal: AbortSignal.timeout(30000) });//Gửi một HTTP Request (GET) tới API Backend
    var elapsed = performance.now() - t0;
    if (!r.ok) throw new Error('HTTP ' + r.status); //Nếu Server phản hồi lỗi (ví dụ lỗi 404, 500), đoạn code sẽ chủ động ném ra một ngoại lệ để nhảy xuống khối catch xử lý.
    var data = await r.json();
    setConn(true, null); handleResult(data, elapsed);
  } catch (err) {
    var elapsed = performance.now() - t0;
    toast('API offline \u2014 showing mock data');
    handleResult(mockData(c), null);
  } finally {
    btn.disabled = false; btn.classList.remove('busy'); btn.textContent = '\u25b6 Run Query';
    document.getElementById('spin').style.display = 'none';
  }
}

function handleResult(data, clientMs) {
  var b = data.benchmark || mockBench(clientMs);//Lấy dữ liệu thời gian chạy (benchmark) của 4 kịch bản từ Backend. Nếu mạng lỗi/offline, nó sẽ tự động kích hoạt hàm mockBench để tự tạo thời gian ảo.
  S.bench = b; S.results = data.results || [];
  var ms = b[S.tab] || clientMs || 150;
  var psMs = b.ps || 1840;
  var spd = psMs / ms;
  // metrics
  iH('m-actors', data.actors_found || S.results.length);
  document.getElementById('m-actors-s').textContent = 'depth ' + ctrl().depth + ' hops';
  iH('m-movies', data.movies_matched || S.results.length);
  iH('m-time', Math.round(ms) + '<sub> ms</sub>');
  document.getElementById('m-strat').textContent = TC[S.tab].label;
  iH('m-speed', spd.toFixed(1) + '<sub>\u00d7</sub>');
  iH('m-inter', (data.intermediate_set || '?') + ' rows');
  var tt = document.getElementById('time-tag');
  tt.textContent = Math.round(ms) + ' ms';
  tt.className = 'tag ' + (ms < 300 ? 'tag-gr' : ms < 800 ? 'tag-am' : 'tag-rd');
  document.getElementById('chart-sub').textContent =
    'actor: ' + ctrl().actor + ' \u00b7 depth: ' + ctrl().depth + ' \u00b7 min $' + document.getElementById('c-rev').value + 'M';
  drawChart(b);
  updateBreakdown(S.tab, b);
  renderTable(S.results);
  S.hist.push(Math.round(ms));
  if (S.hist.length > 4) S.hist = S.hist.slice(-4);
  renderHist();
}

function iH(id, h) { var e = document.getElementById(id); if (e) e.innerHTML = h; }

// ── MOCK DATA ──
function mockBench(ms) {
  var base = ms || (120 + Math.random() * 50);
  return { gf: Math.round(base), sf: Math.round(base * 5.8), pg: Math.round(base * 1.35), ps: Math.round(base * 12.9) };
}

function mockData(c) {
  var pool = [
    { name: 'Tom Hanks', initials: 'TH', ab: 'rgba(167,139,250,.15)', af: '#a78bfa', movie: 'Forrest Gump', revenue: 678e6, year: 1994, bacon: 1 },
    { name: 'Keira Knightley', initials: 'KK', ab: 'rgba(244,114,182,.12)', af: '#f472b6', movie: 'Pirates of Caribbean', revenue: 654e6, year: 2003, bacon: 2 },
    { name: 'Julia Roberts', initials: 'JR', ab: 'rgba(74,222,128,.1)', af: '#4ade80', movie: 'Pretty Woman', revenue: 463e6, year: 1990, bacon: 1 },
    { name: 'Denzel Washington', initials: 'DW', ab: 'rgba(34,211,238,.1)', af: '#22d3ee', movie: 'Philadelphia', revenue: 206e6, year: 1993, bacon: 1 },
    { name: 'Gene Hackman', initials: 'GH', ab: 'rgba(251,191,36,.1)', af: '#fbbf24', movie: 'The Firm', revenue: 270e6, year: 1993, bacon: 2 },
    { name: 'Matt Damon', initials: 'MD', ab: 'rgba(248,113,113,.1)', af: '#f87171', movie: 'Good Will Hunting', revenue: 225e6, year: 1997, bacon: 2 },
    { name: 'Gary Oldman', initials: 'GO', ab: 'rgba(167,139,250,.1)', af: '#a78bfa', movie: 'Air Force One', revenue: 315e6, year: 1997, bacon: 1 },
    { name: 'Robin Wright', initials: 'RW', ab: 'rgba(34,211,238,.08)', af: '#22d3ee', movie: 'Forrest Gump', revenue: 678e6, year: 1994, bacon: 2 }
  ].filter(function (r) { return r.revenue >= c.rev && r.bacon <= parseInt(c.depth) }).slice(0, parseInt(c.limit));
  
  return {
    results: pool, actors_found: pool.length + Math.floor(Math.random() * 200 + 50),
    movies_matched: pool.length,
    intermediate_set: S.tab === 'gf' || S.tab === 'pg' ? Math.floor(Math.random() * 300 + 100) : Math.floor(Math.random() * 10000 + 5000),
    benchmark: mockBench(null)
  };
}

// ── CHART ──
function drawChart(b) {
  var area = document.getElementById('chart-area');
  document.getElementById('chart-empty').style.display = 'none';
  document.getElementById('chart-xlabels').style.display = 'flex';
  area.querySelectorAll('.bar-col').forEach(function (e) { e.remove() });
  var vals = [
    { key: 'gf', label: 'Graph-first', ms: b.gf || 0, color: '#a78bfa' },
    { key: 'sf', label: 'SQL-first', ms: b.sf || 0, color: '#f87171' },
    { key: 'pg', label: 'Pure Graph', ms: b.pg || 0, color: '#fbbf24' },
    { key: 'ps', label: 'Pure SQL', ms: b.ps || 0, color: '#22d3ee' }
  ];
  var maxMs = Math.max.apply(null, vals.map(function (v) { return v.ms })) || 1;
  var maxH = 150;
  var grid = document.getElementById('chart-grid');
  grid.innerHTML = [0.25, 0.5, 0.75, 1.0].map(function (f) {
    return '<div style="position:absolute;bottom:' + (f * maxH) + 'px;left:0;right:0;border-top:1px dashed rgba(255,255,255,.05)">'
      + '<span style="font-size:9px;font-family:var(--mono);color:var(--txt3);background:var(--bg2);padding:0 3px">' + Math.round(maxMs * f) + 'ms</span></div>';
  }).join('');
  vals.forEach(function (v) {
    var h = Math.max(v.ms / maxMs * maxH, 3);
    var isA = S.tab === v.key;
    var col = document.createElement('div');
    col.className = 'bar-col';
    col.innerHTML = '<div class="bar-val" style="color:' + v.color + (isA ? ';font-weight:700' : '') + '">' + Math.round(v.ms) + 'ms</div>'
      + '<div class="bar-body" style="height:' + h + 'px;background:' + v.color + ';opacity:' + (isA ? 1 : .38) + '"></div>'
      + '<div class="bar-lbl" style="color:' + (isA ? v.color : 'var(--txt3)') + ';font-weight:' + (isA ? 600 : 400) + '">' + v.label + '</div>';
    area.appendChild(col);
  });
}

// ── BREAKDOWN ──
var BD = {
  gf: [{ l: 'Graph BFS', p: 35, c: '#a78bfa' }, { l: 'Net transfer', p: 28, c: '#4ade80' }, { l: 'SQL filter', p: 37, c: '#5ba3f5' }],
  sf: [{ l: 'SQL scan', p: 30, c: '#5ba3f5' }, { l: 'Net transfer', p: 20, c: '#4ade80' }, { l: 'N\u00d7Graph lookup', p: 50, c: '#f87171' }],
  pg: [{ l: 'Cypher BFS', p: 55, c: '#fbbf24' }, { l: 'Rev. filter', p: 30, c: '#f87171' }, { l: 'Sort+return', p: 15, c: '#a78bfa' }],
  ps: [{ l: 'CTE anchor', p: 15, c: '#22d3ee' }, { l: 'Recursive join', p: 65, c: '#f87171' }, { l: 'Final filter', p: 20, c: '#5ba3f5' }]
};

var BN = {
  gf: '\u25b8 Small BFS result (~200\u2013500 IDs) \u2192 SQL WHERE IN is cheap. Best cross-model strategy O(V+E).',
  sf: '\u25b8 SQL returns 5K\u201315K candidates \u2192 N\u00d7graph lookups = bottleneck. Avoid for large datasets.',
  pg: '\u25b8 All logic stays in Neo4j. Revenue must be a node property. No SQL overhead. 2nd best.',
  ps: '\u25b8 Recursive CTE rewrites graph as relational. E\u00b2 self-joins \u2192 slowest (13\u00d7). Fallback when Neo4j is down.'
};

function updateBreakdown(t, b) {
  var ms = (b && b[t]) || 0, defs = BD[t];
  var tbar = document.getElementById('tbar');
  tbar.innerHTML = defs.map(function (d) {
    return '<div class="tseg" style="width:' + d.p + '%;background:' + d.c + '22;color:' + d.c + '">' + d.l + ' ' + Math.round(ms * d.p / 100) + 'ms</div>';
  }).join('');
  var rows = document.getElementById('bd-rows');
  rows.innerHTML = defs.map(function (d) {
    return '<div class="brow"><span class="bl">' + d.l + '</span>'
      + '<div class="btrack"><div class="bfill" style="width:' + d.p + '%;background:' + d.c + '"></div></div>'
      + '<span class="bv">' + Math.round(ms * d.p / 100) + ' ms</span></div>';
  }).join('')
    + '<div class="brow tot"><span class="bl">Total</span>'
    + '<div class="btrack"><div class="bfill" style="width:100%;background:' + TC[t].color + ';opacity:.3"></div></div>'
    + '<span class="bv">' + Math.round(ms) + ' ms</span></div>';
  var note = document.getElementById('strat-note');
  note.textContent = BN[t]; note.style.display = 'block'; note.style.borderLeftColor = TC[t].color;
}

// ── TABLE ──
var AVC = [['rgba(167,139,250,.15)', '#a78bfa'], ['rgba(34,211,238,.1)', '#22d3ee'], ['rgba(74,222,128,.1)', '#4ade80'],
['rgba(248,113,113,.1)', '#f87171'], ['rgba(251,191,36,.1)', '#fbbf24'], ['rgba(244,114,182,.1)', '#f472b6']];

function renderTable(rows) {
  var tb = document.getElementById('rtbody');
  var ct = document.getElementById('rows-tag');
  if (!rows || !rows.length) {
    tb.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="empty-text">no results matched your filters</div></div></td></tr>';
    ct.textContent = '0 rows'; return;
  }
  ct.textContent = rows.length + ' rows';
  tb.innerHTML = rows.map(function (r, i) {
    var ac = AVC[i % AVC.length];
    var ini = r.initials || (r.name || '??').split(' ').slice(0, 2).map(function (w) { return (w || '?')[0]; }).join('');
    var rev = r.revenue || 0;
    var rs = rev >= 1e9 ? '$' + (rev / 1e9).toFixed(2) + 'B' : '$' + Math.round(rev / 1e6) + 'M';
    var bn = r.bacon || r.bacon_num || r.depth || '?';
    var bc = bn <= 1 ? 'tag-pu' : bn <= 2 ? 'tag-cy' : 'tag-am';
    return '<tr>'
      + '<td><div class="avc"><div class="av" style="background:' + ac[0] + ';color:' + ac[1] + '">' + ini + '</div>' + (r.name || r.actor_name || '\u2014') + '</div></td>'
      + '<td>' + (r.movie || r.movie_title || '\u2014') + '</td>'
      + '<td class="money">' + rs + '</td>'
      + '<td class="tc"><span class="tag ' + bc + '">' + bn + '</span></td>'
      + '<td class="tc" style="font-family:var(--mono);font-size:11px;color:var(--txt3)">' + (r.year || '\u2014') + '</td>'
      + '</tr>';
  }).join('');
}

// ── HISTORY BARS ──
function renderHist() {
  var h = S.hist; while (h.length < 4) h.unshift(0);
  var r4 = h.slice(-4), max = Math.max.apply(null, r4) || 1;
  var c = document.getElementById('hist-bars'), l = document.getElementById('hist-lbls');
  c.innerHTML = r4.map(function (v, i) {
    var pct = v / max * 100, isL = i === r4.length - 1;
    return '<div style="flex:1;border-radius:2px 2px 0 0;background:' + (isL ? TC[S.tab].color : 'rgba(167,139,250,.22)') + ';height:' + Math.max(pct, 5) + '%"></div>';
  }).join('');
  l.innerHTML = r4.map(function (v) { return '<span>' + (v > 0 ? v + 'ms' : '\u2014') + '</span>'; }).join('');
}

// ── NODE KILL/RESTORE ──
function killNeo4j() {
  if (!S.neo4jUp) return; S.neo4jUp = false;
  document.getElementById('dot-neo4j').className = 'dot dot-r';
  document.getElementById('inf-neo4j').textContent = 'STOPPED \u2014 connection refused';
  document.getElementById('fbanner').style.display = 'block';
  document.getElementById('sys-dot').className = 'ldot dead';
  document.getElementById('sys-status').textContent = '1 node down';
  document.getElementById('kill-btn').disabled = true;
  document.getElementById('kill-btn').textContent = 'Stopped';
  document.getElementById('time-tag').className = 'tag tag-rd';
  document.getElementById('time-tag').textContent = '503 Error';
  S.hist.push(0); if (S.hist.length > 4) S.hist = S.hist.slice(-4); renderHist();
  toast('Neo4j stopped \u2014 fallback Pure SQL CTE. Expect 13\u00d7 slowdown.');
}

function restoreNeo4j() {
  S.neo4jUp = true;
  document.getElementById('dot-neo4j').className = 'dot dot-g';
  document.getElementById('inf-neo4j').textContent = '7687 \u00b7 reconnecting\u2026';
  document.getElementById('fbanner').style.display = 'none';
  document.getElementById('sys-dot').className = 'ldot';
  document.getElementById('sys-status').textContent = 'All nodes healthy';
  document.getElementById('kill-btn').disabled = false;
  document.getElementById('kill-btn').textContent = 'Stop neo4j';
  toast('Neo4j restarted successfully.');
  setTimeout(checkHealth, 600);
}

// ── UTILS ──
function copyQ() { navigator.clipboard.writeText(document.getElementById('qcode').textContent).then(function () { toast('Query copied!'); }); }
function toast(msg) { var t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block'; setTimeout(function () { t.style.display = 'none'; }, 3000); }

// ── INIT ──
window.addEventListener('load', function () {
  updateQCode();
  checkHealth();
  ['c-actor', 'c-depth', 'c-rev', 'c-limit'].forEach(function (id) {
    document.getElementById(id).addEventListener('input', updateQCode);
  });
  document.getElementById('c-api').addEventListener('change', checkHealth);
  setInterval(checkHealth, 30000);
});