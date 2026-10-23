<template>
  <div class="qs-wizard">
    <p v-if="current !== 'result'" class="qs-progress">
      第 {{ history.length + 1 }} 题
    </p>

    <template v-if="current === 'devices'">
      <p class="qs-question">您可以使用哪种设备？（多选）</p>
      <div class="qs-options qs-options--multi">
        <button
          v-for="option in DEVICE_OPTIONS"
          :key="option.value"
          type="button"
          class="qs-option"
          :class="{ selected: devices.includes(option.value) }"
          :aria-pressed="devices.includes(option.value)"
          @click="toggleDevice(option.value)"
        >
          <span class="qs-option-title">{{ option.label }}</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-next" :disabled="devices.length === 0" @click="next">
          下一题
        </button>
      </p>
    </template>

    <template v-else-if="current === 'platform'">
      <p class="qs-question">您更想在哪种设备上运行 MAK？（单选）</p>
      <div class="qs-options">
        <button
          type="button"
          class="qs-option"
          :class="{ selected: platformPref === 'android' }"
          :aria-pressed="platformPref === 'android'"
          @click="platformPref = 'android'"
        >
          <span class="qs-option-title">手机/平板（Android）</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: platformPref === 'pc' }"
          :aria-pressed="platformPref === 'pc'"
          @click="platformPref = 'pc'"
        >
          <span class="qs-option-title">电脑（Windows）</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: platformPref === 'both' }"
          :aria-pressed="platformPref === 'both'"
          @click="platformPref = 'both'"
        >
          <span class="qs-option-title">二者均可</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-back" @click="back">上一题</button>
        <button type="button" class="qs-next" :disabled="!platformPref" @click="next">下一题</button>
      </p>
    </template>

    <template v-else-if="current === 'shizuku'">
      <p class="qs-question">您是否会使用 Shizuku，或手机已经 ROOT？（单选）</p>
      <div class="qs-options">
        <button
          type="button"
          class="qs-option"
          :class="{ selected: shizuku === 'both' }"
          :aria-pressed="shizuku === 'both'"
          @click="shizuku = 'both'"
        >
          <span class="qs-option-title">会使用 Shizuku，且手机已 ROOT</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: shizuku === 'root-only' }"
          :aria-pressed="shizuku === 'root-only'"
          @click="shizuku = 'root-only'"
        >
          <span class="qs-option-title">不会使用 Shizuku，但手机已 ROOT</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: shizuku === 'shizuku-only' }"
          :aria-pressed="shizuku === 'shizuku-only'"
          @click="shizuku = 'shizuku-only'"
        >
          <span class="qs-option-title">会使用 Shizuku，但手机未 ROOT</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: shizuku === 'none' }"
          :aria-pressed="shizuku === 'none'"
          @click="shizuku = 'none'"
        >
          <span class="qs-option-title">不会使用 Shizuku，且手机未 ROOT</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: shizuku === 'unknown' }"
          :aria-pressed="shizuku === 'unknown'"
          @click="shizuku = 'unknown'"
        >
          <span class="qs-option-title">我不知道</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-back" @click="back">上一题</button>
        <button type="button" class="qs-next" :disabled="!shizuku" @click="next">下一题</button>
      </p>
    </template>

    <template v-else-if="current === 'learnShizuku'">
      <p class="qs-question">您是否愿意学习 Shizuku 相关操作？（单选）</p>
      <div class="qs-options">
        <button
          type="button"
          class="qs-option"
          :class="{ selected: learnShizuku === true }"
          :aria-pressed="learnShizuku === true"
          @click="learnShizuku = true"
        >
          <span class="qs-option-title">是</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: learnShizuku === false }"
          :aria-pressed="learnShizuku === false"
          @click="learnShizuku = false"
        >
          <span class="qs-option-title">否</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-back" @click="back">上一题</button>
        <button type="button" class="qs-next" :disabled="learnShizuku === null" @click="next">
          下一题
        </button>
      </p>
    </template>

    <template v-else-if="current === 'emulator'">
      <p class="qs-question">您电脑是否有安装模拟器？（单选）</p>
      <div class="qs-options">
        <button
          type="button"
          class="qs-option"
          :class="{ selected: emulator === 'can-install' }"
          :aria-pressed="emulator === 'can-install'"
          @click="emulator = 'can-install'"
        >
          <span class="qs-option-title">未安装模拟器，但可以安装模拟器</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: emulator === 'no-install' }"
          :aria-pressed="emulator === 'no-install'"
          @click="emulator = 'no-install'"
        >
          <span class="qs-option-title">未安装模拟器，且不想安装模拟器</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: emulator === 'installed' }"
          :aria-pressed="emulator === 'installed'"
          @click="emulator = 'installed'"
        >
          <span class="qs-option-title">已安装模拟器</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-back" @click="back">上一题</button>
        <button type="button" class="qs-next" :disabled="!emulator" @click="next">下一题</button>
      </p>
    </template>

    <template v-else-if="current === 'uiPref'">
      <p class="qs-question">您更喜欢 MXU 还是 MFAA？（单选）</p>
      <div class="qs-options">
        <button
          type="button"
          class="qs-option"
          :class="{ selected: uiPref === 'mxu' }"
          :aria-pressed="uiPref === 'mxu'"
          @click="uiPref = 'mxu'"
        >
          <span class="qs-option-title">MXU</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: uiPref === 'mfaa' }"
          :aria-pressed="uiPref === 'mfaa'"
          @click="uiPref = 'mfaa'"
        >
          <span class="qs-option-title">MFAA</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: uiPref === 'both' }"
          :aria-pressed="uiPref === 'both'"
          @click="uiPref = 'both'"
        >
          <span class="qs-option-title">二者均可</span>
        </button>
        <button
          type="button"
          class="qs-option"
          :class="{ selected: uiPref === 'unknown' }"
          :aria-pressed="uiPref === 'unknown'"
          @click="uiPref = 'unknown'"
        >
          <span class="qs-option-title">我不知道</span>
        </button>
      </div>
      <p class="qs-actions">
        <button type="button" class="qs-back" @click="back">上一题</button>
        <button type="button" class="qs-next" :disabled="!uiPref" @click="next">下一题</button>
      </p>
    </template>

    <div v-else class="qs-result">
      <template v-if="!hasSupported">
        <p class="qs-question">您所选的设备上均不能运行 MAK</p>
        <p class="qs-reason">
          MAK 目前仅支持 Windows 与 Android。请重新选择设备，或更换运行设备后再试。
        </p>
        <p class="qs-actions">
          <button type="button" class="qs-back" @click="back">上一题</button>
          <button type="button" class="qs-back" @click="reset">重新选择</button>
        </p>
      </template>

      <template v-else>
        <p class="qs-question">
          {{ winners.length > 1 ? "以下方案得分相同，可任选其一" : `建议：使用 ${winners[0].title}` }}
        </p>

        <div v-for="item in winners" :key="item.id" class="qs-winner">
          <p class="qs-reason">{{ item.reason }}</p>
          <ul class="qs-points">
            <li v-for="point in item.points" :key="point">{{ point }}</li>
          </ul>
          <p class="qs-link-row">
            <a class="qs-link" :href="withBase(item.path)">前往 {{ item.title }} →</a>
          </p>
        </div>

        <p class="qs-actions">
          <button type="button" class="qs-back" @click="back">上一题</button>
          <button type="button" class="qs-back" @click="reset">重新选择</button>
        </p>

        <table class="qs-scores">
          <caption>各方案得分</caption>
          <thead>
            <tr>
              <th scope="col">方案</th>
              <th scope="col">得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in ranking" :key="item.id" :class="{ winner: item.score === maxScore }">
              <td>{{ item.title }}</td>
              <td>{{ item.score }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { withBase } from "vuepress/client";

type Device = "windows" | "macos" | "android" | "ios" | "harmony";
type PlatformPref = "android" | "pc" | "both";
type Shizuku = "both" | "root-only" | "shizuku-only" | "none" | "unknown";
type Emulator = "can-install" | "no-install" | "installed";
type UiPref = "mxu" | "mfaa" | "both" | "unknown";
type UiId = "mxu" | "mfaa" | "maafwapp";
type StepId = "devices" | "platform" | "shizuku" | "learnShizuku" | "emulator" | "uiPref";

interface UiOption {
  id: UiId;
  title: string;
  reason: string;
  points: string[];
  path: string;
}

interface RankedOption extends UiOption {
  score: number;
}

const DEVICE_OPTIONS: { value: Device; label: string }[] = [
  { value: "windows", label: "电脑（Windows）" },
  { value: "macos", label: "苹果电脑（macOS）" },
  { value: "android", label: "手机/平板（Android）" },
  { value: "ios", label: "苹果手机/平板（iOS）" },
  { value: "harmony", label: "纯血鸿蒙设备（HarmonyOS NEXT）" },
];

const UI_OPTIONS: Record<UiId, UiOption> = {
  mxu: {
    id: "mxu",
    title: "MXU",
    reason: "MXU 的配置步骤最少，相关文档也最为完整，适合首次使用。",
    points: [
      "适用于 Windows 10 / 11，需要先安装模拟器。",
      "模拟器分辨率须设置为 16:9，推荐 1280×720 或 1920×1080。",
    ],
    path: "/guide/quickstart/mxu",
  },
  mfaa: {
    id: "mfaa",
    title: "MFAA",
    reason:
      "MFAA 将任务、设置、实时视图与日志分区展示，适合需要同时查看配置与运行状态的使用者。",
    points: [
      "适用于 Windows 10 / 11，需要先安装模拟器。",
      "模拟器分辨率须设置为 16:9，推荐 1280×720 或 1920×1080。",
    ],
    path: "/guide/quickstart/mfaa",
  },
  maafwapp: {
    id: "maafwapp",
    title: "MaaFwApp（安卓）",
    reason:
      "安卓端无需电脑与模拟器，资源随 APK 绑定，适合没有可用电脑，或希望任务在手机后台运行的场景。",
    points: [
      "需要 Android 10（API 29）及以上，Android 9 及以下无法运行。",
      "需要 Shizuku 或 root 权限，无需连接 ADB。",
      "资源随 APK 绑定，不支持热更新。",
    ],
    path: "/guide/quickstart/maafwapp",
  },
};

const devices = ref<Device[]>([]);
const platformPref = ref<PlatformPref | null>(null);
const shizuku = ref<Shizuku | null>(null);
const learnShizuku = ref<boolean | null>(null);
const emulator = ref<Emulator | null>(null);
const uiPref = ref<UiPref | null>(null);

const current = ref<StepId | "result">("devices");
const history = ref<StepId[]>([]);

const hasWindows = computed(() => devices.value.includes("windows"));
const hasAndroid = computed(() => devices.value.includes("android"));
const hasSupported = computed(() => hasWindows.value || hasAndroid.value);
const hasBothPlatforms = computed(() => hasWindows.value && hasAndroid.value);

const candidates = computed<UiOption[]>(() => {
  const list: UiOption[] = [];
  if (hasWindows.value) {
    list.push(UI_OPTIONS.mxu, UI_OPTIONS.mfaa);
  }
  if (hasAndroid.value) {
    list.push(UI_OPTIONS.maafwapp);
  }
  return list;
});

const scores = computed<Record<UiId, number>>(() => {
  const result: Record<UiId, number> = { mxu: 0, mfaa: 0, maafwapp: 0 };

  if (hasBothPlatforms.value) {
    if (platformPref.value === "android") {
      result.maafwapp += 1;
    }
    if (platformPref.value === "pc") {
      result.mxu += 1;
      result.mfaa += 1;
    }
  }

  if (hasAndroid.value && (shizuku.value === "none" || shizuku.value === "unknown")) {
    result.maafwapp -= 3;
    if (learnShizuku.value === true) {
      result.maafwapp += 1;
    }
    if (learnShizuku.value === false) {
      result.maafwapp -= 1;
    }
  }

  if (hasWindows.value) {
    if (emulator.value === "installed") {
      result.mxu += 1;
      result.mfaa += 1;
    }
    if (emulator.value === "no-install") {
      result.mxu -= 1;
      result.mfaa -= 1;
    }
    if (uiPref.value === "mxu") {
      result.mfaa -= 1;
    }
    if (uiPref.value === "mfaa") {
      result.mxu -= 1;
    }
    if (uiPref.value === "both" || uiPref.value === "unknown") {
      result.mfaa -= 1;
    }
  }

  return result;
});

const ranking = computed<RankedOption[]>(() => {
  const order: UiId[] = ["mxu", "mfaa", "maafwapp"];
  return candidates.value
    .map((item) => ({ ...item, score: scores.value[item.id] }))
    .sort((left, right) => right.score - left.score || order.indexOf(left.id) - order.indexOf(right.id));
});

const maxScore = computed(() => ranking.value[0]?.score ?? 0);
const winners = computed(() => ranking.value.filter((item) => item.score === maxScore.value));

function toggleDevice(value: Device) {
  const index = devices.value.indexOf(value);
  if (index >= 0) {
    devices.value.splice(index, 1);
  } else {
    devices.value.push(value);
  }
}

function nextStep(step: StepId | "result"): StepId | "result" {
  switch (step) {
    case "devices":
      if (!hasSupported.value) {
        return "result";
      }
      if (hasBothPlatforms.value) {
        return "platform";
      }
      return hasAndroid.value ? "shizuku" : "emulator";
    case "platform":
      return hasAndroid.value ? "shizuku" : "emulator";
    case "shizuku":
      return shizuku.value === "none" || shizuku.value === "unknown"
        ? "learnShizuku"
        : afterAndroid();
    case "learnShizuku":
      return afterAndroid();
    case "emulator":
      return "uiPref";
    case "uiPref":
      return "result";
    default:
      return "result";
  }
}

function afterAndroid(): StepId | "result" {
  return hasWindows.value ? "emulator" : "result";
}

function next() {
  history.value.push(current.value as StepId);
  current.value = nextStep(current.value);
}

function back() {
  const previous = history.value.pop();
  if (previous) {
    current.value = previous;
  }
}

function reset() {
  devices.value = [];
  platformPref.value = null;
  shizuku.value = null;
  learnShizuku.value = null;
  emulator.value = null;
  uiPref.value = null;
  history.value = [];
  current.value = "devices";
}
</script>

<style scoped>
.qs-wizard {
  margin: 1.5rem 0;
  padding: 1.25rem 1.5rem;
  border: 1px solid var(--vp-c-border, #e2e2e3);
  border-radius: 8px;
  background: var(--vp-c-bg-soft, #f6f6f7);
}

.qs-progress {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  color: var(--vp-c-text-mute, #6b7280);
}

.qs-question {
  margin: 0 0 0.9rem;
  font-size: 1rem;
  font-weight: 600;
}

.qs-options {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.qs-options--multi {
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.qs-option {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--vp-c-border, #d0d0d4);
  border-radius: 6px;
  background: var(--vp-c-bg, #fff);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s,
    background 0.2s;
}

.qs-option:hover,
.qs-option:focus-visible {
  border-color: var(--vp-c-accent, #3eaf7c);
  box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
  outline: none;
}

.qs-option.selected {
  border-color: var(--vp-c-accent, #3eaf7c);
  background: var(--vp-c-accent-bg, #e6f5ee);
}

.qs-option-title {
  font-weight: 600;
}

.qs-next {
  padding: 0.5rem 1.2rem;
  border: none;
  border-radius: 6px;
  background: var(--vp-c-accent, #3eaf7c);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.qs-next:hover:not(:disabled) {
  background: var(--vp-c-accent-hover, #44a97b);
}

.qs-next:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.qs-result .qs-reason {
  margin: 0 0 0.75rem;
}

.qs-winner {
  margin-bottom: 1rem;
}

.qs-points {
  margin: 0 0 0.75rem;
  padding-left: 1.25rem;
}

.qs-points li {
  margin: 0.25rem 0;
}

.qs-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  margin: 1.5rem 0 0;
  padding-top: 1.25rem;
  border-top: 1px solid var(--vp-c-border, #e2e2e3);
}

.qs-link-row {
  margin: 0;
}

.qs-link {
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  background: var(--vp-c-accent, #3eaf7c);
  color: #fff;
  font-weight: 600;
  text-decoration: none;
}

.qs-link:hover {
  background: var(--vp-c-accent-hover, #44a97b);
}

.qs-back {
  padding: 0.5rem 1.2rem;
  border: 1px solid var(--vp-c-border, #d0d0d4);
  border-radius: 6px;
  background: var(--vp-c-bg, #fff);
  color: var(--vp-c-text, #3c3c43);
  font: inherit;
  cursor: pointer;
  transition:
    border-color 0.2s,
    color 0.2s;
}

.qs-back:hover {
  border-color: var(--vp-c-accent, #3eaf7c);
  color: var(--vp-c-accent, #3eaf7c);
}

.qs-scores {
  width: 100%;
  margin-top: 0.5rem;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.qs-scores caption {
  padding-bottom: 0.4rem;
  color: var(--vp-c-text-mute, #6b7280);
  text-align: left;
}

.qs-scores th,
.qs-scores td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid var(--vp-c-border, #e2e2e3);
  text-align: left;
}

.qs-scores tr.winner td {
  font-weight: 600;
  color: var(--vp-c-accent, #3eaf7c);
}
</style>
