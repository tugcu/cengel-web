/*
 * Çengel bulmaca yerleştirme motoru (Android CrosswordEngine.java ile birebir aynı mantık).
 * Copyright (c) 2026 Tuna Tuğcu. Tüm hakları saklıdır.
 */
(function (root) {
  'use strict';

  var ACROSS = 0;
  var DOWN = 1;
  var GRID = 40;
  var ORIGIN = 20;
  var MAX_LEN = 15;
  var MIN_LEN = 3;

  function normalize(s) {
    if (!s) return '';
    var up = String(s).toLocaleUpperCase('tr-TR');
    var out = '';
    for (var i = 0; i < up.length; i++) {
      var ch = up.charAt(i);
      if (/\p{L}/u.test(ch)) out += ch;
    }
    return out;
  }

  function inb(r, c) {
    return r >= 0 && c >= 0 && r < GRID && c < GRID;
  }

  function countCrossings(g, mask, w, sr, sc, d) {
    var len = w.length;
    var er = sr + (d === DOWN ? len - 1 : 0);
    var ec = sc + (d === ACROSS ? len - 1 : 0);
    if (sr < 0 || sc < 0 || er >= GRID || ec >= GRID) return -1;
    var br = sr - (d === DOWN ? 1 : 0);
    var bc = sc - (d === ACROSS ? 1 : 0);
    if (inb(br, bc) && g[br][bc]) return -1;
    var ar = er + (d === DOWN ? 1 : 0);
    var ac = ec + (d === ACROSS ? 1 : 0);
    if (inb(ar, ac) && g[ar][ac]) return -1;
    var bit = d === ACROSS ? 1 : 2;
    var cross = 0;
    for (var i = 0; i < len; i++) {
      var r = sr + (d === DOWN ? i : 0);
      var c = sc + (d === ACROSS ? i : 0);
      var ex = g[r][c];
      if (ex) {
        if (ex !== w.charAt(i)) return -1;
        if (mask[r][c] & bit) return -1;
        cross++;
      } else {
        var r1 = d === ACROSS ? r - 1 : r;
        var c1 = d === ACROSS ? c : c - 1;
        var r2 = d === ACROSS ? r + 1 : r;
        var c2 = d === ACROSS ? c : c + 1;
        if (inb(r1, c1) && g[r1][c1]) return -1;
        if (inb(r2, c2) && g[r2][c2]) return -1;
      }
    }
    return cross;
  }

  function place(g, mask, placed, e, r, c, d) {
    placed.push({ answer: e.answer, clue: e.clue, row: r, col: c, dir: d, number: 0 });
    var bit = d === ACROSS ? 1 : 2;
    for (var i = 0; i < e.answer.length; i++) {
      var rr = d === DOWN ? r + i : r;
      var cc = d === ACROSS ? c + i : c;
      g[rr][cc] = e.answer.charAt(i);
      mask[rr][cc] |= bit;
    }
  }

  function toPuzzle(placed) {
    var minR = Infinity, minC = Infinity, maxR = -Infinity, maxC = -Infinity;
    placed.forEach(function (w) {
      minR = Math.min(minR, w.row);
      minC = Math.min(minC, w.col);
      maxR = Math.max(maxR, w.row + (w.dir === DOWN ? w.answer.length - 1 : 0));
      maxC = Math.max(maxC, w.col + (w.dir === ACROSS ? w.answer.length - 1 : 0));
    });
    var rows = maxR - minR + 1;
    var cols = maxC - minC + 1;
    var solution = [];
    for (var r = 0; r < rows; r++) solution.push(new Array(cols).fill(''));

    var shifted = placed.map(function (w) {
      return { answer: w.answer, clue: w.clue, row: w.row - minR, col: w.col - minC, dir: w.dir, number: 0 };
    });
    shifted.forEach(function (s) {
      for (var i = 0; i < s.answer.length; i++) {
        var rr = s.row + (s.dir === DOWN ? i : 0);
        var cc = s.col + (s.dir === ACROSS ? i : 0);
        solution[rr][cc] = s.answer.charAt(i);
      }
    });

    var numAt = [];
    for (var r2 = 0; r2 < rows; r2++) numAt.push(new Array(cols).fill(0));
    shifted.forEach(function (s) { numAt[s.row][s.col] = -1; });
    var n = 0;
    for (var r3 = 0; r3 < rows; r3++) {
      for (var c3 = 0; c3 < cols; c3++) {
        if (numAt[r3][c3] === -1) numAt[r3][c3] = ++n;
      }
    }
    shifted.forEach(function (s) { s.number = numAt[s.row][s.col]; });
    shifted.sort(function (a, b) { return (a.number - b.number) || (a.dir - b.dir); });

    return { rows: rows, cols: cols, solution: solution, words: shifted };
  }

  function build(entries) {
    var remaining = [];
    var seen = {};
    (entries || []).forEach(function (e) {
      var a = normalize(e.answer);
      if (a.length < MIN_LEN || a.length > MAX_LEN || seen[a]) return;
      seen[a] = true;
      remaining.push({ answer: a, clue: String(e.clue || '').trim() });
    });
    if (remaining.length < 2) return null;
    remaining.sort(function (x, y) { return y.answer.length - x.answer.length; });

    var g = [];
    var mask = [];
    for (var r = 0; r < GRID; r++) {
      g.push(new Array(GRID).fill(''));
      mask.push(new Array(GRID).fill(0));
    }
    var placed = [];
    var first = remaining.shift();
    place(g, mask, placed, first, ORIGIN, ORIGIN - Math.floor(first.answer.length / 2), ACROSS);

    while (remaining.length > 0) {
      var best = null;
      for (var idx = 0; idx < remaining.length; idx++) {
        var w = remaining[idx].answer;
        for (var gr = 0; gr < GRID; gr++) {
          for (var gc = 0; gc < GRID; gc++) {
            var ch = g[gr][gc];
            if (!ch) continue;
            for (var i = 0; i < w.length; i++) {
              if (w.charAt(i) !== ch) continue;
              for (var d = ACROSS; d <= DOWN; d++) {
                var sr = d === DOWN ? gr - i : gr;
                var sc = d === ACROSS ? gc - i : gc;
                var cr = countCrossings(g, mask, w, sr, sc, d);
                if (cr <= 0) continue;
                var score = cr * 100 - (Math.abs(sr - ORIGIN) + Math.abs(sc - ORIGIN));
                if (best === null || score > best.score) {
                  best = { idx: idx, row: sr, col: sc, dir: d, score: score };
                }
              }
            }
          }
        }
      }
      if (best === null) break;
      var chosen = remaining.splice(best.idx, 1)[0];
      place(g, mask, placed, chosen, best.row, best.col, best.dir);
    }

    if (placed.length < 2) return null;
    return toPuzzle(placed);
  }

  function wordCovers(w, r, c) {
    if (w.dir === ACROSS) return r === w.row && c >= w.col && c < w.col + w.answer.length;
    return c === w.col && r >= w.row && r < w.row + w.answer.length;
  }

  function wordAt(p, r, c, dir) {
    if (r < 0 || c < 0 || r >= p.rows || c >= p.cols) return null;
    for (var i = 0; i < p.words.length; i++) {
      var w = p.words[i];
      if (w.dir === dir && wordCovers(w, r, c)) return w;
    }
    return null;
  }

  function isPlayable(p, r, c) {
    return p.solution[r][c] !== '';
  }

  function isSolved(p, user) {
    for (var r = 0; r < p.rows; r++) {
      for (var c = 0; c < p.cols; c++) {
        if (p.solution[r][c] !== '' && user[r][c] !== p.solution[r][c]) return false;
      }
    }
    return true;
  }

  var api = {
    ACROSS: ACROSS,
    DOWN: DOWN,
    normalize: normalize,
    build: build,
    wordAt: wordAt,
    wordCovers: wordCovers,
    isPlayable: isPlayable,
    isSolved: isSolved
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  } else {
    root.CrosswordEngine = api;
  }
})(typeof self !== 'undefined' ? self : this);
