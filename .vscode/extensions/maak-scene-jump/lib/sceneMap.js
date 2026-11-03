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

/**
 * 从 interface.json（JSONC，允许注释）中提取资源目录的相对路径。
 *
 * 与 maa-support 推导 Bundle 根目录的方式保持一致：
 *   - resource[].path
 *   - controller[].attach_resource_path（其中 {PROJECT_DIR} 表示 interface.json 所在目录）
 * interface.json 一律是 JSONC（Maa 官方模板自带注释），因此必须走 parseJsonc；
 * 用严格 JSON.parse 会解析失败并静默退化。
 *
 * 返回按出现顺序去重的相对路径数组；解析失败返回 []。
 */
function resourceDirsFromInterface(text) {
  let obj;
  try {
    obj = parseJsonc(text);
  } catch {
    return [];
  }
  const out = [];
  const seen = new Set();
  const add = (p) => {
    if (typeof p !== 'string') return;
    const norm = p.replace(/\{PROJECT_DIR\}/g, '.').replace(/\\/g, '/');
    if (!norm || seen.has(norm)) return;
    seen.add(norm);
    out.push(norm);
  };
  const asArray = (v) => (Array.isArray(v) ? v : typeof v === 'string' ? [v] : []);
  for (const res of asArray(obj && obj.resource)) {
    for (const p of asArray(res && res.path)) add(p);
  }
  for (const ctrl of asArray(obj && obj.controller)) {
    for (const p of asArray(ctrl && ctrl.attach_resource_path)) add(p);
  }
  return out;
}

// ── 字符串扫描（带 JSON 路径与偏移）──────────────────────────────────

/**
 * 扫描文本中所有字符串字面量，返回 token 数组：
 *   { segments, isKey?, value, start, end, valueStart, valueEnd }
 * segments 为从根到该字符串的 JSON 路径段（对象键为字符串，数组下标为数字）。
 * 对于对象键 token：segments 为该键所属对象的路径（不含键本身），isKey=true。
 * start/end 为字节偏移（不含注释，偏移与原文一致）；valueStart/valueEnd 为字面量
 * 去掉两侧引号后的内容范围，用于定义跳转/悬停的精确 Range。
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
    const end = i; // 结束引号之后（字符串未闭合时等于 n）
    // 值范围（不含两侧引号）：跳转/悬停用它定位，避免把引号算进定义范围。
    // 与 maa-support 用 jsonc-parser 节点 offset/length 时的 +1 / -2 修正同源。
    const valueStart = start + 1;
    const valueEnd = end > valueStart && text[end - 1] === '"' ? end - 1 : end;
    const raw = text.slice(start, end);
    let value;
    try { value = JSON.parse(raw); } catch { value = raw.slice(1, -1); }
    return { start, end, valueStart, valueEnd, value };
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
      tokens.push({
        segments: path.slice(),
        value: tok.value,
        start: tok.start,
        end: tok.end,
        valueStart: tok.valueStart,
        valueEnd: tok.valueEnd,
      });
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
        tokens.push({
          segments: path.slice(),
          isKey: true,
          value: keyTok.value,
          start: keyTok.start,
          end: keyTok.end,
          valueStart: keyTok.valueStart,
          valueEnd: keyTok.valueEnd,
        });
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
 *     'parent'  —— 场景的父场景（可为字符串或数组）
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
      const field = s[s.length - 2];
      // parent 数组中的元素（多父）
      if (field === 'parent') return 'parent';
      // detect 组合写法中的子识别节点：scenes.<场景>.detect.all_of[i] / .any_of[i]
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
    // 节点自身的 desc（pipeline 写法：{ "<节点名>": { "desc": "…", … } }），用于内联提示
    const descNodes = new Set();
    for (const t of tokens) {
      if (t.isKey && t.value === 'desc' && t.segments.length === 1) descNodes.add(t.segments[0]);
    }
    const descs = new Map();
    for (const t of tokens) {
      if (t.isKey || t.segments.length !== 2 || t.segments[1] !== 'desc') continue;
      if (!descNodes.has(t.segments[0]) || descs.has(t.segments[0])) continue;
      descs.set(t.segments[0], t.value);
    }
    for (const t of tokens) {
      if (t.isKey && t.segments.length === 0) {
        if (!index.has(t.value)) index.set(t.value, []);
        index.get(t.value).push({
          path: f.path,
          offset: t.start,
          // 定义范围应指向节点名本身，而不是它两侧的引号
          valueStart: t.valueStart,
          valueEnd: t.valueEnd,
          desc: descs.get(t.value) || '',
          text: f.text,
        });
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

// ── 引用诊断（跨文件一致性校验，与 tools/validate_scene_map.py 同一套规则）──

/** 收集 scenes 下的场景名（key）。 */
function collectSceneNames(tokens) {
  const names = new Set();
  for (const t of tokens) {
    if (t.isKey && t.segments.length === 1 && t.segments[0] === 'scenes') names.add(t.value);
  }
  return names;
}

/**
 * 对 scene_jump_map 文本产出引用诊断（纯逻辑，不依赖 vscode）。
 *
 * 只覆盖 JSON Schema 表达不了的跨文件一致性（形态类错误交给内置 JSON 校验，不重复报）：
 *   - 节点引用（detect / detect.all_of|any_of[i] / jump）能否在 pipeline 索引中解析到；
 *   - 场景引用（from / to / parent / via）是否在 scenes 中定义；
 *   - 场景名是否重复定义（重复时跳转只会到后一处）。
 *
 * opts:
 *   nodeIndex       Map<节点名, 定义位置数组>（pipeline 索引）
 *   sceneNames      Set<string>（可选，缺省从文本现算）
 *   incompleteIndex boolean，索引不完整时节点类诊断降级为 warning 并注明
 * 返回 [{ start, end, message, severity: 'error' | 'warning' }]，
 * start/end 为字符串字面量的范围（含两侧引号），与波浪线/查找引用的区间一致。
 */
function collectDiagnostics(text, opts = {}) {
  const toks = scanJsoncStrings(text);
  const names = opts.sceneNames instanceof Set ? opts.sceneNames : collectSceneNames(toks);
  const nodeIndex = opts.nodeIndex instanceof Map ? opts.nodeIndex : new Map();
  const incomplete = !!opts.incompleteIndex;
  const nodeSeverity = incomplete ? 'warning' : 'error';
  const nodeSuffix = incomplete ? '（索引可能不完整）' : '';
  const out = [];

  // 场景名重复定义：buildSceneInfo / 查找引用会静默覆盖前者
  const defined = new Map();
  for (const t of toks) {
    if (!(t.isKey && t.segments.length === 1 && t.segments[0] === 'scenes')) continue;
    if (defined.has(t.value)) {
      out.push({
        start: t.start,
        end: t.end,
        message: `场景名 ${t.value} 重复定义；跳转只会到后一处`,
        severity: 'warning',
      });
    } else {
      defined.set(t.value, t.start);
    }
  }

  for (const t of toks) {
    const kind = refKind(t);
    if (!kind || kind === 'scene') continue;
    if (isSceneRef(kind)) {
      if (!names.has(t.value)) {
        out.push({
          start: t.start,
          end: t.end,
          message: `${kind} 引用的场景未在 scenes 中定义：${t.value}`,
          severity: 'error',
        });
      }
    } else if (!nodeIndex.has(t.value)) {
      out.push({
        start: t.start,
        end: t.end,
        message: `${kind} 引用的节点未在 pipeline 资源中找到：${t.value}${nodeSuffix}`,
        severity: nodeSeverity,
      });
    }
  }
  return out;
}

// ── 内联提示（引用处的灰色 desc，同 maa-support 的任务文档提示）──────────

/** 内联提示默认最大长度（超出部分省略，完整内容放 tooltip）。 */
const INLAY_HINT_MAX_CHARS = 40;

/**
 * 为 scene_jump_map 引用收集内联提示（纯逻辑，不依赖 vscode）。
 *
 *   - 场景引用（from / to / parent / via）→ scenes.<name>.desc
 *   - 节点引用（detect / detect.all_of|any_of[i] / jump）→ pipeline 节点的 desc
 *   - 场景名（scenes key）本身不提示：其 desc 就在紧邻的字段里，重复显示只会变吵
 *
 * 位置取被注解字面量的末尾（与 maa-support 的 location.offset + location.length 一致），
 * 由调用方按可见 range 过滤。
 * opts:
 *   sceneDescs  Map<场景名, desc>
 *   nodeIndex   Map<节点名, 定义数组>（缺省则不给节点提示）
 *   maxLength   省略阈值，缺省 INLAY_HINT_MAX_CHARS
 * 返回 [{ position, text, tooltip }]，position 为字面量结束处的偏移。
 */
function collectInlayHints(text, opts = {}) {
  const toks = scanJsoncStrings(text);
  const sceneDescs = opts.sceneDescs instanceof Map ? opts.sceneDescs : new Map();
  const nodeIndex = opts.nodeIndex instanceof Map ? opts.nodeIndex : null;
  const max = typeof opts.maxLength === 'number' ? opts.maxLength : INLAY_HINT_MAX_CHARS;
  const out = [];
  for (const t of toks) {
    const kind = refKind(t);
    if (!kind || kind === 'scene') continue;
    let desc = '';
    if (isSceneRef(kind)) {
      desc = sceneDescs.get(t.value) || '';
    } else if (nodeIndex) {
      const defs = nodeIndex.get(t.value);
      desc = defs && defs.length ? defs[0].desc || '' : '';
    }
    if (!desc) continue;
    out.push({
      position: t.end,
      text: desc.length > max ? `${desc.slice(0, max - 1)}…` : desc,
      tooltip: desc.length > max ? desc : '',
    });
  }
  return out;
}

module.exports = {
  stripJsonc,
  parseJsonc,
  resourceDirsFromInterface,
  scanJsoncStrings,
  refKind,
  isSceneRef,
  isNodeRef,
  isDetectLogicField,
  buildNodeIndex,
  offsetToPosition,
  tokenAt,
  fieldAt,
  collectSceneNames,
  collectDiagnostics,
  collectInlayHints,
  INLAY_HINT_MAX_CHARS,
};
