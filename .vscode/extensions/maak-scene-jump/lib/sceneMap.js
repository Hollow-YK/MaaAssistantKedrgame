'use strict';
/**
 * sceneMap.js —— SceneJump 节点引用的纯逻辑模块（不依赖 vscode API，可独立测试）。
 *
 * 能力（与 nekosu.maa-support 的 Pipeline 语义分析同一思路，但独立实现）：
 *   - 扫描 JSON/JSONC 文件，为每个字符串字面量记录其在 JSON 中的路径与偏移；
 *   - 从 pipeline 资源中建立“节点名 -> 定义位置”索引；
 *   - 判断 scene_jump_map.json 中某一处字符串是否为“节点引用”及引用类型。
 */

// ── JSONC 处理 ─────────────────────────────────────────────────────────

/** 去掉 JSONC 注释（保留换行，维持行号）。 */
function stripJsonc(text) {
  const out = [];
  let state = 0; // 0=正常 1=字符串 2=转义
  let i = 0;
  while (i < text.length) {
    const c = text[i];
    if (state === 0) {
      if (c === '"') { out.push(c); state = 1; i++; }
      else if (c === '/' && text[i + 1] === '/') {
        while (i < text.length && text[i] !== '\n') i++;
        if (i < text.length) { out.push('\n'); i++; }
      } else if (c === '/' && text[i + 1] === '*') {
        i += 2;
        while (i + 1 < text.length && !(text[i] === '*' && text[i + 1] === '/')) {
          if (text[i] === '\n') out.push('\n');
          i++;
        }
        i += 2;
      } else { out.push(c); i++; }
    } else if (state === 1) {
      out.push(c);
      if (c === '\\') state = 2;
      else if (c === '"') state = 0;
      i++;
    } else { // 转义
      out.push(c); state = 1; i++;
    }
  }
  return out.join('');
}

/** 解析 JSONC 为对象。 */
function parseJsonc(text) {
  return JSON.parse(stripJsonc(text));
}

// ── 字符串扫描（带 JSON 路径与偏移）──────────────────────────────────

/**
 * 扫描文本中所有字符串字面量，返回 token 数组：
 *   { segments: Array<string|number>, isKey?: boolean, value: string, start: number, end: number }
 * segments 为从根到该字符串的 JSON 路径段（对象键为字符串，数组下标为数字）。
 * 对于对象键 token：segments 为该键所属对象的路径（不含键本身），isKey=true。
 * start/end 为字节偏移（不含注释，偏移与原文一致）。
 */
function scanJsoncStrings(text) {
  const tokens = [];
  const path = [];
  let i = 0;
  const n = text.length;

  function skipWs() {
    for (;;) {
      while (i < n && /\s/.test(text[i])) i++;
      if (text[i] === '/' && text[i + 1] === '/') {
        while (i < n && text[i] !== '\n') i++;
        continue;
      }
      if (text[i] === '/' && text[i + 1] === '*') {
        i += 2;
        while (i + 1 < n && !(text[i] === '*' && text[i + 1] === '/')) i++;
        i += 2;
        continue;
      }
      break;
    }
  }

  function parseStringToken() {
    const start = i;
    i++; // 跳过起始引号
    while (i < n) {
      const c = text[i];
      if (c === '\\') i += 2;
      else if (c === '"') { i++; break; }
      else i++;
    }
    const raw = text.slice(start, i);
    let value;
    try { value = JSON.parse(raw); } catch { value = raw.slice(1, -1); }
    return { start, end: i, value };
  }

  function skipPrimitive() {
    while (i < n) {
      const c = text[i];
      if (c === ',' || c === ']' || c === '}' || /\s/.test(c)) break;
      i++;
    }
  }

  function parseValue() {
    skipWs();
    if (i >= n) return;
    const c = text[i];
    if (c === '"') {
      const tok = parseStringToken();
      tokens.push({ segments: path.slice(), value: tok.value, start: tok.start, end: tok.end });
      return;
    }
    if (c === '{') {
      i++;
      skipWs();
      if (text[i] === '}') { i++; return; }
      for (;;) {
        skipWs();
        if (i >= n || text[i] !== '"') { skipPrimitive(); break; }
        const keyTok = parseStringToken();
        tokens.push({ segments: path.slice(), isKey: true, value: keyTok.value, start: keyTok.start, end: keyTok.end });
        skipWs();
        if (text[i] === ':') i++;
        path.push(keyTok.value);
        parseValue();
        path.pop();
        skipWs();
        if (text[i] === ',') { i++; continue; }
        if (text[i] === '}') { i++; break; }
        break;
      }
      return;
    }
    if (c === '[') {
      i++;
      skipWs();
      if (text[i] === ']') { i++; return; }
      let idx = 0;
      for (;;) {
        path.push(idx);
        parseValue();
        path.pop();
        skipWs();
        if (text[i] === ',') { i++; idx++; continue; }
        if (text[i] === ']') { i++; break; }
        break;
      }
      return;
    }
    skipPrimitive();
  }

  while (i < n) {
    skipWs();
    if (i >= n) break;
    const pos = i;
    const c = text[i];
    if (c === '{' || c === '[' || c === '"') parseValue();
    else skipPrimitive();
    // 防御：残缺 JSON（如多余的 , ] }）可能导致本轮未前进，强制跳过以避免死循环
    if (i <= pos) i++;
  }
  return tokens;
}

// ── 引用类型判断 ──────────────────────────────────────────────────────

/**
 * 判断 token 是否为 scene_jump_map.json 中的“引用”。
 * 返回引用类型字符串，非引用返回 null：
 *   场景引用（指向 scenes 中同名场景定义）:
 *     'scene'   —— scenes 下的场景名（key）
 *     'parent'  —— 场景的父场景
 *     'from' / 'to' —— 边的当前/目标场景
 *     'via'     —— 边的中间场景
 *   节点引用（指向 pipeline 中的节点定义）:
 *     'detect'  —— 场景的识别节点（含组合写法 scenes.<场景>.detect.all_of[i] / .any_of[i]）
 *     'jump'    —— 边的跳转节点
 */
function refKind(tok) {
  if (tok.isKey) {
    // scenes 下每个场景名（key）→ 场景引用
    return tok.segments.length === 1 && tok.segments[0] === 'scenes' ? 'scene' : null;
  }
  const s = tok.segments;
  if (s.length >= 3 && s[0] === 'scenes') {
    const last = s[s.length - 1];
    if (last === 'detect' || last === 'parent') return last;
    if (typeof last === 'number') {
      // detect 组合写法中的子识别节点：scenes.<场景>.detect.all_of[i] / .any_of[i]
      const field = s[s.length - 2];
      if ((field === 'all_of' || field === 'any_of') && s[s.length - 3] === 'detect') {
        return 'detect';
      }
    }
  }
  if (s[0] === 'edges') {
    const last = s[s.length - 1];
    if (last === 'from' || last === 'to' || last === 'jump' || last === 'via') return last;
    if (typeof last === 'number') {
      // to / jump / via 数组中的元素
      const parent = s[s.length - 2];
      if (parent === 'to' || parent === 'jump' || parent === 'via') return parent;
    }
  }
  return null;
}

/** 是否为“detect 组合写法中的子识别列表字段”（all_of / any_of）。 */
function isDetectLogicField(keyTok) {
  return (
    keyTok.isKey &&
    (keyTok.value === 'all_of' || keyTok.value === 'any_of') &&
    keyTok.segments.length >= 3 &&
    keyTok.segments[keyTok.segments.length - 1] === 'detect'
  );
}

/** 是否为“场景引用”（应跳转到 scene_jump_map.json 的 scenes.<name>）。 */
function isSceneRef(kind) {
  return kind === 'scene' || kind === 'parent' || kind === 'from' || kind === 'to' || kind === 'via';
}

/** 是否为“节点引用”（应跳转到 pipeline 资源中的节点定义）。 */
function isNodeRef(kind) {
  return kind === 'detect' || kind === 'jump';
}

// ── 节点索引 ──────────────────────────────────────────────────────────

/**
 * 从一组文件文本建立“节点名 -> 定义位置”索引。
 * files: [{ path: string, text: string }]
 * 返回 Map<nodeName, Array<{ path, offset, text }>>
 * （只取每份文件最顶层的键，即 pipeline 节点名。）
 */
function buildNodeIndex(files) {
  const index = new Map();
  for (const f of files) {
    let tokens;
    try { tokens = scanJsoncStrings(f.text); } catch { continue; }
    for (const t of tokens) {
      if (t.isKey && t.segments.length === 0) {
        if (!index.has(t.value)) index.set(t.value, []);
        index.get(t.value).push({ path: f.path, offset: t.start, text: f.text });
      }
    }
  }
  return index;
}

// ── 工具 ──────────────────────────────────────────────────────────────

/** 字节偏移 -> { line, col }（0 基）。 */
function offsetToPosition(text, offset) {
  let line = 0;
  let col = 0;
  const end = Math.min(offset, text.length);
  for (let i = 0; i < end; i++) {
    if (text[i] === '\n') { line++; col = 0; } else col++;
  }
  return { line, col };
}

/** 在 token 数组中查找包含指定偏移的 token。 */
function tokenAt(tokens, offset) {
  for (const t of tokens) {
    if (offset >= t.start && offset <= t.end) return t;
  }
  return null;
}

// ── 光标处字段识别（补全用）───────────────────────────────────────────

const REF_FIELDS = new Set(['detect', 'parent', 'from', 'to', 'jump', 'via']);

function segmentsEq(a, b) {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

/**
 * 从某个 key 的结束位置起，若其值是数组则返回该数组 `]` 的偏移，否则返回 null。
 * 用于判断光标是否仍在 all_of / any_of 数组内部（补全用）。
 */
function valueArrayEnd(text, keyEnd) {
  const n = text.length;
  let i = keyEnd;

  const skipTrivia = () => {
    for (;;) {
      while (i < n && /\s/.test(text[i])) i++;
      if (text[i] === '/' && text[i + 1] === '/') {
        while (i < n && text[i] !== '\n') i++;
        continue;
      }
      if (text[i] === '/' && text[i + 1] === '*') {
        i += 2;
        while (i + 1 < n && !(text[i] === '*' && text[i + 1] === '/')) i++;
        i += 2;
        continue;
      }
      break;
    }
  };

  skipTrivia();
  if (text[i] === ':') i++;
  skipTrivia();
  if (text[i] !== '[') return null;

  let depth = 0;
  while (i < n) {
    const c = text[i];
    if (c === '"') {
      i++;
      while (i < n && text[i] !== '"') {
        if (text[i] === '\\') i++;
        i++;
      }
      i++;
      continue;
    }
    if (c === '/' && text[i + 1] === '/') {
      while (i < n && text[i] !== '\n') i++;
      continue;
    }
    if (c === '/' && text[i + 1] === '*') {
      i += 2;
      while (i + 1 < n && !(text[i] === '*' && text[i + 1] === '/')) i++;
      i += 2;
      continue;
    }
    if (c === '[') depth++;
    else if (c === ']') {
      depth--;
      if (depth === 0) return i;
    }
    i++;
  }
  return null;
}

/**
 * 判断光标 offset 所在位置正在编辑的“节点引用字段”。
 * 返回 { kind, value? }；非引用位置返回 null。
 *   - 光标落在已完成 token 内：kind 为该引用类型，value 为当前节点名；
 *   - 光标正在输入值（值未完成）：kind 为最近一个值未完成的引用字段；
 *   - 光标在 detect 组合写法的 all_of / any_of 数组内：kind 为 'detect'；
 *   - 其他位置返回 null。
 */
function fieldAt(text, offset, toks) {
  const t = tokenAt(toks, offset);
  if (t) {
    const k = refKind(t);
    return k ? { kind: k, value: t.value } : null;
  }
  // 正在输入：找光标前最近、且其值尚未完成的引用字段 key
  const before = toks
    .filter((x) => x.isKey && x.end <= offset)
    .sort((a, b) => b.end - a.end);
  for (const k of before) {
    // detect 组合写法：光标在 all_of / any_of 数组内 → 补全节点名
    if (isDetectLogicField(k)) {
      const end = valueArrayEnd(text, k.end);
      if (end !== null && offset < end) return { kind: 'detect' };
      continue;
    }
    if (!REF_FIELDS.has(k.value)) continue;
    const valPrefix = k.segments.concat(k.value);
    const hasVal = toks.some(
      (x) =>
        !x.isKey &&
        x.end <= offset &&
        x.segments.length >= valPrefix.length &&
        valPrefix.every((v, i) => v === x.segments[i])
    );
    if (!hasVal) return { kind: k.value };
  }
  return null;
}

module.exports = {
  stripJsonc,
  parseJsonc,
  scanJsoncStrings,
  refKind,
  isSceneRef,
  isNodeRef,
  isDetectLogicField,
  buildNodeIndex,
  offsetToPosition,
  tokenAt,
  fieldAt,
};
