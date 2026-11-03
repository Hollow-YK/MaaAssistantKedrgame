'use strict';
/**
 * MAK SceneJump 节点跳转 —— 工作区扩展入口。
 *
 * 为 agent/custom/action/scene_jump_map.json 提供两类引用的跳转：
 *   - 场景引用（scenes 场景名 key、parent、from、to、via）→ 跳到 scenes.<name> 定义
 *   - 节点引用（detect、jump）→ 跳到 pipeline 资源中的节点定义
 * 并提供：悬停提示、查找引用（Shift+F12）、文档链接（下划线可点击）、节点名补全、
 * 引用诊断（Problems 面板 + 波浪线，规则与 tools/validate_scene_map.py 一致）。
 *
 * 能力与 nekosu.maa-support 的 Pipeline 语义分析同源（建立节点索引并解析引用），
 * 因 maa-support 未暴露公共 API，此处独立实现其等价逻辑（见 lib/sceneMap.js）。
 * 其中资源目录推导、JSONC 解析、重建防抖三点与 maa-support 的做法保持一致：
 *   - 资源目录 = interface.json 所在目录下的 resource[].path + controller[].attach_resource_path；
 *   - interface.json 一律按 JSONC 解析（Maa 官方模板自带注释）；
 *   - 文件变更后延迟合并重建（maa-support ContentJson.dispatchFlush 为 100ms），
 *     重建期间到来的事件标记为“再跑一次”，避免并发重建。
 */

const path = require('path');
const vscode = require('vscode');
const {
  scanJsoncStrings,
  parseJsonc,
  resourceDirsFromInterface,
  refKind,
  isSceneRef,
  tokenAt,
  fieldAt,
  buildNodeIndex,
  offsetToPosition,
  collectDiagnostics,
} = require('./lib/sceneMap');

const MAP_PATTERN = '**/agent/custom/action/scene_jump_map.json';
/** 地图已关联为 jsonc（支持注释），同时覆盖 json/jsonc 以兼容不同编辑器设置。 */
const MAP_SELECTOR = [
  { language: 'jsonc', pattern: MAP_PATTERN },
  { language: 'json', pattern: MAP_PATTERN },
];
/** 找不到 assets/interface.json 时的兜底资源目录（与 Maa 插件默认一致）。 */
const FALLBACK_RESOURCE_DIRS = [
  'assets/resource',
  'assets/resource_bilibili',
  'assets/resource_taptap',
];
/** 单次索引扫描的文件上限，达到上限时告警而不是静默截断。 */
const MAX_INDEX_FILES = 8000;
/** 文件变更后的重建合并窗口（同 maa-support 的 100ms）。 */
const REBUILD_DEBOUNCE_MS = 100;
/** 诊断刷新防抖（按文档）。 */
const DIAG_DEBOUNCE_MS = 200;

let nodeIndex = new Map(); // pipeline 节点名 -> 定义位置（资源文件变更时重建）
let watchers = [];
let watchKey = ''; // 当前监视的资源目录集合，用于判断是否需要重建监视器
let rebuildTimer = null;
let rebuildReason = '';
let rebuilding = false;
let rebuildAgain = false;
let output = null;
let statusItem = null;
let diagnostics = null;
let indexReady = false; // 首建索引完成前不出诊断，避免把未索引误报为“找不到节点”
let indexIncomplete = false; // 走兜底目录或触顶时，节点类诊断降级为 warning
const diagTimers = new Map(); // uri -> 诊断防抖定时器

function log(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  if (output) output.appendLine(line);
  else console.log(`[SceneJump] ${line}`);
}

/** 读取文本文件；不存在或不可读时返回 null（不抛异常）。 */
async function readText(uri) {
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}

async function exists(uri) {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

/** 取父目录（不依赖 Uri.joinPath 对 '..' 的归一化行为）。 */
function parentUri(uri) {
  return uri.with({ path: uri.path.replace(/\/[^/]*$/, '') });
}

/**
 * 解析要索引的资源目录与 interface.json 位置（与 maa-support 的 Bundle 根目录推导一致）。
 * 只看工作区自身的 assets/interface.json，不会把 install/、Android/ 等部署快照扫进来；
 * interface.json 是 JSONC，必须用 parseJsonc 解析（见 lib/sceneMap.js）。
 * 只保留真实存在的目录；一个都没解析到时回退到默认资源目录。
 */
async function resolveResourceUris() {
  const dirs = [];
  const ifaces = [];
  const seen = new Set();
  let usedFallback = false;
  const push = async (uri) => {
    const key = uri.toString();
    if (seen.has(key)) return;
    if (!(await exists(uri))) return;
    seen.add(key);
    dirs.push(uri);
  };

  for (const folder of vscode.workspace.workspaceFolders || []) {
    const iface = vscode.Uri.joinPath(folder.uri, 'assets', 'interface.json');
    const text = await readText(iface);
    if (text === null) continue;
    ifaces.push(iface);
    const base = parentUri(iface);
    for (const rel of resourceDirsFromInterface(text)) {
      const clean = rel.replace(/^\.\//, '').replace(/\/+$/, '');
      if (!clean || clean.startsWith('/')) continue;
      await push(vscode.Uri.joinPath(base, clean));
    }
  }

  if (!dirs.length) {
    log('未从 assets/interface.json 解析到可用资源目录，回退到默认资源目录');
    usedFallback = true;
    for (const folder of vscode.workspace.workspaceFolders || []) {
      for (const d of FALLBACK_RESOURCE_DIRS) {
        await push(vscode.Uri.joinPath(folder.uri, d));
      }
    }
  }
  return { dirs, ifaces, usedFallback };
}

/** 收集 pipeline/tasks 下的 JSON/JSONC 文本（含资源根目录的 default_pipeline.json）。 */
async function collectIndexFiles(dirs) {
  const files = [];
  const seen = new Set();
  let capped = false;
  const add = async (uri) => {
    const key = uri.fsPath;
    if (seen.has(key)) return;
    const text = await readText(uri);
    if (text === null) return;
    seen.add(key);
    files.push({ path: key, text });
  };

  for (const dir of dirs) {
    for (const sub of ['pipeline', 'tasks']) {
      const uris = await vscode.workspace.findFiles(
        new vscode.RelativePattern(vscode.Uri.joinPath(dir, sub), '**/*.{json,jsonc}'),
        '**/node_modules/**',
        MAX_INDEX_FILES
      );
      if (uris.length >= MAX_INDEX_FILES) {
        capped = true;
        log(`⚠ ${dir.fsPath} 下 ${sub} 文件数达到上限 ${MAX_INDEX_FILES}，索引可能不完整`);
      }
      for (const uri of uris) await add(uri);
    }
    // 与 Maa 插件一致，额外收录资源根目录下的 default_pipeline.json
    await add(vscode.Uri.joinPath(dir, 'default_pipeline.json'));
  }
  return { files, capped };
}

function setupWatchers(dirs, ifaces) {
  for (const w of watchers) w.dispose();
  watchers = [];
  const watch = (pattern, delay, reason) => {
    const w = vscode.workspace.createFileSystemWatcher(pattern);
    const fire = () => scheduleRebuild(delay, reason);
    w.onDidChange(fire);
    w.onDidCreate(fire);
    w.onDidDelete(fire);
    watchers.push(w);
  };
  for (const dir of dirs) {
    watch(new vscode.RelativePattern(dir, '**/*.{json,jsonc}'), REBUILD_DEBOUNCE_MS, '资源文件变更');
  }
  for (const iface of ifaces) {
    // interface.json 变化可能改变资源目录集合（等价于 maa-support 的 interfaceChanged → updatePaths）
    watch(new vscode.RelativePattern(parentUri(iface), 'interface.json'), 0, 'interface.json 变更');
  }
}

/** 延迟合并重建：窗口内的多个事件只触发一次（对应 maa-support 的 dispatchFlush）。 */
function scheduleRebuild(delay = REBUILD_DEBOUNCE_MS, reason = '文件变更') {
  rebuildReason = reason;
  if (rebuildTimer) return;
  rebuildTimer = setTimeout(() => {
    rebuildTimer = null;
    void runRebuild(rebuildReason);
  }, delay);
}

async function rebuildIndex(reason) {
  const started = Date.now();
  const { dirs, ifaces, usedFallback } = await resolveResourceUris();
  const key = [...dirs, ...ifaces].map((u) => u.toString()).join('|');
  if (key !== watchKey) {
    watchKey = key;
    setupWatchers(dirs, ifaces);
  }

  const { files, capped } = await collectIndexFiles(dirs);
  nodeIndex = buildNodeIndex(files);
  indexIncomplete = usedFallback || capped;
  indexReady = true;

  const ms = Date.now() - started;
  log(
    `${reason}：索引 ${nodeIndex.size} 个节点 / ${files.length} 个文件` +
      `（${dirs.length} 个资源目录，用时 ${ms}ms${indexIncomplete ? '，索引可能不完整' : ''}）`
  );
  if (statusItem) {
    statusItem.text = `$(symbol-namespace) SceneJump ${nodeIndex.size}`;
    statusItem.tooltip = `SceneJump 已索引 ${nodeIndex.size} 个 pipeline 节点（${files.length} 个文件，${ms}ms）\n点击刷新索引`;
  }
  // 索引变化后重算已打开地图的诊断（此前可能因索引缺失而误报/漏报）
  refreshAllDiagnostics();
}

/**
 * 串行化重建：进行中时只标记“再跑一次”，避免并发重建（对应 maa-support 的 duringFlush/needFlush）。
 * 任何异常都只记录日志，不影响已注册的 provider 与手动刷新命令。
 */
async function runRebuild(reason) {
  if (rebuilding) {
    rebuildAgain = true;
    return;
  }
  rebuilding = true;
  try {
    await rebuildIndex(reason);
  } catch (err) {
    log(`✗ 索引重建失败：${err && err.message ? err.message : err}`);
    if (statusItem) {
      statusItem.text = '$(warning) SceneJump';
      statusItem.tooltip = `SceneJump 索引重建失败：${err && err.message ? err.message : err}`;
    }
  } finally {
    rebuilding = false;
    if (rebuildAgain) {
      rebuildAgain = false;
      scheduleRebuild(0, '排程合并');
    }
  }
}

/* ── SceneJump 文档内解析（不依赖缓存，编辑后立即可用）──────────────── */

function rel(p) {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root || !p.startsWith(root)) return p;
  // 与 tools/validate_scene_map.py 的输出保持一致：统一用 '/'
  return path.relative(root, p).split(path.sep).join('/');
}

function docTokens(doc) {
  return scanJsoncStrings(doc.getText());
}

function positionAt(text, offset) {
  const pos = offsetToPosition(text, offset);
  return new vscode.Position(pos.line, pos.col);
}

/**
 * 从当前文档现算场景信息（不依赖缓存，编辑后立即可用）。
 * 返回 { names: Set, locs: Map<场景名, Location>, defs: Map<场景名, { desc, def }> }
 */
function buildSceneInfo(doc) {
  const names = new Set();
  const locs = new Map();
  const defs = new Map();
  const toks = docTokens(doc);
  let scenesObj = {};
  try {
    const obj = parseJsonc(doc.getText());
    if (obj && obj.scenes && typeof obj.scenes === 'object') scenesObj = obj.scenes;
  } catch {
    /* 非严格 JSON 时仅用 token 信息 */
  }
  for (const t of toks) {
    if (t.isKey && t.segments.length === 1 && t.segments[0] === 'scenes') {
      names.add(t.value);
      locs.set(t.value, new vscode.Location(doc.uri, new vscode.Range(doc.positionAt(t.start), doc.positionAt(t.end))));
      const data = scenesObj[t.value] && typeof scenesObj[t.value] === 'object' ? scenesObj[t.value] : {};
      defs.set(t.value, {
        desc: typeof data.desc === 'string' ? data.desc : '',
        def: `"${t.value}": ${JSON.stringify(data, null, 4)}`,
      });
    }
  }
  return { names, locs, defs };
}

function defsFor(token, kind, sceneInfo) {
  if (kind === 'scene') {
    // 场景 key 本身即定义，不提供跳转
    return [];
  }
  if (isSceneRef(kind)) {
    // 场景引用：跳到 scene_jump_map.json 的 scenes.<name> 定义
    const loc = sceneInfo.locs.get(token.value);
    return loc ? [loc] : [];
  }
  // 节点引用（detect / jump）：跳到 pipeline 资源中的节点定义
  return (nodeIndex.get(token.value) || []).map((d) => {
    // 定义范围指向节点名本身（valueStart/valueEnd 已排除引号），而不是包含引号
    const from = d.valueStart !== undefined ? d.valueStart : d.offset;
    const to = d.valueEnd !== undefined ? d.valueEnd : from + token.value.length;
    return new vscode.Location(
      vscode.Uri.file(d.path),
      new vscode.Range(positionAt(d.text, from), positionAt(d.text, to))
    );
  });
}

/* ── 引用诊断（Problems / 波浪线）─────────────────────────────────── */

/** 是否为本扩展关心的 scene_jump_map 文档。 */
function isMapDoc(doc) {
  return vscode.languages.match(MAP_SELECTOR, doc) > 0;
}

/** 按文档防抖刷新诊断。 */
function scheduleDiagnostics(doc) {
  if (!diagnostics || !indexReady || !isMapDoc(doc)) return;
  const key = doc.uri.toString();
  clearTimeout(diagTimers.get(key));
  diagTimers.set(
    key,
    setTimeout(() => {
      diagTimers.delete(key);
      publishDiagnostics(doc);
    }, DIAG_DEBOUNCE_MS)
  );
}

function publishDiagnostics(doc) {
  if (!diagnostics) return;
  const list = collectDiagnostics(doc.getText(), {
    nodeIndex,
    incompleteIndex: indexIncomplete,
  }).map((d) => {
    const diag = new vscode.Diagnostic(
      new vscode.Range(doc.positionAt(d.start), doc.positionAt(d.end)),
      d.message,
      d.severity === 'warning' ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
    );
    diag.source = 'SceneJump';
    return diag;
  });
  diagnostics.set(doc.uri, list);
}

/** 索引变化后重算所有已打开地图的诊断。 */
function refreshAllDiagnostics() {
  if (!diagnostics) return;
  for (const doc of vscode.workspace.textDocuments) {
    if (!isMapDoc(doc)) continue;
    if (indexReady) publishDiagnostics(doc);
    else diagnostics.delete(doc.uri);
  }
}

async function activate(context) {
  output = vscode.window.createOutputChannel('SceneJump');
  context.subscriptions.push(output);

  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusItem.command = 'maak-scene-jump.refreshIndex';
  statusItem.text = '$(symbol-namespace) SceneJump …';
  statusItem.tooltip = 'SceneJump 节点索引：正在建立…';
  statusItem.show();
  context.subscriptions.push(statusItem);

  // 引用诊断集合（单独命名，与 maa-support 的 "maa" 集合互不干扰）
  diagnostics = vscode.languages.createDiagnosticCollection('scenejump');
  context.subscriptions.push(diagnostics);
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((doc) => scheduleDiagnostics(doc)),
    vscode.workspace.onDidChangeTextDocument((e) => scheduleDiagnostics(e.document)),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      const key = doc.uri.toString();
      clearTimeout(diagTimers.get(key));
      diagTimers.delete(key);
      if (diagnostics) diagnostics.delete(doc.uri);
    })
  );

  const selector = MAP_SELECTOR;

  // 定义跳转（Ctrl+Click / F12）
  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider(selector, {
      provideDefinition(doc, position) {
        const t = tokenAt(docTokens(doc), doc.offsetAt(position));
        if (!t) return null;
        const kind = refKind(t);
        if (!kind) return null;
        const locs = defsFor(t, kind, buildSceneInfo(doc));
        return locs.length ? locs : null;
      },
    })
  );

  // 悬停提示
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(selector, {
      provideHover(doc, position) {
        const t = tokenAt(docTokens(doc), doc.offsetAt(position));
        if (!t) return null;
        const kind = refKind(t);
        if (!kind) return null;
        const sceneInfo = buildSceneInfo(doc);
        const md = new vscode.MarkdownString();
        const scene = sceneInfo.defs.get(t.value);

        if (kind === 'scene') {
          // 场景定义本身：显示名称 + desc（无跳转）
          md.appendMarkdown(`**${t.value}** \`(场景定义)\``);
          if (scene && scene.desc) md.appendMarkdown(`\n\n${scene.desc}`);
          return new vscode.Hover(md);
        }

        if (isSceneRef(kind)) {
          // 场景引用：显示 desc + 场景定义内容 + 位置
          const title = scene && scene.desc ? `**${t.value}** — ${scene.desc}` : `**${t.value}**`;
          md.appendMarkdown(`${title}  \`(${kind} · 场景)\``);
          if (scene) {
            md.appendCodeblock(scene.def, 'json');
            const loc = sceneInfo.locs.get(t.value);
            if (loc) {
              md.appendMarkdown(`\n定义位置: \`${rel(loc.uri.fsPath)}:${loc.range.start.line + 1}\``);
            }
          } else {
            md.appendMarkdown('\n\n⚠ 该场景未在 scenes 中定义');
          }
          return new vscode.Hover(md);
        }

        // 节点引用（detect / jump）：显示节点名 + pipeline 定义位置
        const defs = nodeIndex.get(t.value) || [];
        md.appendMarkdown(`**${t.value}**  \`(${kind} · 节点)\``);
        if (!defs.length) {
          md.appendMarkdown('\n\n⚠ 未在 pipeline 资源中找到该节点定义');
        } else {
          md.appendMarkdown('\n\n**定义位置**\n\n');
          for (const d of defs.slice(0, 6)) {
            const from = d.valueStart !== undefined ? d.valueStart : d.offset;
            md.appendMarkdown(`- \`${rel(d.path)}:${offsetToPosition(d.text, from).line + 1}\`\n`);
          }
          if (defs.length > 6) md.appendMarkdown(`- …另有 ${defs.length - 6} 处\n`);
        }
        return new vscode.Hover(md);
      },
    })
  );

  // 查找引用（Shift+F12）
  context.subscriptions.push(
    vscode.languages.registerReferenceProvider(selector, {
      provideReferences(doc, position) {
        const t = tokenAt(docTokens(doc), doc.offsetAt(position));
        if (!t || !refKind(t)) return null;
        const out = [];
        for (const x of docTokens(doc)) {
          if (refKind(x) && x.value === t.value) {
            out.push(
              new vscode.Location(
                doc.uri,
                new vscode.Range(doc.positionAt(x.start), doc.positionAt(x.end))
              )
            );
          }
        }
        return out;
      },
    })
  );

  // 文档链接（下划线 + Ctrl+Click）
  context.subscriptions.push(
    vscode.languages.registerDocumentLinkProvider(selector, {
      provideDocumentLinks(doc) {
        const sceneInfo = buildSceneInfo(doc);
        const links = [];
        for (const t of docTokens(doc)) {
          const kind = refKind(t);
          if (!kind || kind === 'scene') continue; // 场景 key 自身即定义，不加链接
          const defs = defsFor(t, kind, sceneInfo);
          if (!defs.length) continue;
          const target = defs[0].uri.with({ fragment: `L${defs[0].range.start.line + 1}` });
          links.push(new vscode.DocumentLink(new vscode.Range(doc.positionAt(t.start), doc.positionAt(t.end)), target));
        }
        return links;
      },
    })
  );

  // 节点名补全
  context.subscriptions.push(
    vscode.languages.registerCompletionItemProvider(
      selector,
      {
        provideCompletionItems(doc, position) {
          const f = fieldAt(doc.getText(), doc.offsetAt(position), docTokens(doc));
          if (!f || f.kind === 'scene') {
            // 场景名（key）自身即定义，不是引用位置，不给候选
            return [];
          }
          const items = [];
          const add = (name) => {
            const it = new vscode.CompletionItem(name, vscode.CompletionItemKind.Reference);
            const w = doc.getWordRangeAtPosition(position);
            if (w) it.range = w;
            items.push(it);
          };
          if (f.kind === 'from' || f.kind === 'to' || f.kind === 'parent' || f.kind === 'via') {
            // 场景引用：补全 scenes 中定义的场景名
            for (const s of [...buildSceneInfo(doc).names].sort()) add(s);
          } else {
            // 节点引用（detect / jump）：补全 pipeline 节点名
            for (const n of [...nodeIndex.keys()].sort()) add(n);
          }
          return items;
        },
      },
      '"'
    )
  );

  // 手动刷新索引
  context.subscriptions.push(
    vscode.commands.registerCommand('maak-scene-jump.refreshIndex', async () => {
      await runRebuild('手动刷新');
      vscode.window.setStatusBarMessage('SceneJump 节点索引已刷新', 3000);
    })
  );

  // provider 先就位，首建索引放在最后：即使索引失败也保留跳转/补全与手动刷新
  await runRebuild('激活');
}

function deactivate() {
  if (rebuildTimer) {
    clearTimeout(rebuildTimer);
    rebuildTimer = null;
  }
  for (const timer of diagTimers.values()) clearTimeout(timer);
  diagTimers.clear();
  for (const w of watchers) w.dispose();
  watchers = [];
}

module.exports = { activate, deactivate };