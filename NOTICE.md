# NOTICE：第三方素材与许可

本仓库的**代码**按 [LICENSE](LICENSE)（MIT）发布，署名 苌萌萌。下面这些**不属于**那份许可，各自保留原来的权利。

*English: the code in this repository (the .py files written for this film) is MIT. It does not cover
the song, the lyrics, the reference project's design language, the fonts, or the map data listed
below. Each keeps its own terms.*

---

## 1. 歌曲与歌词（不在本仓库里）

| 东西 | 权利人 | 怎么获得 |
|---|---|---|
| 音频《シリウスの心臓（天狼星的心脏）Piano Ver.》 | 原曲作者 / ヰ世界情緒 | **自备**，放到 `audio/song.mp3`，或用 `PV_SONG` 指向别处 |
| 歌词文字 | 词作 / 翻填者 | **自备**，放到 `work/lines.local.json`，或用 `PV_LINES` 指向一个 .lrc |
| 翻填版《东方红一号》的填词、曲绘、映像 | 炙弹冰（协作：星辰不唏嘘 / 星与辰Stars） | 见影片本身的 credits；本仓库不再许可 |

本仓库**一个字节的歌词文本都没有**。它只带 `song.timeline.json`：每一行的起点、终点与 sha256。
`pv/pvclock.py` 在你本机把「你自己的歌词」和「仓库里的时间码」合起来，并**逐行比对 sha256**——
对不上就报错退出，不会拿一版歌词配另一版的时间。

> 这样做是有代价的：**没有 `work/lines.local.json` 时这个仓库连 `import` 都跑不过去**
> （词级时间轴在模块级就被需要）。这是刻意的取舍——干净地剥离版权内容，比开箱即跑更重要。

## 2. 设计语言与代码基础：参考项目

- **来源**：[`MisakaZentai/world-execute-me-dsh-pv`](https://github.com/MisakaZentai/world-execute-me-dsh-pv)
  （MIT code + CC BY-NC-SA 4.0 artwork，B站成片 [BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)）。
- **本片沿用了什么**：**技术路线**（帧 = 歌曲时间 t 的纯函数、固定五层合成序、分镜三表 + lint + 弧线）
  与**呈现形式**（1280×720 / 24 fps / 琥珀色荧光屏调色板 / 半块字符网格 / 扫描线 / 暗角 / 辉光）。
  `pv/tuikit.py` 是基于同一套语义的**重写**，保留了它的调色板与图元设计意图。
- **本片没有沿用**：参考项目的角色立绘（`whale-*.webp`，CC BY-NC-SA 4.0，**未随本仓库分发**）
  与其附带字体（Space Mono Bold / Anton，**未随本仓库分发**）。
  本片的主体是**程序化绘制**的东方红一号卫星，**零外部图像素材**。
- 差异与替代方案逐条记在 [docs/PORTING.md](docs/PORTING.md)。

参考项目是 MIT 代码 + CC BY-NC-SA 素材的混合授权。本片只继承其**代码侧的设计意图**，
不包含任何来自它的图像资源，因此本仓库不含 CC BY-NC-SA 内容。

## 3. 字体（不在本仓库里）

本片在 Windows 上制作，用的是系统自带字体。**这些字体不随本仓库分发**，各系统自备：

| 用途 | 本片使用 | 替代 |
|---|---|---|
| 等宽正文 | Consolas / Consolas Bold | 任意等宽字体，设 `PV_F_MONO` / `PV_F_MONO_B` |
| 标题 | Consolas Bold（参考项目的 Space Mono Bold 不可再分发） | `PV_F_HEAD` |
| 中文正文 | 微软雅黑 | `PV_F_CJK` |
| 数学符号（`∃ ⟨ ⟩ ⊢ ∀`） | Segoe UI Symbol | `PV_F_SYM` |
| 报纸头版 | 华文楷体 / 黑体 / 宋体 | `PV_F_KAI` / `PV_F_HEI` / `PV_F_SONG` |

全部字体路径都可以用环境变量覆盖，见 [docs/FONTS.md](docs/FONTS.md)。

## 4. 中国地图数据（随本仓库分发）

- **文件**：`work/map/china_full.json`
- **来源**：阿里云 DataV 地理小工具系列 `areas_v3` 全国边界，**审图号 GS(2019)1719号**。
  35 个要素，含 `710000`（台湾）/ `810000`（中国香港）/ `820000`（中国澳门）
  与 `100000_JD`（南海诸岛九段线）。
- **本片怎么用**：`pv/chinamap.py` 用 Albers 等积割圆锥投影把它画出来，
  **并把审图号印在南海诸岛插框上**——按公开出版的规范做法。
- ⚠️ **使用地图务必遵守当地法规**：任何公开传播的地图都须完整、规范地表示中国版图。
  改动边界、省略南海诸岛或台湾、香港、澳门，都可能违反《地图管理条例》。
  引用本仓库的数据不构成合规保证，发布前请自行核对。

## 5. 事实数据

`pv/facts.py` 里的航天参数来自公开资料（CNSA / CAST 参数表、科普中国、Space-Track 等），
逐条在文件内注明。**口头共识不一致处已在片中标明口径**：
英文维基给 441 / 2286 km、68.42°、114.09 min；中文官方与 CAST 参数表给 439 / 2384 km、68.5°、114 min。
本片采用**中文官方口径**，并在镜头里只上屏后一组数字。

片中的**气动数值**（max-Q、滞止温度）出自**假定弹道**（`C_D=0.30`、`Isp=260 s`），
东方红一号上升段**没有公开气动数据**；2026 年的轨道根数是按阻力**外推**，不是实测。
`pv/facts.py` 头部把这三类口径写成了 `[事实]` / `[推论]` / `[假定]` / `[推定]`，镜头里照此标注。

## 6. 声明

- 这是**非官方同人作品**，与上述各位作者、机构没有任何从属或合作关系，也未经其认可。
- 本仓库不授予歌曲、歌词、字体或任何第三方素材的再许可。使用前请自行确认各自条款。
