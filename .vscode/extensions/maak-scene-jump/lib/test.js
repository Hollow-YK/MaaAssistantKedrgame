'use strict';
/**
 * 纯逻辑自测（node 直接运行，无需 vscode）。
 *   用法: node .vscode/extensions/maak-scene-jump/lib/test.js
 *   校验: 所有节点引用（scenes key/detect/parent、edges from/to/jump/via）
 *          都能在 pipeline 资源中解析到定义，且内部一致性（from/to/parent ∈ scenes）。
 */
const fs = require('fs');
const path = require('path');
const { scanJsoncStrings, refKind, isSceneRef, buildNodeIndex, fieldAt, parseJsonc } = require('./sceneMap');
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const MAP_FILE = path.join(REPO_ROOT, 'agent', 'custom', 'action', 'scene_jump_map.json');
const mapText = fs.readFileSync(MAP_FILE, 'utf-8');

function rglob(dir, exts, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) rglob(p, exts, out);
    else if (exts.includes(path.extname(p))) out.push(p);
  }
  return out;
}

function resolveResourceDirs() {
  // 与扩展的 resolveResourcePaths 一致：从 assets/interface.json 的 resource[].path 推导
  const dirs = new Set();
  const ifacePath = path.join(REPO_ROOT, 'assets', 'interface.json');
  if (fs.existsSync(ifacePath)) {
    try {
      const iface = parseJsonc(fs.readFileSync(ifacePath, 'utf-8'));
      for (const res of iface.resource || []) {
        for (const p of res.path || []) {
          dirs.add(path.resolve(path.dirname(ifacePath), p));
        }
      }
    } catch (e) {
      console.warn(`解析 interface.json 失败: ${e}`);
    }
  }
  if (!dirs.size) {
    for (const d of ['assets/resource', 'assets/resource_bilibili', 'assets/resource_taptap']) {
      dirs.add(path.join(REPO_ROOT, d));
    }
  }
  return [...dirs];
}

function main() {
  // 1) 建立节点索引
  const files = [];
  for (const res of resolveResourceDirs()) {
    for (const sub of ['pipeline', 'tasks']) {
      for (const fp of rglob(path.join(res, sub), ['.json', '.jsonc'])) {
        files.push({ path: fp, text: fs.readFileSync(fp, 'utf-8') });
      }
    }
  }
  const index = buildNodeIndex(files);
  console.log(`索引节点数: ${index.size}，扫描文件数: ${files.length}`);

  // 2) 扫描 map
  const toks = scanJsoncStrings(mapText);

  // 内部一致性：scenes 场景名集合
  const sceneNames = new Set();
  for (const t of toks) {
    if (t.isKey && t.segments.length === 1 && t.segments[0] === 'scenes') sceneNames.add(t.value);
  }

  const missing = []; // { ref, node, why }
  let refCount = 0;

  for (const t of toks) {
    const kind = refKind(t);
    if (!kind) continue;
    refCount++;
    if (isSceneRef(kind)) {
      // 场景引用（parent/from/to/via）：必须存在于 scenes；scene key 本身即定义
      if (kind !== 'scene' && !sceneNames.has(t.value)) {
        missing.push({ ref: segPath(t.segments), node: t.value, why: '场景引用未在 scenes 中定义' });
      }
      continue;
    }
    // 节点引用（detect / jump）：必须能在 pipeline 中解析到定义
    if (!index.has(t.value)) {
      missing.push({ ref: segPath(t.segments), node: t.value, why: '节点引用未在 pipeline 中找到定义' });
    }
  }

  // 缺省 detect 的场景：视为仅作 parent 的抽象场景，不要求 pipeline 节点


  console.log(`引用总数: ${refCount}`);
  if (missing.length) {
    for (const m of missing) console.log(`  ❌ ${m.ref} = ${JSON.stringify(m.node)}: ${m.why}`);
    console.log(`❌ ${missing.length} 处引用错误`);
    process.exit(1);
  }
    console.log(`✓ 全部 ${refCount} 处引用均能解析（场景引用→scenes，节点引用→pipeline）`);
}

function segPath(segs) {
  return segs.map((s, i) => (typeof s === 'number' ? `[${s}]` : i === 0 ? s : `.${s}`)).join('');
}

// ── fieldAt（补全定位）自测 ───────────────────────────────────────────
function testFieldAt() {
  const toks = scanJsoncStrings(mapText);

  // 1) 光标落在已完成引用值内 → 返回对应类型
  const fromTok = toks.find((t) => t.segments[0] === 'edges' && t.segments[2] === 'from' && !t.isKey);
  const f1 = fieldAt(mapText, fromTok.start + 1, toks);
  if (!f1 || f1.kind !== 'from') throw new Error(`fieldAt 完成值错误: ${JSON.stringify(f1)}`);

  // 2) 光标在未完成值内（截断文本模拟输入中）→ 返回该字段
  const snip = '{"scenes": {"A": {"detect": "Status_X';
  const stoks = scanJsoncStrings(snip);
  const f2 = fieldAt(snip, snip.length, stoks);
  if (!f2 || f2.kind !== 'detect') throw new Error(`fieldAt 输入中错误: ${JSON.stringify(f2)}`);

  // 3) 光标在非引用位置（desc 值）→ null
  const descTok = toks.find((t) => t.segments[0] === 'scenes' && t.segments[2] === 'desc' && !t.isKey);
  const f3 = fieldAt(mapText, descTok.start + 1, toks);
  if (f3 !== null) throw new Error(`fieldAt 非引用位置错误: ${JSON.stringify(f3)}`);

  console.log('✓ fieldAt 补全定位测试通过');
}
testFieldAt();

// ── to 数组（多目标候选）场景引用分类自测 ─────────────────────────────
function testToArray() {
  const snip =
    '{"scenes":{"A":{},"B":{},"C":{}},"edges":[{"from":"A","to":["B","C"],"jump":["X"]}]}';
  const toks = scanJsoncStrings(snip);
  const kinds = toks.filter((t) => refKind(t)).map((t) => `${t.value}:${refKind(t)}`);
  if (kinds.indexOf('B:to') < 0 || kinds.indexOf('C:to') < 0) {
    throw new Error(`to 数组分类错误: ${kinds.join(',')}`);
  }
  console.log('✓ to 数组场景引用分类测试通过');
}
testToArray();

// ── detect 组合写法（And/Or）引用分类与补全自测 ───────────────────────
function testDetectComposite() {
  const snip = JSON.stringify({
    scenes: {
      Shop: { desc: '商店', detect: 'UI_Shop_VipShop' },
      Shop_1: {
        desc: '推荐',
        detect: { type: 'And', all_of: ['UI_Shop_VipShop', 'UI_Shop_OCRSelected_1'] },
      },
      Shop_2: {
        desc: '兑换',
        detect: { type: 'Or', any_of: ['UI_Shop_Shop', 'UI_Shop_OCRSelected_2'] },
      },
      Alert: { desc: '对话框' },
    },
    edges: [],
  });

  const toks = scanJsoncStrings(snip);

  // 1) 组合 detect 内的节点名应识别为节点引用 'detect'
  const kinds = toks
    .filter((t) => refKind(t))
    .map((t) => `${t.value}:${refKind(t)}`);

  for (const want of [
    'UI_Shop_VipShop:detect',
    'UI_Shop_OCRSelected_1:detect',
    'UI_Shop_Shop:detect',
    'UI_Shop_OCRSelected_2:detect',
  ]) {
    if (kinds.indexOf(want) < 0) {
      throw new Error(`组合 detect 引用分类错误，缺少 ${want}：${kinds.join(',')}`);
    }
  }

  // 2) 组合 detect 内的 token 应能定位到（供跳转/悬停用）
  const comboVal = toks.find(
    (t) => t.value === 'UI_Shop_OCRSelected_1' && t.segments[0] === 'scenes'
  );
  if (!comboVal) throw new Error('组合 detect 子节点 token 未找到');
  if (comboVal.segments[comboVal.segments.length - 1] !== 1) {
    throw new Error(`组合 detect 子节点路径错误: ${JSON.stringify(comboVal.segments)}`);
  }

  // 3) 光标在 all_of 数组内（输入中）→ fieldAt 返回 detect，供补全节点名
  const cut = snip.slice(0, snip.indexOf('UI_Shop_OCRSelected_1'));
  const cutToks = scanJsoncStrings(cut);
  const f = fieldAt(cut, cut.length, cutToks);
  if (!f || f.kind !== 'detect') {
    throw new Error(`all_of 内补全定位错误: ${JSON.stringify(f)}`);
  }

  // 4) any_of 同理
  const cut2 = snip.slice(0, snip.indexOf('UI_Shop_OCRSelected_2'));
  const f2 = fieldAt(cut2, cut2.length, scanJsoncStrings(cut2));
  if (!f2 || f2.kind !== 'detect') {
    throw new Error(`any_of 内补全定位错误: ${JSON.stringify(f2)}`);
  }

  // 5) 数组闭合之后不应再被判定为该字段（避免后续无关位置误补全）
  const after = snip.slice(0, snip.indexOf('"Alert"'));
  const f3 = fieldAt(after, after.length, scanJsoncStrings(after));
  if (f3 !== null) {
    throw new Error(`数组闭合后仍误判: ${JSON.stringify(f3)}`);
  }

  console.log('✓ detect 组合写法（And/Or）引用分类与补全测试通过');
}
testDetectComposite();

// ── 残缺 JSON 不死循环自测 ────────────────────────────────────────────
function testMalformed() {
  const cases = [
    '{,"a":1}',
    '{"a":1,,}',
    '{"a":]',
    '[,]',
    '}]},,,',
    '"unterminated',
    '{"a": 1} extra } ,',
    '[[[[[,',
    '{"a": [1,2,,3]}',
    '{"a": "x\\", }',
    '{"scenes": {"MainMenu": {"desc": "主',
    '{"edges": [{"from": "A", "to":',
  ];
  for (const s of cases) {
    const toks = scanJsoncStrings(s); // 若修复前会死循环
    if (!Array.isArray(toks)) throw new Error(`scanJsoncStrings 非数组: ${JSON.stringify(s)}`);
  }
  console.log(`✓ 残缺 JSON 不死循环测试通过（${cases.length} 例）`);
}
testMalformed();

main();
