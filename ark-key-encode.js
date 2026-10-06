#!/usr/bin/env node
/**
 * ark-key-encode.js — 生成/验证方舟 API Key 的混淆编码
 *
 * 用法:
 *   node ark-key-encode.js <你的APIKey>
 *   node ark-key-encode.js --check   # 验证 index.html 内嵌 key 与当前 key 是否一致
 *
 * 说明: 前端混淆仅防明文扫描, 不构成真正安全。提交至公域 git 前请务必:
 *   1) 使用本脚本生成新 key 的 ARK_KEY_ENCODED;
 *   2) 或在 index.html 中配置 ARK_PROXY_URL 走后端代理, 前端不持有 key。
 */
const SALT = 'AI_FUND_SELECT_2026';

function encode(key) {
  let out = '';
  for (let i = 0; i < key.length; i++) {
    out += String.fromCharCode(key.charCodeAt(i) ^ SALT.charCodeAt(i % SALT.length));
  }
  return Buffer.from(out, 'binary').toString('base64');
}

function decode(encoded) {
  const raw = Buffer.from(encoded, 'base64').toString('binary');
  let out = '';
  for (let i = 0; i < raw.length; i++) {
    out += String.fromCharCode(raw.charCodeAt(i) ^ SALT.charCodeAt(i % SALT.length));
  }
  return out;
}

const arg = process.argv[2];
if (!arg) {
  console.log('用法: node ark-key-encode.js <APIKey>  |  node ark-key-encode.js --check');
  process.exit(1);
}

if (arg === '--check') {
  const fs = require('fs');
  const html = fs.readFileSync('index.html', 'utf-8');
  const m = html.match(/const ARK_KEY_ENCODED = '([^']+)'/);
  if (!m) { console.log('未在 index.html 中找到 ARK_KEY_ENCODED'); process.exit(1); }
  console.log('index.html 内嵌 key =', decode(m[1]));
} else {
  const encoded = encode(arg);
  console.log('ARK_KEY_ENCODED = ' + encoded);
  console.log('校验还原 =', decode(encoded));
  console.log('\n替换 index.html 中 const ARK_KEY_ENCODED 的值即可。');
}
