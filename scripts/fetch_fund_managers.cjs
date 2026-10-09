#!/usr/bin/env node
/**
 * 为基金池批量抓取基金经理（数据源：东方财富 pingzhongdata）
 * 输出：fund-managers.js  →  window.FUND_MANAGERS = { "005827.OF": "张坤、杨思亮", ... }
 *
 * 说明：
 *  - 纯离线化的最终产物是 fund-managers.js（静态 JS），前端只读该文件，运行时零请求；
 *  - 本脚本仅在"数据更新"时手动运行一次；
 *  - 接口并发受限流约束，串行 + 间隔，失败自动重试 3 次。
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const DIR = '/Users/yzreal/WorkBuddy/2026-09-22-09-21-20/交付物/ai-fund-selection-h5-fixed';
const OUT = path.join(DIR, 'fund-managers.js');

// 读取基金池
global.window = global;
require(path.join(DIR, 'fund-pool-base.js'));
const FUNDS = global.FUND_POOL_BASE || [];

/**
 * 从 pingzhongdata 脚本文本中提取基金经理姓名。
 * 注意：不能用 /\[[\s\S]*?\]/ 非贪婪匹配——数组元素是对象，对象内的第一个 "]" 会提前截断
 * （实测 005827 在 position 1914 触发 "Unexpected non-whitespace character after JSON"）。
 * 改为：定位起点的 "["，再做括号配对扫描，取到匹配的 "]"，保证完整。
 */
function extractManagers(buf) {
  const key = 'Data_currentFundManager';
  const ki = buf.indexOf(key);
  if (ki < 0) return null;
  const start = buf.indexOf('[', ki);
  if (start < 0) return null;
  let depth = 0, end = -1, inStr = false, esc = false;
  for (let i = start; i < buf.length; i++) {
    const ch = buf[i];
    if (inStr) {
      if (esc) { esc = false; }
      else if (ch === '\\') { esc = true; }
      else if (ch === '"') { inStr = false; }
      continue;
    }
    if (ch === '"') { inStr = true; continue; }
    if (ch === '[') depth++;
    else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  if (end < 0) return null;
  const json = buf.slice(start, end + 1);
  try {
    const arr = JSON.parse(json);
    const names = arr.map(x => x && x.name).filter(Boolean);
    return names.length ? Array.from(new Set(names)).join('、') : null;
  } catch (e) { return null; }
}

function fetchFund(code6, retries = 3) {
  const url = `https://fund.eastmoney.com/pingzhongdata/${code6}.js`;
  return new Promise((resolve) => {
    const attempt = (n) => {
      https.get(url, {
        headers: {
          'Referer': 'https://fund.eastmoney.com/',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }, timeout: 15000
      }, res => {
        if (res.statusCode !== 200) { res.resume(); return n > 0 ? setTimeout(() => attempt(n - 1), 800) : resolve(null); }
        let buf = '';
        res.setEncoding('utf8');
        res.on('data', d => buf += d);
        res.on('end', () => {
          const names = extractManagers(buf);
          return resolve(names);
        });
      }).on('error', () => n > 0 ? setTimeout(() => attempt(n - 1), 800) : resolve(null))
        .on('timeout', function () { this.destroy(); n > 0 ? setTimeout(() => attempt(n - 1), 800) : resolve(null); });
    };
    attempt(retries);
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const map = {};
  let ok = 0, miss = 0;
  const total = FUNDS.length;
  for (let i = 0; i < total; i++) {
    const f = FUNDS[i];
    const code6 = String(f.fundCode || '').replace(/\.(OF|SH|SZ)$/i, '');
    if (!/^\d{6}$/.test(code6)) { miss++; continue; }
    const mgr = await fetchFund(code6);
    if (mgr) { map[f.fundCode] = mgr; ok++; }
    else miss++;
    if ((i + 1) % 25 === 0 || i === total - 1) {
      console.log(`[${i + 1}/${total}] 成功 ${ok} 缺失 ${miss}  (最近: ${f.fundName} → ${mgr || '—'})`);
    }
    await sleep(120);   // 限流：约 8 只/秒
  }
  const js = '// 自动生成 — 基金经理映射（数据源：东方财富 pingzhongdata，离线快照）\n' +
    '// 仅供 ai-fund-selection-h5 前端离线读取；更新时重跑 scripts/fetch_fund_managers.cjs\n' +
    'window.FUND_MANAGERS = ' + JSON.stringify(map) + ';\n';
  fs.writeFileSync(OUT, js, 'utf8');
  console.log(`\n完成：成功 ${ok} / 缺失 ${miss} / 总计 ${total}`);
  console.log('写出：', OUT, `(${(js.length / 1024).toFixed(1)} KB)`);
})();
