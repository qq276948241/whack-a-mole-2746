# 打地鼠 Whack-a-Mole — 架构文档

> 本文件是隔很久回来改代码时的快速上手指南。运行入口：`python whack_a_mole.py`

---

## 1. 模块与文件依赖

```
whack_a_mole.py   ← 主入口 + 游戏主循环（不包含游戏实体/UI细节）
     │
     ├── moles.py    ← 游戏实体层：地鼠、洞、浮文、分数/连击管理
     │     (无UI依赖，不直接 import scenes)
     │
     └── scenes.py   ← UI/场景层：绘制工具、音效、开始/结束场景、排行榜
           (import moles 仅用于 Mole 类型常量和颜色)
```

**依赖方向**：`whack_a_mole → scenes → moles`，单向依赖，无循环。

| 文件 | 主要责任 | 典型内容 |
|---|---|---|
| `whack_a_mole.py` | 入口调度，主循环组织 | `main()`、`game_loop()` |
| `moles.py` | 纯游戏实体，可独立测试 | `Mole`、`Hole`、`FloatingText`、`ScoreManager` |
| `scenes.py` | 所有 pygame 绘制/音效/场景 | `start_screen()`、`end_screen()`、`make_sound()`、排行榜IO |

---

## 2. 游戏状态机（场景切换）

游戏有 3 个场景，在 `whack_a_mole.py` 的 `main()` 里串成状态机：

```
              点击「开始游戏」                  60秒倒计时到0
 ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
 │ start_screen │───────▶│  game_loop   │───────▶│  end_screen  │
 └──────────────┘        └──────────────┘        └──────────────┘
        ▲                                                │
        │        点击「再来一局」返回 True                │
        └────────────────────────────────────────────────┘
                         点击「退出游戏」返回 False → pygame.quit()
```

每个场景本身是一个 `while True` 循环，在内部处理事件和绘制，直到某个用户操作触发 `return`：

| 场景 | 所在函数 | 退出条件 | 返回值 |
|---|---|---|---|
| 开始界面 | `scenes.start_screen(screen, clock, fonts)` | 点击「开始游戏」按钮 | `None` |
| 游戏中 | `whack_a_mole.game_loop(...)` | `remaining <= 0`（60秒到） | 本局分数 `int` |
| 结束界面 | `scenes.end_screen(screen, clock, fonts, score)` | 点击按钮 | `True`（再来一局）或 `False`（退出） |

状态机核心代码（[whack_a_mole.py#L100-L116](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/whack_a_mole.py#L100-L116)）：

```python
def main():
    ...  # pygame 初始化、screen/clock/fonts/sounds
    while True:
        start_screen(screen, clock, fonts)           # 场景1
        final_score = game_loop(screen, clock, ...)   # 场景2
        if not end_screen(screen, clock, ..., final_score):  # 场景3
            break
    pygame.quit()
    sys.exit()
```

每局游戏都会重新创建 `holes`、`score_mgr`，因此不存在状态残留。

---

## 3. 单只地鼠的内部状态机

每只 `Mole` 有独立的上升/停留/下降状态机，驱动 `current_height` 从 0 → max → 0：

```
             speed 帧/步                 停留 stay_time 帧           speed 帧/步
 ┌─────────┐  height += speed   ┌───────────┐  counter++   ┌───────────┐
 │ rising  │───────────────────▶│  staying  │─────────────▶│  falling  │
 └─────────┘                    └───────────┘              └───────────┘
       │                               │                           │
       │  height >= max_height        │  counter >= stay_time      │  height <= 0
       ▼                               ▼                           ▼
   state=staying                  state=falling                return False (消亡)
```

**特殊情况**：
- 被打中：跳到 `hit = True`，以 `speed * 2` 快速缩回，不进入 falling。
- 安全帽地鼠第一下：`hat_cracked = True`，状态机不打断。
- 缩回去时：如果不是被打中的（`escaped and not hit`），外部会调用 `ScoreManager.break_combo()`。

实现见 [moles.py#L144-L167](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/moles.py#L144-L167)。

---

## 4. Mole 类型体系与类图

三种地鼠**不是子类继承**，而是用 `Mole.SPECS` 配置表 + `mole_type` 字段区分，避免过度继承。如果未来需要独立行为再拆子类。

```
                    ┌───────────────────────────────────────┐
                    │                 Mole                  │
                    ├───────────────────────────────────────┤
                    │  + NORMAL / GOLDEN / HARDHAT (常量)   │
                    │  + SPECS: dict[str, Spec] (属性表)    │
                    ├───────────────────────────────────────┤
                    │  - mole_type: str                     │
                    │  - body_c / outline_c / ...           │
                    │  - current_height, state, hit, speed  │
                    │  - hits_remaining (安全帽=2, 其他=1)  │
                    │  - stay_counter, stay_time            │
                    │  - hat_cracked (仅安全帽)             │
                    ├───────────────────────────────────────┤
                    │  + apply_difficulty(progress)         │
                    │  + body_color() / outline_color()     │
                    │  + base_score()                       │
                    │  + draw(screen, cx, gy)               │
                    │  + update() -> bool (是否存活)        │
                    │  + check_hit(x, y, cx, gy)            │
                    │  │     -> (hit, fully_killed, dink)   │
                    └───────────────────────────────────────┘
                         │          │          │
                         ▼          ▼          ▼
                   ┌────────┐ ┌────────┐ ┌──────────┐
                   │ NORMAL │ │ GOLDEN │ │ HARDHAT  │
                   ├────────┤ ├────────┤ ├──────────┤
                   │ hits:1 │ │ hits:1 │ │ hits:2   │
                   │ score:10│ │ score:50│ │ score:20 │
                   │ stay:0 │ │ stay:-8│ │ stay:+20 │
                   │ rise:0 │ │ rise:+1│ │ rise:-1  │
                   └────────┘ └────────┘ └──────────┘
                      (SPECS 表配置)
```

**SPECS 字段含义**（[moles.py#L49-L74](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/moles.py#L49-L74)）：

| 字段 | 说明 |
|---|---|
| `hits` | 敲几下才死（1 或 2） |
| `score` | 基础分（连击倍率乘这个） |
| `body` / `outline` | 绘制颜色 |
| `stay_adj` | 停留时间偏移（帧），安全帽+20 给足时间敲第二下 |
| `rise_adj` | 上升速度偏移，金色+1 更难打到 |

---

## 5. 难度曲线（随时间变化的计算）

游戏总时长 60 秒，`progress = min(elapsed / 60, 1.0)` ∈ [0, 1]。难度曲线是**线性递增**。

### 5.1 地鼠出现间隔

```
spawn_interval = 60 - 35 * progress   (帧)
```

| 时间 | progress | spawn_interval | 每秒约出现几只 |
|---|---|---|---|
| 0s | 0.0 | 60 帧 | 1.0/秒 |
| 30s | 0.5 | ~42 帧 | ~1.4/秒 |
| 60s | 1.0 | 25 帧 | 2.4/秒 |

实现见 [whack_a_mole.py#L39-L41](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/whack_a_mole.py#L39-L41)。

### 5.2 单只地鼠的速度和停留时间

通过 `Mole.apply_difficulty(progress)`（[moles.py#L96-L100](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/moles.py#L96-L100)）：

```
speed     = max(1, 2 + int(3 * progress) + rise_adj)
stay_time = max(10, 35 - int(20 * progress) + stay_adj)
```

以普通地鼠为例：

| 时间 | speed (帧/步) | stay_time (帧) | 完全露头+停留总时长 ≈ |
|---|---|---|---|
| 0s | 2 | 35 | 上升 35 帧 + 停留 35 帧 ≈ 1.17 秒 |
| 30s | 3 | 25 | 上升 24 帧 + 停留 25 帧 ≈ 0.82 秒 |
| 60s | 5 | 15 | 上升 14 帧 + 停留 15 帧 ≈ 0.48 秒 |

安全帽地鼠因为 `stay_adj=+20`，在任何时刻都比普通地鼠多停留 20 帧以上，保证玩家能敲两下。

### 5.3 类型概率

| 类型 | 概率 |
|---|---|
| NORMAL | 75% |
| GOLDEN | 10% |
| HARDHAT | 15% |

实现见 [moles.py#random_mole_type](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/moles.py#L230-L236)。

---

## 6. 分数与连击系统

`ScoreManager` 封装了所有分数逻辑，内部持有：

```
ScoreManager
├── score: int              总得分
├── combo: int              当前连击数（0/1 都视为无连击）
└── floating_texts: list    正在飘动的 +XX 文字特效
```

### 6.1 得分公式

```
earned = mole.base_score() * combo
```

| 情况 | combo | 普通地鼠 | 金色地鼠 | 安全帽地鼠 |
|---|---|---|---|---|
| 第1只打中 | 1 | +10 | +50 | +20 |
| 连续第2只 | 2 | +20 | +100 | +40 |
| 连续第5只 | 5 | +50 | +250 | +100 |
| 连续第10只 | 10 | +100 | +500 | +200 |

### 6.2 连击中断条件（任一触发 combo=0）

1. **点空了**：鼠标点击但没打到任何地鼠
2. **地鼠逃了**：地鼠自己缩回洞里但不是被打中的
3. **新一局开始**：`ScoreManager.reset()` 显式清零

### 6.3 HUD 显示

- 左上角：分数 + 倒计时（≤10秒变红色）
- 右上角：连击数（≥2 显示，≥5 橙色"连击 x5!"，≥10 金色大字"超级连击 x10!!" + 倍率小字）

实现见 [ScoreManager.draw_hud](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/moles.py#L290-L316)。

---

## 7. 音效系统

全部 beep 用 `math.sin` + `array.array('h')` 在运行时生成 16-bit PCM，不依赖外部音频文件（[scenes.py#make_sound](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/scenes.py#L23-L42)）。

| 事件 | 生成方式 | 频率/特点 |
|---|---|---|
| 普通地鼠打中 | `make_combo_sound(combo)` | 400 + combo×80 Hz，连击越高越尖锐 |
| 金色地鼠打中 | `make_golden_sound()` | C6+E6+G6 三和弦叠加（1047/1319/1568 Hz） |
| 安全帽第一下 | SOUNDS["hardhat_dink"] | 300 Hz 短促 |
| 安全帽击破 | SOUNDS["hardhat_break"] | 200 Hz 低沉稍长 |
| 连击断（点空） | SOUNDS["miss"] | 150 Hz 低沉 buzz |

初始化在 `scenes.init_sounds()`，返回的字典传给 `game_loop` 统一播放。

---

## 8. 数据持久化

排行榜保存在脚本同目录下的 `highscores.json`（路径定义见 [scenes.py#L15](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo26/project26/scenes.py#L15)），格式：

```json
[
  {"score": 1230, "date": "2026-06-23 15:30"},
  {"score":  980, "date": "2026-06-22 20:11"}
]
```

只保留前 5 名，结束界面展示时若分数正好是第一名会加 `★` 并用金色字。

---

## 9. 常见改动位置速查

| 想改什么 | 去哪里 |
|---|---|
| 地鼠血量/分数/颜色/出现时长 | `moles.py → Mole.SPECS` |
| 三种地鼠的出现概率 | `moles.py → random_mole_type()` |
| 难度曲线（60秒内怎么变快） | `whack_a_mole.py → game_loop` 中的 spawn_interval；`Mole.apply_difficulty` |
| 游戏总时长 | `scenes.py → GAME_DURATION` 常量 |
| 连击得分倍率 | `moles.py → ScoreManager.register_hit` 的 `earned = base * combo` 行 |
| 新增地鼠类型 | 在 `Mole.SPECS` 加一项，在 `random_mole_type()` 调概率，在 `Mole.draw()` 加绘制分支 |
| 开始/结束界面布局 | `scenes.py → start_screen()` / `end_screen()` |
| 排行榜保留名额 | `scenes.py → save_high_score()` 里的 `scores = scores[:5]` |
| 音量 | `scenes.py → make_sound(..., volume=0.25)` 及各具体 make_* 函数的 volume 参数 |
