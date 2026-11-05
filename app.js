/*
 * Çengel Bulmaca - web uygulaması.
 * Copyright (c) 2026 Tuna Tuğcu. Tüm hakları saklıdır.
 */
(function () {
  'use strict';

  var E = window.CrosswordEngine;
  var APP_VERSION = '1.8';
  var REMOTE_URL = 'https://raw.githubusercontent.com/tugcu/cengel-bulmaca/main/puzzles.json';
  var BUNDLED_URL = 'puzzles.json';
  var KEY_PLAYED = 'cb_played';
  var KEY_BANK = 'cb_bank';
  var MIN_WORDS = 6;
  var COLOR_EMPTY = '#ffffff';
  var PALETTE = [
    '#FFCDD2', '#C8E6C9', '#BBDEFB', '#FFF59D',
    '#E1BEE7', '#FFE0B2', '#B2EBF2', '#F8BBD0',
    '#DCEDC8', '#D7CCC8', '#CFD8DC', '#FFECB3'
  ];

  var els = {};
  var state = {
    items: null,
    puzzle: null,
    user: null,
    numAt: null,
    startColorAt: null,
    cellEls: null,
    clueEls: null,
    selR: -1,
    selC: -1,
    selDir: E.ACROSS,
    solvedNotified: false
  };

  function $(id) { return document.getElementById(id); }

  function colorFor(i) { return PALETTE[i % PALETTE.length]; }

  function colorOfWord(w) {
    var idx = state.puzzle.words.indexOf(w);
    return idx < 0 ? COLOR_EMPTY : colorFor(idx);
  }

  function setStatus(msg) { els.status.textContent = msg; }

  function compareVersions(a, b) {
    var pa = String(a).split('.');
    var pb = String(b).split('.');
    var n = Math.max(pa.length, pb.length);
    for (var i = 0; i < n; i++) {
      var va = parseInt(pa[i] || '0', 10) || 0;
      var vb = parseInt(pb[i] || '0', 10) || 0;
      if (va !== vb) return va < vb ? -1 : 1;
    }
    return 0;
  }

  function parseBank(text) {
    var b = JSON.parse(text);
    if (!b.puzzles || b.puzzles.length < 10) throw new Error('Bulmaca sayısı yetersiz');
    return {
      version: String(b.version || '1.0'),
      items: b.puzzles.map(function (p) {
        return { id: p.id, topic: p.topic || '', words: p.words };
      })
    };
  }

  function readPlayed() {
    try { return JSON.parse(localStorage.getItem(KEY_PLAYED) || '[]'); } catch (e) { return []; }
  }

  function writePlayed(list) {
    try { localStorage.setItem(KEY_PLAYED, JSON.stringify(list)); } catch (e) { /* depolama dolu */ }
  }

  async function loadBank() {
    var bundled = null;
    try {
      var r = await fetch(BUNDLED_URL, { cache: 'no-cache' });
      bundled = parseBank(await r.text());
    } catch (e) { bundled = null; }

    var cached = null;
    try {
      var text = localStorage.getItem(KEY_BANK);
      if (text) cached = parseBank(text);
    } catch (e) { cached = null; }

    var bank = bundled;
    if (cached && (!bank || compareVersions(cached.version, bank.version) > 0)) bank = cached;
    if (!bank) throw new Error('Bulmaca veritabanı okunamadı');
    return bank;
  }

  // Uzak sürüm daha yeniyse bir sonraki açılış için önbelleğe alır.
  async function checkRemote(currentVersion) {
    try {
      var ctrl = new AbortController();
      var timer = setTimeout(function () { ctrl.abort(); }, 10000);
      var r = await fetch(REMOTE_URL, { cache: 'no-cache', signal: ctrl.signal });
      clearTimeout(timer);
      if (!r.ok) return;
      var text = await r.text();
      var remote = parseBank(text);
      if (compareVersions(remote.version, currentVersion) > 0) {
        localStorage.setItem(KEY_BANK, text);
      }
    } catch (e) { /* ağ yok ya da depo özel: paketteki kopya kullanılır */ }
  }

  function shuffle(list) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = list[i]; list[i] = list[j]; list[j] = t;
    }
    return list;
  }

  // Oynanmamış rastgele bir bulmaca seçer. Hepsi oynandıysa geçmişi sıfırlar.
  function pickPuzzle(items, played) {
    var pool = items.filter(function (it) { return played.indexOf(it.id) < 0; });
    if (pool.length === 0) {
      played.length = 0;
      pool = items.slice();
    }
    shuffle(pool);
    for (var k = 0; k < pool.length; k++) {
      var puzzle = E.build(pool[k].words);
      if (puzzle && puzzle.words.length >= MIN_WORDS) {
        played.push(pool[k].id);
        return { item: pool[k], puzzle: puzzle };
      }
    }
    return null;
  }

  function updateRemaining(played) {
    var left = state.items.filter(function (it) { return played.indexOf(it.id) < 0; }).length;
    els.remaining.textContent = 'Kalan farklı oyun: ' + left;
  }

  function newGame() {
    if (!state.items) return;
    var played = readPlayed();
    var picked = pickPuzzle(state.items, played);
    if (!picked) {
      setStatus('Oynanabilir bulmaca bulunamadı.');
      return;
    }
    writePlayed(played);
    updateRemaining(played);

    state.puzzle = picked.puzzle;
    state.user = [];
    for (var r = 0; r < picked.puzzle.rows; r++) {
      state.user.push(new Array(picked.puzzle.cols).fill(''));
    }
    state.selR = -1;
    state.selC = -1;
    state.selDir = E.ACROSS;
    state.solvedNotified = false;

    els.topic.textContent = picked.item.topic;
    renderClues();
    renderBoard();
    setStatus('');
  }

  function sizeBoard() {
    var p = state.puzzle;
    var avail = els.board.parentElement.clientWidth;
    var byWidth = Math.floor(avail / p.cols);
    var byHeight = Math.floor((window.innerHeight * 0.5) / p.rows);
    var cell = Math.max(18, Math.min(48, byWidth, byHeight));
    document.documentElement.style.setProperty('--cell', cell + 'px');
  }

  function renderBoard() {
    var p = state.puzzle;
    els.board.innerHTML = '';
    els.board.style.setProperty('--cols', p.cols);

    state.numAt = [];
    state.startColorAt = [];
    state.cellEls = [];
    for (var r = 0; r < p.rows; r++) {
      state.numAt.push(new Array(p.cols).fill(0));
      state.startColorAt.push(new Array(p.cols).fill(COLOR_EMPTY));
      state.cellEls.push(new Array(p.cols).fill(null));
    }
    p.words.forEach(function (w, i) {
      if (state.numAt[w.row][w.col] === 0) {
        state.numAt[w.row][w.col] = w.number;
        state.startColorAt[w.row][w.col] = colorFor(i);
      }
    });

    for (var rr = 0; rr < p.rows; rr++) {
      for (var cc = 0; cc < p.cols; cc++) {
        var el = document.createElement('div');
        el.className = 'cell';
        el.dataset.r = rr;
        el.dataset.c = cc;
        if (!E.isPlayable(p, rr, cc)) {
          el.classList.add('blank');
        } else {
          if (state.numAt[rr][cc] > 0) {
            var num = document.createElement('span');
            num.className = 'num';
            num.textContent = String(state.numAt[rr][cc]);
            el.appendChild(num);
          }
          var ltr = document.createElement('span');
          ltr.className = 'ltr';
          el.appendChild(ltr);
          el.addEventListener('click', onCellTap.bind(null, rr, cc));
        }
        els.board.appendChild(el);
        state.cellEls[rr][cc] = el;
      }
    }
    sizeBoard();
    paintBoard();
  }

  function renderClues() {
    els.across.innerHTML = '';
    els.down.innerHTML = '';
    state.clueEls = [];
    state.puzzle.words.forEach(function (w, i) {
      var box = w.dir === E.ACROSS ? els.across : els.down;
      var div = document.createElement('div');
      div.className = 'clue';
      div.textContent = w.number + '. ' + w.clue;
      div.style.background = colorFor(i);
      div.addEventListener('click', function () { selectWord(w); });
      box.appendChild(div);
      state.clueEls[i] = div;
    });
  }

  function currentWord() {
    if (!state.puzzle || state.selR < 0) return null;
    return E.wordAt(state.puzzle, state.selR, state.selC, state.selDir);
  }

  function paintBoard() {
    var p = state.puzzle;
    var active = currentWord();
    var activeColor = active ? colorOfWord(active) : COLOR_EMPTY;
    for (var r = 0; r < p.rows; r++) {
      for (var c = 0; c < p.cols; c++) {
        var el = state.cellEls[r][c];
        if (!el || !E.isPlayable(p, r, c)) continue;
        var isStart = state.numAt[r][c] > 0;
        var inActive = active && E.wordCovers(active, r, c);
        var bg = isStart ? state.startColorAt[r][c] : (inActive ? activeColor : COLOR_EMPTY);
        el.style.background = bg;
        el.classList.toggle('selected', r === state.selR && c === state.selC);
        el.querySelector('.ltr').textContent = state.user[r][c] || '';
      }
    }
    if (state.clueEls) {
      p.words.forEach(function (w, i) {
        if (state.clueEls[i]) {
          state.clueEls[i].style.outline = (active === w) ? '3px solid #000' : 'none';
        }
      });
    }
  }

  function afterSelection() {
    paintBoard();
    var w = currentWord();
    if (w) {
      setStatus(w.number + (w.dir === E.ACROSS ? ' Yatay' : ' Dikey') + ': ' + w.clue);
    }
    els.kb.focus();
  }

  function onCellTap(r, c) {
    var p = state.puzzle;
    if (!E.isPlayable(p, r, c)) return;
    var other = state.selDir === E.ACROSS ? E.DOWN : E.ACROSS;
    if (r === state.selR && c === state.selC) {
      if (E.wordAt(p, r, c, other)) state.selDir = other;
    } else {
      if (!E.wordAt(p, r, c, state.selDir)) state.selDir = other;
      state.selR = r;
      state.selC = c;
    }
    afterSelection();
  }

  function selectWord(w) {
    state.selR = w.row;
    state.selC = w.col;
    state.selDir = w.dir;
    afterSelection();
  }

  function indexIn(w, r, c) {
    return w.dir === E.ACROSS ? c - w.col : r - w.row;
  }

  function inputChars(text) {
    if (!state.puzzle || state.selR < 0) return;
    for (var ch of text) {
      var norm = E.normalize(ch);
      if (!norm) continue;
      state.user[state.selR][state.selC] = norm.charAt(0);
      var w = currentWord();
      if (w) {
        var idx = indexIn(w, state.selR, state.selC);
        if (idx + 1 < w.answer.length) {
          state.selR = w.dir === E.DOWN ? w.row + idx + 1 : w.row;
          state.selC = w.dir === E.ACROSS ? w.col + idx + 1 : w.col;
        }
      }
    }
    paintBoard();
    checkSolved();
  }

  function deleteBack() {
    if (!state.puzzle || state.selR < 0) return;
    if (state.user[state.selR][state.selC]) {
      state.user[state.selR][state.selC] = '';
    } else {
      var w = currentWord();
      if (!w) return;
      var idx = indexIn(w, state.selR, state.selC);
      if (idx > 0) {
        state.selR = w.dir === E.DOWN ? w.row + idx - 1 : w.row;
        state.selC = w.dir === E.ACROSS ? w.col + idx - 1 : w.col;
        state.user[state.selR][state.selC] = '';
      }
    }
    paintBoard();
  }

  function checkSolved() {
    if (!state.solvedNotified && E.isSolved(state.puzzle, state.user)) {
      state.solvedNotified = true;
      setStatus('Tebrikler, bulmacayı çözdün!');
    }
  }

  function revealSolution() {
    var p = state.puzzle;
    if (!p) return;
    for (var r = 0; r < p.rows; r++) {
      state.user[r] = p.solution[r].slice();
    }
    paintBoard();
    setStatus('Çözüm gösterildi.');
  }

  function wireKeyboard() {
    els.kb.addEventListener('input', function (e) {
      if (e.isComposing) return;
      var v = els.kb.value;
      els.kb.value = '';
      if (v) inputChars(v);
    });
    els.kb.addEventListener('compositionend', function () {
      var v = els.kb.value;
      els.kb.value = '';
      if (v) inputChars(v);
    });
    els.kb.addEventListener('keydown', function (e) {
      if (e.key === 'Backspace') {
        e.preventDefault();
        deleteBack();
      }
    });
  }

  async function init() {
    ['topic', 'remaining', 'newBtn', 'revealBtn', 'status', 'board', 'across', 'down',
      'kb', 'appVersion'].forEach(function (id) { els[id] = $(id); });

    els.appVersion.textContent = 'Sürüm ' + APP_VERSION;
    els.newBtn.addEventListener('click', newGame);
    els.revealBtn.addEventListener('click', revealSolution);
    window.addEventListener('resize', function () { if (state.puzzle) sizeBoard(); });
    wireKeyboard();

    try {
      var bank = await loadBank();
      state.items = bank.items;
      els.appVersion.textContent = 'Sürüm ' + APP_VERSION + ' · Bulmaca ' + bank.version;
      els.newBtn.disabled = false;
      newGame();
      checkRemote(bank.version);
    } catch (e) {
      setStatus('Bulmaca veritabanı okunamadı: ' + e.message);
    }

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(function () { /* çevrimdışı desteği olmadan devam */ });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
