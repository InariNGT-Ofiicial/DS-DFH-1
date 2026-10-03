# FONTS：字体清单与替代方案

本片在 Windows 上制作，用的是**系统自带字体**。这些字体**不可再分发**，因此**不在本仓库里**。

所有字体路径都能用**环境变量**覆盖，所以换系统不用改代码：

| 环境变量 | 本片默认（Windows） | 用途 | 换系统时建议 |
|---|---|---|---|
| `PV_F_MONO` | `C:/Windows/Fonts/consola.ttf` | 等宽正文，界面里绝大多数文字 | 任意等宽：DejaVu Sans Mono、JetBrains Mono、Menlo |
| `PV_F_MONO_B` | `C:/Windows/Fonts/consolab.ttf` | 等宽粗体，读数与标题 | 同上，粗体字重 |
| `PV_F_HEAD` | `C:/Windows/Fonts/consolab.ttf` | 页面标题 | 见下「唯一的替代」 |
| `PV_F_BANNER` | `C:/Windows/Fonts/arialbd.ttf` | 巨型横幅（只吃拉丁） | 任何粗体无衬线 |
| `PV_F_CJK` | `C:/Windows/Fonts/msyh.ttc` | 中文正文（微软雅黑） | 思源黑体、Noto Sans CJK SC |
| `PV_F_SYM` | `C:/Windows/Fonts/seguisym.ttf` | 数学符号 `∃ ⟨ ⟩ ⊢ ∀` | DejaVu Sans（覆盖面广） |
| `PV_F_KAI` | `C:/Windows/Fonts/STKAITI.TTF` | 报纸报头（华文楷体） | 任意楷体 |
| `PV_F_HEI` | `C:/Windows/Fonts/simhei.ttf` | 报纸标题（黑体） | 任意黑体 |
| `PV_F_SONG` | `C:/Windows/Fonts/simsun.ttc` | 报纸正文（宋体） | 思源宋体、Noto Serif CJK SC |

用法：

```bash
PV_F_MONO=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf \
PV_F_CJK=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc \
python build.py all
```

`python build.py check` 会**逐个验证字体文件存在**，缺哪个就报哪个——不会跑到一半才发现字体不对。

## 唯一的替代

**`F_HEAD`（标题字体）。** 参考项目用的是 **Space Mono Bold**，它不可再分发，
所以也**没有随原仓库分发**。本片因此改用系统等宽字体（`consolab.ttf`）。
这是整支片子里**唯一不可避免的字体替代**，影响的是页面标题的观感，不影响版式与文字内容。

## 关于中日韩文字

中文**不能塞进等宽拉丁字体**——会变成一排空框（俗称「豆腐」，tofu）。
本工程在这件事上踩过坑并留了工具：

- `tuikit.needs_cjk(s)`：按码点判定要不要换 CJK 面。
  ⚠️ 它判的是 **`>0x7F`**，**不能拿它判整行**——Consolas 自带一批数学符号
  （`· ³ π μ √ − ² ρ →`），整行推到雅黑反而难看。
  整行判断要用 `scenes._cjk_line(s)`（判 `>0x2E7F`）。
- `tuikit.mixed_text()` / `script_runs()`：**按分段**选字体，两段共用一条基线。
- `tools/tofu_audit.py`：全片逐 0.5 s 渲染，**真比对字形**
  （该面 `getmask(ch)` 为空或等于它自己的 `.notdef`），把每一处豆腐记账。

> 注意 `tofu_audit` 的**判据本身**修过一次。旧判据是「等宽字面 + 非 ASCII」，
> 它会把整屏**正常的代数式**报成 14 处豆腐。判据不真，扫描就没有意义。
