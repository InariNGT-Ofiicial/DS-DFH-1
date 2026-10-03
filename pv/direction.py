"""Direction table: every shot, the grammar it uses, the elements it stages, and the cut into it.

Same contract as the reference PV's direction.py:
  - a shot declares (grammar, [elements], params). It never says how anything is drawn.
  - a transition is a rule; where there is a reason, the reason is in the comment.
  - hard cuts (None) are kept for the places the music asks for them.

Shot boundaries sit on the vocal onsets, which a human timed, not on the beat grid alone.
"""
from __future__ import annotations

import facts as F
import pvclock as ck

# ---------------------------------------------------------------- reusable copy

CHECK_LOG = [
    "$ boot --mission 651",
    "[  OK  ] 站钟同步  station clock synced          +0.000 s",
    "[  OK  ] 电源母线  bus 27.3 V  (银锌电池 silver-zinc)",
    "[  OK  ] 自旋稳定  spin 120 r/min  (自旋姿态稳定)",
    "[  OK  ] 短波发射机  shortwave 20.009 MHz  ready",
    "[  OK  ] 乐音装置  音源振荡器  audio oscillator ready",
    "[ WAIT ] 星箭对接  awaiting separation  T-00:00",
]

P581 = [
    "$ 581 --init",
    "1958-05  我们也要搞人造卫星",
    "1958-08  代号 581  组长 钱学森",
    "1959-01  卫星明后年不放，与国力不相称",
    "1960-02  T-7M  8 km",
]
P651 = [
    "$ 651 --plan",
    "1965-01  两份建议同月落到同一张桌上",
    "1965-10  友谊宾馆  42 天论证会",
    "1966-01  651 设计院成立",
    "1966-05  701 工程处  地面观测系统",
]
PCAST = [
    "$ cast --standup",
    "1968-02  空间技术研究院成立  院长 钱学森",
    "1968-xx  18 位年轻人  航天十八勇士",
    "1969-09  长征一号三级试车通过",
    "1969-09  第一颗正样星通过环境模拟",
]
PTRAIN = [
    "$ train --to jiuquan",
    "1970-04-01  专列抵达酒泉",
    "1970-04-09  星箭对接完成",
    "1970-04-23  总理来电：24 日或 25 日",
    "1970-04-24  15:30  主席批准",
    "1970-04-24  21:35  点火",
]

AFTER_LOG = [
    "1971  实践一号          sience-1",
    "1975  返回式卫星        recoverable",
    "1984  东方红二号        geostationary",
    "1988  风云一号          weather",
    "2000  北斗              navigation",
    "2003  神舟五号          crewed",
    "2007  嫦娥一号          lunar",
    "2020  天问一号          mars",
    "2022  天宫              station",
]

# ---------------------------------------------------------------- the same history, drawn
# Every line of the programme log now carries the shape of its event, and the roster of later
# missions carries the shape of its machine. These are block pictograms (see icons.py), not
# photographs: a head and shoulders is a person, a table with people at it is a meeting.

P581_STORY = [
    ("$ 581 --init", None),
    ("1958-05  我们也要搞人造卫星", "slogan"),
    ("1958-08  代号 581  组长 钱学森", "speaker"),
    ("1959-01  卫星明后年不放，与国力不相称", "pause"),
    ("1960-02  T-7M  8 km", "t7m"),
]
P651_STORY = [
    ("$ 651 --plan", None),
    ("1965-01  两份建议同月落到同一张桌上", "desk"),
    ("1965-10  友谊宾馆  42 天论证会", "meeting"),
    ("1966-01  651 设计院成立", "building"),
    ("1966-05  701 工程处  地面观测系统", "dish"),
]
PCAST_STORY = [
    ("$ cast --standup", None),
    ("1968-02  空间技术研究院成立  院长 钱学森", "rostrum"),
    ("1968-xx  18 位年轻人  航天十八勇士", "team"),
    ("1969-09  长征一号三级试车通过", "teststand"),
    ("1969-09  第一颗正样星通过环境模拟", "sphere"),
]
PTRAIN_STORY = [
    ("$ train --to jiuquan", None),
    ("1970-04-01  专列抵达酒泉", "train"),
    ("1970-04-09  星箭对接完成", "dock"),
    ("1970-04-23  总理来电：24 日或 25 日", "phone"),
    ("1970-04-24  15:30  主席批准", "approve"),
    ("1970-04-24  21:35  点火", "liftoff"),
]


def after_items(rows):
    """F.AFTER rows with their block icon attached, for craftlist / ladder."""
    return [(y, n, note, F.AFTER_ICON.get(n, "sphere")) for y, n, note in rows]


# ---------------------------------------------------------------- her own record
# The song asks three rhetorical questions -- 雾霭萦绕的人生 要如何度过 at 42.3, 蜉蝣一般的人生 要如何
# 度过 at 183.0, 你被定格的人生 要如何解说 at 276.2 -- and answers none of them.
#
# The film does not answer them either. Anything the film wrote here would be the film's opinion, and
# the questions are not about the film. What answers is 东方红一号's own record, the same facts the
# rest of the picture is built on (see facts.py), set out in three spans: what carried her up, what
# she sang and for how long, and what has been true of her since the transmitter went quiet.
#
# Each span runs over a couplet of the lyric -- the question line and the 要如何度过 that closes it --
# and both shots read the same rows on the same clock, so the record does not restart between them.

HER_ASCENT = [
    ("1970-04-24 21:35", "点火   酒泉卫星发射中心", "liftoff"),
    ("运载", "长征一号  三级  29.46 m   81.5 t", "ascent"),
    ("入轨", "近地点 439 km   远地点 2384 km   倾角 68.5 度", "orbit1"),
]
HER_SONG = [
    ("1970-04-24", "短波发射机 20.009 MHz 开始播送《东方红》", "radio"),
    ("每 114 分钟", "绕地球一周   一天约十二圈半", "loop"),
    ("1970-05-14", "电池耗尽   乐音停止   实际工作 28 天", "silent"),
]
HER_AFTER = [
    ("1970 — 2009", "三十九年   地面再未听到她", "silent"),
    ("2009", "重新测轨   近地点 430 km   远地点 2075 km", "retrack"),
    ("2026", "第五十六年   仍在轨道上运行", "still56"),
]


def programme_items():
    """F.PROGRAMME rows with their block icon attached."""
    return [(d, n, note, F.PROGRAMME_ICON[i] if i < len(F.PROGRAMME_ICON) else "sphere")
            for i, (d, n, note) in enumerate(F.PROGRAMME)]

# ---------------------------------------------------------------- the shots

SHOTS: list[dict] = [
    dict(name="shot_pre", start=0.000, end=1.360, mode="raw",
         els=[("log", dict(lines=CHECK_LOG, speed=26.0))],
         her=dict(deploy=0.0, cjk=False)),

    # 01 ASSEMBLY -------------------------------------------------------
    dict(name="shot_fuel", start=1.360, end=4.820, mode="split",
         els=[("rocket", dict(ignited=0.0))], her=dict(deploy=0.0, volt=24.0, temp=-6.0)),
    dict(name="shot_tune", start=4.820, end=8.150, mode="split",
         els=[("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5], lit=1.0))],
         her=dict(deploy=0.15, tune=0.9)),
    # 8.15-11.48  "从这荒原中升起吧": she leaves the gantry, and under her the arithmetic of why
    # she can. 104 t of thrust against 81.5 t of rocket -- T/W = 1.276, and that is the whole
    # reason a 29.46 m stack gets off the pad at all.  [推论]  Typed, not captioned.
    dict(name="shot_ascent", start=8.150, end=11.480, mode="split",
         els=[("beam", dict(layers=["80 km", "50 km", "20 km"], dy=-60)),
              ("rocket", dict(ignited=1.0, lift="auto", climb=0.32), (418, 66, 1150, 306)),
              ("formula", dict(lines=F.DERIV_THRUST), (418, 320, 1150, 590))],
         her=dict(deploy=0.2, temp=41.0)),
    # 11.48-14.72  the orbit *derived* rather than drawn: T = 2*pi*sqrt(a^3/mu) and the vis-viva
    # speed, both from her own 439/2384 km.  [推论] -- the inputs are hers, the arithmetic is ours.
    # Typed line by line, like the reference film's algebra shot: the viewer watches it be worked
    # out instead of reading a caption that was always there.
    dict(name="shot_orbit_period", start=11.480, end=14.720, mode="split",
         els=[("orbit", dict(), (418, 70, 1150, 322)),
              ("formula", dict(lines=F.DERIV_ORBIT), (418, 336, 1150, 590))],
         her=dict(deploy=0.9)),
    dict(name="shot_twin_clock", start=14.720, end=18.000, mode="full",
         els=[("timeline", dict(left="1970", right="今天",
                                marks=[(0.08, "1958"), (0.22, "1965"), (0.36, "1970.04.24"),
                                       (0.52, "1970.05.14"), (0.74, "2009"), (0.92, "2026")],
                                now=0.92))],
         her=dict(deploy=1.0)),
    dict(name="shot_relay", start=18.000, end=21.310, mode="split",
         els=[("beam", dict(layers=["电离层 F", "电离层 E", "对流层", "地面站"], packets=7))],
         her=dict(deploy=1.0, tune=0.8)),
    dict(name="shot_call", start=21.310, end=24.590, mode="split",
         els=[("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5]))], her=dict(deploy=1.0)),
    dict(name="shot_silence", start=24.590, end=29.180, mode="full",
         els=[("stars", dict(n=70, seed=5))], her=dict(deploy=1.0, lit=0.5, volt=25.1)),

    # 02 FIRST LIGHT ----------------------------------------------------
    dict(name="shot_grain", start=29.180, end=32.720, mode="split",
         els=[("grid", dict(cols=18, rows=11, seed=9))], her=dict(deploy=0.0, zoom=0.8)),
    dict(name="shot_try", start=32.720, end=35.740, mode="split",
         els=[("spectrum", dict(label="CARRIER PROBE  ·  第一声"))], her=dict(deploy=0.4, tune=0.5)),
    dict(name="shot_newborn", start=35.740, end=39.850, mode="split",
         els=[("stars", dict(n=210, seed=13))], her=dict(deploy=0.55, temp=9.0)),
    dict(name="shot_alone", start=39.850, end=42.320, mode="full",
         els=[("stars", dict(n=150, seed=17)),
              ("orbit", dict(), (430, 90, 1150, 600))], her=dict(deploy=0.7)),
    # 02 the questions, i: 雾霭萦绕的人生 要如何度过 ----------------------
    # The couplet gets her record rather than a diagram. The first half asks the question across her
    # own ascent log; the second half is staged full-width and adds her portrait for the live line,
    # so the answer is the half of the question that gets the room and the drawing.
    dict(name="shot_haze", start=42.320, end=45.840, mode="split",
         els=[("answer", dict(question="雾霭萦绕的人生  /  要如何度过", rows=HER_ASCENT))],
         her=dict(deploy=0.75, temp=18.0)),
    # 45.84-49.11  the answer to 雾霭萦绕的人生, with her ascent drawn as a chart and not as a
    # pictogram: q(t) rising to max-Q.  [假定] -- the trajectory is ours, and the note says so.
    dict(name="shot_drift", start=45.840, end=49.110, mode="full",
         els=[("answer", dict(question="要如何度过", rows=HER_ASCENT, picture=True, chart="q",
                              chart_title="q(t)",
                              chart_note="assumed trajectory  ·  C_D 0.30  ·  Isp 260 s"))],
         her=dict(deploy=0.8)),
    dict(name="shot_letgo", start=49.110, end=50.800, mode="split",
         els=[("rocket", dict(ignited=0.0))], her=dict(deploy=0.9)),
    dict(name="shot_dawn", start=50.800, end=58.620, mode="bleed",
         els=[("bloom", dict(n=28, k=0.8)), ("bigtext", dict(text="", size=10, alpha=0.0))],
         her=dict(deploy=1.0, temp=22.0)),

    # 03 UPLINK ---------------------------------------------------------
    dict(name="shot_bus", start=58.620, end=62.110, mode="split",
         els=[("gauge", dict(label="BUS", value="27.3", unit=" V", frac=0.62), (420, 110, 1140, 132)),
              ("gauge", dict(label="SOLAR / CHEM", value="silver-zinc", unit="", frac=0.9), (420, 168, 1140, 190)),
              ("gauge", dict(label="TUNE OUT", value="20.009", unit=" MHz", frac=0.78), (420, 226, 1140, 248)),
              ("table", dict(title="POWER", rows=[("cell", "银锌 battery"), ("design", "20 d"),
                                                  ("bus", "27.3 V")]), (420, 300, 1140, 470))],
         her=dict(deploy=1.0, volt=27.3)),
    dict(name="shot_lock", start=62.110, end=65.430, mode="split",
         els=[("spectrum", dict(label="LOCKED  20.009 MHz"))], her=dict(deploy=1.0, tune=1.0)),
    dict(name="shot_eye", start=65.430, end=68.730, mode="split",
         els=[("earth", dict(station=True))], her=dict(deploy=1.0)),
    dict(name="shot_watch", start=68.730, end=71.920, mode="twin",
         els=[("earth", dict(r=0.34)), ("orbit", dict())], her=dict(deploy=1.0)),
    dict(name="shot_warmth", start=71.920, end=75.250, mode="split",
         els=[("table", dict(title="THERMAL", rows=[("skin", "14.0 C"), ("treated", "aluminium alloy"),
                                                    ("mirror", "temperature control")]), (420, 120, 1140, 350)),
              ("gauge", dict(label="SKIN TEMP", value="14.0", unit=" C", frac=0.44), (420, 400, 1140, 422))],
         her=dict(deploy=1.0, temp=14.0)),
    dict(name="shot_heart", start=75.250, end=78.530, mode="split",
         els=[("grid", dict(cols=9, rows=9, seed=21)),
              ("bloom", dict(k=0.5), (404, 56, 1164, 604))], her=dict(deploy=1.0, volt=27.3)),
    # 从这荒原中 升起吧: the vehicle actually leaves the gantry here, which is the one place in the
    # film where the tower should be seen standing on its own afterwards
    dict(name="shot_desert", start=78.530, end=81.850, mode="split",
         els=[("rocket", dict(ignited="auto", lift="auto", pad=True))], her=dict(deploy=1.0)),
    dict(name="shot_sunburst", start=81.850, end=86.510, mode="bleed",
         els=[("bloom", dict(n=40, k=1.0))], her=dict(deploy=1.0, temp=30.0)),

    # 04 IGNITION -------------------------------------------------------
    dict(name="shot_leap", start=86.510, end=93.040, mode="split",
         els=[("stars", dict(n=190, seed=23)),
              ("orbit", dict(), (430, 120, 1150, 580))], her=dict(deploy=1.0)),
    dict(name="shot_skirt", start=93.040, end=99.480, mode="split",
         els=[("skirt", dict())], her=dict(deploy=1.0, lit=0.75)),
    dict(name="shot_brief", start=99.480, end=103.050, mode="split",
         els=[("table", dict(title="MISSION CLOCK", rows=[
             ("launch", f"{F.LAUNCH_DATE} {F.LAUNCH_TIME}"),
             ("design life", f"{F.LIFE_DESIGN_D} d"),
             ("actual", f"{F.LIFE_ACTUAL_D} d"),
             ("silent", F.SILENT_DATE)]), (420, 120, 1140, 560))],
         her=dict(deploy=1.0, lit=0.85)),
    dict(name="shot_sing", start=103.050, end=106.380, mode="split",
         els=[("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5], progress=1.0))], her=dict(deploy=1.0, tune=1.0)),
    dict(name="shot_synth", start=106.380, end=109.660, mode="split",
         els=[("spectrum", dict(label="OSC  音源振荡器"), (404, 56, 1164, 400)),
              ("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5]), (404, 410, 1164, 600))],
         her=dict(deploy=1.0, tune=1.0)),
    dict(name="shot_celebrate", start=109.660, end=114.660, mode="bleed",
         els=[("banner", dict(text="1970 04 24", h=0.5)),
              ("bigtext", dict(text="东 方 红 一 号", size=54, y=470, color=None))],
         her=dict(deploy=1.0, lit=1.0)),

    # 05 the programme (instrumental A) ---------------------------------
    # Every line carries the picture of its own event, and the right-hand pane holds that picture
    # big enough to recognise: this passage is history with illustrations, not a text dump. Both
    # panes read the same clock (el_storylines / el_scene share `_dwell`), so a line and the
    # drawing that belongs to it change on the same frame.
    # The 581 frame keeps the log + picture: the material is a terminal's own history, and 钱学森
    # -- the subject of the frame -- is drawn large beside it.
    dict(name="shot_p581", start=114.660, end=128.000, mode="full",
         els=[("storylines", dict(lines=P581_STORY, step=46, cell=3), (24, 56, 656, 604)),
              ("scene", dict(lines=P581_STORY, title="581 / 我们也要搞人造卫星"),
               (676, 56, 1164, 604))],
         her=dict(deploy=0.0, cjk=False, zoom=0.75)),
    dict(name="shot_p651", start=128.000, end=142.000, mode="twin",
         els=[("storylines", dict(lines=P651_STORY, step=54, cell=3)),
              ("scene", dict(lines=P651_STORY, title="651 / 42 天论证会"))],
         her=dict(deploy=0.1, zoom=0.8)),
    dict(name="shot_pcast", start=142.000, end=156.000, mode="full",
         els=[("ladder", dict(items=programme_items(), cell=2, icons=True), (24, 56, 700, 604)),
              ("scene", dict(lines=PCAST_STORY, title="CAST / 1968 - 1969"), (720, 56, 1164, 604))],
         her=dict(deploy=0.2, zoom=0.7)),
    # she stays deployed behind the log here: the run-in to the launch is the one place the
    # programme itself should be watching, not just described
    dict(name="shot_ptrain", start=156.000, end=170.010, mode="split",
         els=[("storylines", dict(lines=PTRAIN_STORY, step=44, cell=3), (404, 56, 812, 604)),
              ("scene", dict(lines=PTRAIN_STORY, title="702 / 经酒泉"), (832, 56, 1164, 604))],
         her=dict(deploy=0.3, cjk=False, zoom=0.85)),

    # 06 BROADCAST ------------------------------------------------------
    dict(name="shot_dfh1", start=170.010, end=173.530, mode="bleed",
         els=[("bigtext", dict(text="东方红  太阳升", size=76, y=300)),
              ("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5], progress=1.0), (240, 430, 1040, 600))],
         her=dict(deploy=1.0, lit=1.0)),
    dict(name="shot_proud", start=173.530, end=176.410, mode="split",
         els=[("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5]))], her=dict(deploy=1.0, tune=1.0)),
    # 176.41-179.39  the layer that is not there. The beam still draws the ionosphere; under it the
    # arithmetic that answers "why is she still up": at 439 km rho is 1.6e-13 kg/m^3.  [假定] H=60.
    dict(name="shot_ionosphere", start=176.410, end=179.390, mode="split",
         els=[("beam", dict(layers=["电离层 F2", "电离层 E", "D 层", "地面"], packets=9),
               (418, 70, 1150, 314)),
              ("formula", dict(lines=F.DERIV_RHO), (418, 328, 1150, 590))],
         her=dict(deploy=1.0)),
    dict(name="shot_global", start=179.390, end=183.000, mode="split",
         els=[("earth", dict(r=0.40, station=True)),
              ("beam", dict(packets=11), (404, 420, 1164, 560))], her=dict(deploy=1.0)),
    # 06 the questions, ii: 蜉蝣一般的人生 要如何度过 ---------------------
    # Same form as the first pair, different span of the same record: not what she was, but what she
    # actually did with the time -- the tone, the turns, and the day the battery finished.
    dict(name="shot_ephemeral", start=183.000, end=186.440, mode="split",
         els=[("answer", dict(question="蜉蝣一般的人生  /  要如何度过", rows=HER_SONG))],
         her=dict(deploy=1.0, lit=0.8)),
    dict(name="shot_how", start=186.440, end=189.860, mode="full",
         els=[("answer", dict(question="要如何度过", rows=HER_SONG, picture=True))],
         her=dict(deploy=1.0)),
    dict(name="shot_declaration", start=189.860, end=193.110, mode="full",
         els=[("bigtext", dict(text="上得去  抓得住  看得到  听得见", size=44, y=300)),
              ("grid", dict(cols=26, rows=3, seed=31), (100, 380, 1180, 470))],
         her=dict(deploy=1.0, lit=1.0)),
    dict(name="shot_shake", start=193.110, end=197.150, mode="bleed",
         els=[("bloom", dict(n=32, k=0.7)), ("banner", dict(text="28", h=0.42))],
         her=dict(deploy=1.0)),

    # 07 what came after (instrumental B) -------------------------------
    # Fifty-two seconds, and it used to be the same roster four times over: craftlist of 3, ladder
    # of 5, craftlist of 9, ladder of 9. The counts climbed, so it *looked* like a progression, but
    # two of the four shots showed the identical finished list and only two devices were ever used.
    # That is what a viewer reads as "nothing is happening", and check_variety() could not see it:
    # its window is one cut wide, and every adjacent pair here did differ.
    #
    # The passage now asks four different questions of the same nine dates, each with its own
    # instrument, and only the first of them enumerates:
    #
    #   a1  who they were   a roster, once, filling across the whole shot
    #   a2  how fast        the same nine as a cumulative count: the area under a step curve
    #   a3  how long        one ruled span, 1970 to 2026, with her 28 working days magnified
    #   a4  where they are  the nine machines placed in the frame instead of listed
    dict(name="shot_a1", start=197.150, end=210.000, mode="split",
         els=[("craftlist", dict(items=after_items(F.AFTER), cell=3, lit=0.7, pace=0.95))],
         her=dict(deploy=1.0, lit=0.55, zoom=0.8)),
    # 210.00-223.00  a list of nine dates cannot show rate; a count can. Same nine, different
    # quantity, and it lands in the film's ink class because a step is an area of rectangles.
    dict(name="shot_a2", start=210.000, end=223.000, mode="full",
         els=[("aero", dict(kind="fleet", title="n(t)",
                           note="cumulative  ·  the nine in the roster"))],
         her=dict(deploy=1.0, lit=0.5, zoom=0.7)),
    # 223.00-236.00  the ratio the whole section is about: her twenty-eight days, and the fifty-six
    # years they sit inside. One axis, or the comparison does not exist.
    dict(name="shot_a3", start=223.000, end=236.000, mode="full",
         els=[("afterline", dict(items=after_items(F.AFTER),
                                 title="after  ·  1970 — 2026"))],
         her=dict(deploy=1.0, lit=0.5, zoom=0.8)),
    # 236.00-249.00  and finally the machines where they belong -- in the frame, not in a column,
    # which is also the right thing to cut from into her own planet
    dict(name="shot_a4", start=236.000, end=249.000, mode="split",
         els=[("fleet", dict(items=after_items(F.AFTER), cell=2, title="after  ·  in place"))],
         her=dict(deploy=1.0, lit=0.55, zoom=0.7)),
    dict(name="shot_a5", start=249.000, end=263.210, mode="split",
         els=[("earth", dict(), (404, 56, 1164, 604))], her=dict(deploy=1.0, lit=0.6)),

    # 08 still in orbit --------------------------------------------------
    dict(name="shot_dfh2", start=263.210, end=266.740, mode="bleed",
         els=[("bigtext", dict(text="东方红  太阳升", size=76, y=300)),
              ("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5], progress=1.0), (240, 430, 1040, 600))],
         her=dict(deploy=1.0, lit=1.0)),
    dict(name="shot_brightest", start=266.740, end=269.780, mode="split",
         els=[("stars", dict(n=240, seed=41)),
              ("bloom", dict(n=20, k=0.6), (404, 56, 1164, 604))], her=dict(deploy=1.0, lit=1.0)),
    dict(name="shot_still", start=269.780, end=272.730, mode="full",
         els=[("bigtext", dict(text="今天仍在轨道上", size=52, y=250)),
              ("table", dict(title="2026", rows=[("status", "still in orbit"),
                                                 ("2009 re-track", F.ORBIT_2009),
                                                 ("re-entry", "not yet")]), (300, 380, 1000, 580))],
         her=dict(deploy=1.0, lit=0.9)),
    dict(name="shot_witness", start=272.730, end=276.240, mode="full",
         els=[("ladder", dict(items=F.AFTER))], her=dict(deploy=1.0, lit=0.9, zoom=0.7)),
    # 09 the questions, iii: 你被定格的人生 要如何解说 -------------------
    # The third span is everything after 1970-05-14, and it is the record's own rebuttal: the tone
    # was what stopped, not her.
    dict(name="shot_frozen", start=276.240, end=279.770, mode="split",
         els=[("answer", dict(question="你被定格的人生  /  要如何解说", rows=HER_AFTER))],
         her=dict(deploy=1.0, lit=0.7, volt=0.0, tune=0.0)),
    # 279.77-282.98  the last answer, and the one the film's whole physics leads to: thirty-nine
    # years of decay as an area under a curve -- less than a metre a revolution.  [推论] from the
    # two recorded tracks (439/2384 and 430/2075 km); past 2009 the chart says it is extrapolated.
    dict(name="shot_noise", start=279.770, end=282.980, mode="full",
         els=[("answer", dict(question="要如何解说", rows=HER_AFTER, picture=True, chart="decay",
                              chart_title="a(t)",
                              chart_note="tracked 439/2384 → 430/2075 km  ·  derived beyond 2009"))],
         her=dict(deploy=1.0, lit=0.6)),
    dict(name="shot_echo", start=282.980, end=285.290, mode="split",
         els=[("spectrum", dict(label="20.009 MHz"))], her=dict(deploy=1.0, lit=0.8, tune=0.55)),
    dict(name="shot_echo2", start=285.290, end=291.760, mode="split",
         els=[("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5])), ("stars", dict(n=120, seed=43))],
         her=dict(deploy=1.0, lit=0.85, tune=0.7)),

    # 09 the dispatch ----------------------------------------------------
    # From here the song carries a broadcast instead of a vocal. The film carries the dispatch:
    # the 1970 新华社 bulletin, off the wire, on screen -- rather than leaving the band at rest.
    # The broadcast runs the 公报 as the page it actually appeared on: the 人声 reads a newspaper,
    # so the frame is one. 报头 / 电头 / 标题 / 正文 / 图片, set in 楷体 / 黑体 / 宋体, and the
    # picture the page would have run is the launch itself.
    dict(name="shot_dispatch", start=291.760, end=297.780, mode="full",
         els=[("paper", dict(lines=F.PAPER_BODY, masthead=F.PAPER_MASTHEAD, slug=F.PAPER_SLUG,
                             headline=F.PAPER_HEADLINE, subhead=F.PAPER_SUBHEAD, photo="liftoff",
                             caption=F.PAPER_CAPTION, body_size=18, text_frac=0.50),
               (24, 56, 1164, 604))],
         her=dict(deploy=1.0, lit=0.9, zoom=0.8)),

    # 10 sign-off --------------------------------------------------------
    dict(name="shot_signoff", start=297.780, end=310.000, mode="full",
         els=[("bloom", dict(n=24, k=0.5), (0, 0, 1280, 720)),
              ("bulletin", dict(head="东方红，太阳升", lines=F.BULLETIN_2, size=30, title="公报"),
               (56, 96, 690, 566)),
              ("wave", dict(notes=[5, 5, 6, 2, 1, 1, 6, 5], progress=1.0), (740, 180, 1200, 480))],
         her=dict(lit=1.0)),
    dict(name="shot_out", start=310.000, end=330.069, mode="raw",
         els=[("chinamap", dict(cell=2, marks=[(F.SITE_LATLON[0], F.SITE_LATLON[1], "酒泉", "red"),
                                               (F.BEIJING_LATLON[0], F.BEIJING_LATLON[1], "北京", "amb")]),
               (24, 70, 660, 604)),
              ("wire", dict(kicker=F.BULLETIN_KICKER, lines=F.BULLETIN_3, speed=1.4,
                            title="电讯  ·  仍在轨道上", slug="· 五十六年 ·"), (690, 70, 1256, 604))],
         her=dict(lit=0.4)),
]

BY_NAME = {s["name"]: s for s in SHOTS}


# ---------------------------------------------------------------- where the music asks for a cut

# 'glide' is the default: the pane layout itself moves. Everything below has a reason.
CHOREO = {
    # the log does not end, it re-forms into the vehicle on the pad
    ("shot_pre", "shot_fuel"): dict(kind="reflow", frames=12),
    # under the tune, the oscillator that will sing it
    ("shot_tune", "shot_ascent"): dict(kind="zoom", frames=12, a=(560, 300, 1000, 560), b="screen"),
    # the ascent curve closes into the orbit
    ("shot_ascent", "shot_orbit_period"): dict(kind="reflow", frames=12),
    # half a century: the wire between the two decades draws itself
    ("shot_twin_clock", "shot_relay"): dict(kind="pan", frames=12, dir="down"),
    # the band goes quiet
    ("shot_call", "shot_silence"): dict(kind="reflow", frames=16),
    # a grain of silver sand becomes many
    ("shot_silence", "shot_grain"): dict(kind="reflow", frames=12),
    # the noise resolves into a carrier
    ("shot_try", "shot_newborn"): dict(kind="spinfade", frames=14),
    # the stars thin out into the first line of her record
    ("shot_alone", "shot_haze"): dict(kind="reflow", frames=14),
    # the 要如何度过 of the couplet: the record stays, the frame opens out and her portrait joins it
    ("shot_haze", "shot_drift"): dict(kind="reflow", frames=12),
    # sunrise: full bleed
    ("shot_letgo", "shot_dawn"): dict(kind="crt", frames=14),
    ("shot_dawn", "shot_bus"): dict(kind="reflow", frames=12),
    # the meters drain into the locked band
    ("shot_bus", "shot_lock"): dict(kind="reflow", frames=12),
    # the antenna on the ground turns to her
    ("shot_eye", "shot_watch"): dict(kind="zoom", frames=10, a=(470, 300, 900, 560), b="screen"),
    # the grid collapses into a core
    ("shot_heart", "shot_desert"): dict(kind="inward", frames=12, seed=(784, 330)),
    # sunburst bleeds into the leap
    ("shot_sunburst", "shot_leap"): dict(kind="reflow", frames=14),
    # the skirt unfolds
    ("shot_skirt", "shot_brief"): dict(kind="reflow", frames=12),
    # 1970-04-24: hard cut, the year arrives on the downbeat
    ("shot_synth", "shot_celebrate"): None,
    # into the programme, backwards in time
    ("shot_celebrate", "shot_p581"): dict(kind="crt", frames=16),
    # and forward, decade by decade
    ("shot_pcast", "shot_ptrain"): dict(kind="reflow", frames=14),
    # the broadcast: hard cut on the vocal onset
    ("shot_ptrain", "shot_dfh1"): None,
    ("shot_dfh1", "shot_proud"): dict(kind="reflow", frames=8),
    # the wave crosses the sky
    ("shot_ionosphere", "shot_global"): dict(kind="pan", frames=12, dir="down"),
    # the second couplet: same device as the first, one line further into the record
    ("shot_global", "shot_ephemeral"): dict(kind="reflow", frames=14),
    ("shot_ephemeral", "shot_how"): dict(kind="reflow", frames=12),
    # the second instrumental pulls back out to orbit
    ("shot_shake", "shot_a1"): dict(kind="crt", frames=16),
    # the second broadcast: hard cut again, as the first
    ("shot_a5", "shot_dfh2"): None,
    # the third couplet, and the last thing the record has to say
    ("shot_witness", "shot_frozen"): dict(kind="reflow", frames=14),
    ("shot_frozen", "shot_noise"): dict(kind="reflow", frames=12),
    # the film ends on the dispatch, then pulls back out to the map: hard cut
    ("shot_echo2", "shot_dispatch"): None,
    # and lets the bulletin breathe out into the tune she is famous for
    ("shot_dispatch", "shot_signoff"): dict(kind="reflow", frames=18),
    # and lets the bulletin breathe out into the map of where she still is.
    # NOT 'inward': that transition only repaints the centre pane, and both of these shots draw
    # outside it, so the previous shot would stay on screen for the rest of the film.
    ("shot_signoff", "shot_out"): dict(kind="reflow", frames=22),
}


def shot_at(t: float) -> dict:
    for s in SHOTS:
        if s["start"] - 1e-9 <= t < s["end"] - 1e-9:
            return s
    return SHOTS[-1]


def index_of(name: str) -> int:
    return [i for i, s in enumerate(SHOTS) if s["name"] == name][0]


def transition(a: dict, b: dict) -> dict | None:
    """The transition into shot b: a spec, or None for a hard cut."""
    key = (a["name"], b["name"])
    if key in CHOREO:
        spec = CHOREO[key]
        return dict(spec) if spec else None
    return dict(kind="reflow", frames=11)


def check_variety() -> list[str]:
    """Two consecutive shots may share a grammar only if they stage a different lead element.
    Same grammar *and* same lead element means the cut reads as nothing having happened."""
    def lead(s):
        return s["mode"], (s["els"][0][0] if s["els"] else "")

    bad = []
    for a, b in zip(SHOTS, SHOTS[1:]):
        if lead(a) == lead(b):
            bad.append(f"{a['name']} -> {b['name']}: {lead(a)}")
    return bad


def check_clock() -> list[str]:
    """Every shot boundary must land on a vocal onset, on a section edge, inside an instrumental
    passage, or inside the broadcast (where the staging is free to subdivide the tone as it likes)."""
    onsets = {round(r[0], 3) for r in ck.ROWS}
    onsets |= {round(s, 3) for s, _ in ck.SECTIONS}
    onsets |= {round(a, 3) for a, _ in ck.INSTRUMENTAL}
    onsets |= {round(b, 3) for _, b in ck.INSTRUMENTAL}
    onsets |= {round(a, 3) for a, _, _, _ in ck.SPOKEN}
    onsets |= {round(b, 3) for _, b, _, _ in ck.SPOKEN}

    def inside_inst(edge: float) -> bool:
        if any(a + 1e-6 < edge < b - 1e-6 for a, b in ck.INSTRUMENTAL):
            return True
        return any(a + 1e-6 < edge < b - 1e-6 for a, b, _, _ in ck.SPOKEN)

    bad = []
    for s in SHOTS:
        for edge in (s["start"], s["end"]):
            if any(abs(edge - o) < 0.02 for o in onsets) or inside_inst(edge):
                continue
            if edge >= ck.SONG_LEN - 0.05:      # the end of the song is always a legal edge
                continue
            bad.append(f"{s['name']} @ {edge:.3f}")
    return bad
