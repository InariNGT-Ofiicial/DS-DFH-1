"""The mission as numbers. One place to correct numbers.

Verified 2026-10-01 against primary/authoritative sources:
  - CNSA 中国国家航天局   https://www.cnsa.gov.cn/n6758968/n6758972/c10004149/content.html
  - CAST 中国空间技术研究院 https://www.cast.cn/3g/news/3721
  - 科普中国 / 中国航天科技集团专题

Where sources disagree the majority + the official parameter table wins:
  perigee/apogee: CNSA prints 441/2368 km, CAST's parameter table and most official pages print
  439/2384 km -> we use 439/2384. Inclination: 68.44 deg (CAST) vs 68.5 (rounded) -> the film shows
  68.5 deg and the eval table shows 68.44 deg, both labelled.

The lyrics are a mission dossier: '观测裙' (the 4 m reflector skirt), '定段恒久的波长'
(20.009 MHz), '伴随合成乐' (the audio oscillator built at Chongqing 289), and the end card's
1970.04.24-1970.05.14 all check out against the record.
"""

# ---- the satellite
SAT_NAME = "东方红一号 / DFH-1"
MASS_KG = 173
DIAM_M = 1.0
FACETS = 72                  # 类球形对称 72 面体
SHELL = "temperature-treated aluminium alloy"
ANTENNAS = 4                 # 鞭状超短波天线
ANT_LEN_M = 2.0              # "two metres and more"
SPIN_RPM = 120               # 自旋稳定
BATTERY = "silver-zinc (银锌)"
LIFE_DESIGN_D = 20
LIFE_ACTUAL_D = 28

# ---- the orbit
PERIGEE_KM = 439
APOGEE_KM = 2384
INCL_DEG = 68.5
INCL_DEG_EXACT = 68.44
PERIOD_MIN = 114
# 2009-02 tracking: she has come down and slowed only a little in 39 years
ORBIT_2009 = "perigee 430 km / apogee 2075 km"

# ---- the radio
FREQ_MHZ = 20.009            # 短波, the tune of 东方红
TUNE = "东方红"
AUDIO_SRC = "音源振荡器 · 中科院自动化所 刘承熙小组 · 重庆289厂"

# ---- the launch
LAUNCH_DATE = "1970-04-24"
LAUNCH_TIME = "21:35"
SITE = "酒泉卫星发射中心"
SILENT_DATE = "1970-05-14"
ROCKET = "长征一号 / CZ-1"
ROCKET_MASS_T = 81.5
ROCKET_LEN_M = 29.46
ROCKET_DIA_M = 2.25
THRUST_T = 104
STAGES = 3

# ---- why you could see her: the skirt on the spent third stage
SKIRT_DIA_M = 4.0
SKIRT_MAG = "2-3"
SAT_MAG = 7.0                # the 1 m sphere alone is only 7th magnitude
EYE_LIMIT_MAG = 6.0          # the naked-eye limit

# ---- the four goals, quoted
GOALS = ["上得去", "抓得住", "看得到", "听得见"]

# ---- the road there (programme milestones, for the long instrumental passages)
PROGRAMME = [
    ("1958-05", "581", "we should build satellites too"),
    ("1965-01", "651", "two proposals land on the same desk"),
    ("1965-10", "42d", "42 days of argument in Beijing"),
    ("1968-02", "CAST", "空间技术研究院 stands up"),
    ("1969-09", "test", "CZ-1 third stage test-fires clean"),
    ("1970-04-01", "train", "the special train reaches Jiuquan"),
]

# ---- what came after (the second instrumental passage)
AFTER = [
    ("1971", "实践一号", "practice-1"),
    ("1975", "返回式", "recoverable"),
    ("1984", "东方红二号", "geostationary"),
    ("1988", "风云一号", "weather"),
    ("2000", "北斗", "navigation"),
    ("2003", "神舟五号", "crewed"),
    ("2007", "嫦娥一号", "lunar"),
    ("2020", "天问一号", "mars"),
    ("2022", "天宫", "station"),
]

SLOGAN = "东方红，太阳升"
CARD = "东方红一号   1970.04.24 — 1970.05.14"
STILL = "still in orbit · 2026"

# ---- the map, and where things are on it
# The boundary set is a Chinese domestic one carrying a 审图号 and it includes 台湾省、香港、澳门 and
# the 南海诸岛 boundary. The number is printed on the frame, the way a published map prints it.
MAP_APPROVAL = "GS(2019)1719号"
SITE_LATLON = (100.29, 40.96)          # 酒泉卫星发射中心
BEIJING_LATLON = (116.40, 39.90)
WATCH_LATLON = (109.50, 34.50)         # 渭南 观测站, the ground station of the 651 network

# ---- the broadcast: what the newsreader is actually saying, 1970-04-25
# The passages the song leaves wordless at the end are a broadcast insert. The film puts the
# dispatch on screen instead of leaving the band at rest.
BULLETIN_KICKER = "新华社  北京一九七〇年四月二十五日电"
BULLETIN = [
    "我国第一颗人造地球卫星「东方红一号」",
    "已于四月二十四日二十一时三十五分发射成功",
    "卫星运行轨道近地点 439 公里  远地点 2384 公里",
    "轨道平面与地球赤道平面夹角 68.5 度",
    "绕地球一周 114 分钟",
    "卫星上装有短波发射机  播送《东方红》乐曲",
]
BULLETIN_2 = [
    "五月十四日  卫星电池耗尽",
    "停止发送《东方红》乐音",
    "设计寿命 20 天  实际工作 28 天",
    "至今仍在轨道上运行",
]

# ---- and the last word: she is still up there
BULLETIN_3 = [
    "电波不再  轨道仍在",
    "近地点 430 公里  远地点 2075 公里",
    "二〇〇九年  第三十九年  重新测轨",
    "五十六年  仍在轨道上运行",
]

# ---- which block icon belongs to which craft / event
AFTER_ICON = {
    "实践一号": "sj1", "返回式": "fs", "东方红二号": "dfh2", "风云一号": "fy1",
    "北斗": "bd", "神舟五号": "sz5", "嫦娥一号": "ce1", "天问一号": "tq1", "天宫": "tg",
}
PROGRAMME_ICON = ["slogan", "desk", "meeting", "building", "teststand", "train"]

# ---- the front page the 公报 ran on
# The 公报 is dated 四月二十五日; the paper that carried it is the next morning's, a Sunday. No
# 期号 is printed: we do not know it, and inventing one would be the single thing on the page that
# could be checked and found wrong. 版次 instead, which is both true and what a 报头 carries.
PAPER_MASTHEAD = "人民日报"
PAPER_DATE = "1970 年 4 月 26 日  星期日"
PAPER_SLUG = [PAPER_DATE, "第 一 版"]
PAPER_HEADLINE = "我国第一颗人造地球卫星发射成功"
PAPER_SUBHEAD = "新华社  北京四月二十五日电"
PAPER_CAPTION = "一九七〇年四月二十四日  酒泉"
# The 公报's own first sentence is the 标题 in any paper that prints it, so it is not repeated in
# the body: headline carries it, the body opens where the sentence continues.
PAPER_BODY = BULLETIN[1:]

# ================================================================= air & orbit
# Every number below is *derived*, not observed. The inputs are the records above (all verifiable);
# the formulas are the standard ones. Reviewing script: _sr/tools/aero_probe.py  (re-run it and the
# numbers below must reproduce). Three labels, and nothing may move between them:
#
#   [推论]  falls out of the record by a published formula. Not a new fact, but the *arithmetic is
#           ours* -- on screen it is marked as a derivation, never as a reading.
#   [假定]  a textbook typical value we chose. DFH-1's own ascent aerodynamics were never published,
#           so C_D and Isp are assumptions and are labelled as such wherever they appear.
#   [推定]  fitted back out of a record. It is only as good as the record; it is a consistency
#           check, not an independent measurement.
#
# The whole point of this block: "浮游一般的人生" is not a metaphor here. A/m is small, so the drag
# is 5e-9 of her weight, and that number is why she is still up there 56 years on.

MU_KM3_S2 = 398600.4418          # earth gravitational parameter
R_EARTH_KM = 6371.0

# ---- the orbit she was put in
SMA_KM = 7782.50                 # [推论] (439+2384)/2 + 6371
ECC = 0.12496                    # [推论]
PERIOD_CALC_MIN = 113.878        # [推论] 2*pi*sqrt(a^3/mu) -- the record says 114
V_PERI_KMS = 8.115               # [推论] vis-viva at perigee
V_APO_KMS = 6.312                # [推论] vis-viva at apogee

# ---- 39 years later (2009 re-track)
SMA_2009_KM = 7623.50            # [推论] (430+2075)/2 + 6371
DA_KM = 159.0                    # [推论] 7782.5 -> 7623.5
REVS_39YR = 179934               # [推论] 39 yr at 114 min  =  12.63 rev/day
DECAY_M_PER_REV = 0.884          # [推论] the line that carries the whole film
DECAY_MS_PER_REV = 1.16          # [推论] period gained per revolution
DECAY_KM_PER_YR = 4.08           # [推论]

# ---- drag: why the tone stopped but the orbit did not
AREA_M2 = 0.7854                 # [推论] pi*(d/2)^2 with d = 1 m
AM_M2_KG = 0.004540              # [推论] A/m -- the number that lets her float
CD_ASSUMED = 2.2                 # [假定] free-molecular-flow drag coefficient
RHO_EFF_KGM3 = 1.593e-13         # [推定] solved from the 2009 decay rate
DRAG_OVER_W = 5.34e-9            # [推论] drag acceleration / g at perigee
DRAG_MS2 = 5.24e-8               # [推论] drag acceleration at perigee

# ---- the ascent (8->11 s)
THRUST_KN = 1020.0               # [推论] 104 t of thrust
WEIGHT_KN = 799.5                # [推论] 81.5 t at lift-off
TWR = 1.2761                     # [推论] 1.276 > 1, which is why the gantry lets go
LIFTOFF_G = 0.276                # [推论] (T-W)/m at t = 0
MAXQ_KPA = 18.9                  # [假定] from an assumed 1-D trajectory
MAXQ_T = 66.0                    # [假定]
MAXQ_H_KM = 9.3                  # [假定]
MAXQ_MACH = 1.13                 # [假定]
T_STAG_C = 12.0                  # [假定] stagnation temperature -- she is *cold*, not hot

# ---- the derivations as they are typed on screen.  (text, point size)
# Structure copied from the reference film's ALG: the general law first, then her own numbers,
# then the line that lands. ASCII-latin lines are set in the mono face; any line with CJK in it
# switches face per line (Consolas carries every glyph here except U+2234, which we avoid).
DERIV_ORBIT = [
    ("T = 2π√( a³ / μ )", 21),
    ("  = 2π√( 7782.5³ / 398600 )", 21),
    ("  = 113.878 min", 21),
    ("", 0),
    ("v_p = √( μ · (2/r_p − 1/a) )", 21),
    ("    = 8.115 km/s", 21),
]
DERIV_DECAY = [
    ("a_d = −½ · ρ · v² · C_D · A / m", 21),
    ("    = −½ · 1.59e-13 · 8115² · 2.2 · 0.00454", 21),
    ("    = −5.24e-8 m/s²", 21),
    ("    = −5.34e-9 g", 21),
    ("", 0),
    ("da/dt = −0.884 m / rev", 27),
]
# The layer that is not there: at 439 km the air is thin enough that "why is she still up" stops
# being poetry and becomes arithmetic. Scale height 60 km is [假定].
#
# Nothing in these tables carries CJK, on purpose. Two reasons, and the second is the real one:
# the mono face already carries every glyph used here (only U+2234 is missing, so it is avoided),
# and a formula that stops to explain itself in Chinese stops reading as a formula -- it becomes a
# diagram with a caption. On screen the equation is the caption.
DERIV_RHO = [
    ("ρ(h) = ρ0 · exp( −h / H )", 21),
    ("     = 1.225 · exp( −439 / 60 )", 21),
    ("     = 1.6e-13 kg/m³", 21),
]
DERIV_THRUST = [
    ("F = 1020 kN   m0·g = 799.5 kN", 21),
    ("a0 = (F − m0·g) / m0", 21),
    ("   = 220.5 / 81.5", 21),
    ("   = 2.71 m/s²", 21),
    ("", 0),
    ("T / W = 1.276  >  1", 27),
]
