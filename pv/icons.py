"""Block icons: every picture in this film is made of blocks, so the pictures of the spacecraft,
the people and the events should be too.

An icon is an ASCII bitmap. The renderer turns each character into one filled square (``#`` full,
``+`` two-thirds, ``-`` a third, ``.`` a sixth, space nothing) and pastes it as an RGBA sprite, so
the icons carry the same half-block texture as the rest of the film and stay a pure function of
their arguments.

Drawing them by hand in text, rather than pulling photographs, is deliberate: these are the *shapes*
of the machines, at the resolution a terminal would give you, and nothing here is anybody's
copyrighted image.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

import tuikit as tk

# luminance of each glyph, as a fraction of full
LEVELS = {"#": 1.00, "+": 0.62, "-": 0.34, ".": 0.15, " ": 0.0, ",": 0.22}


# ---------------------------------------------------------------- the nine that came after
# Rough silhouettes only -- a body, the wings, the dish, the nozzle. That is what makes them
# recognisable at 40 px, and pretending to more detail would only turn into noise at this size.

CRAFT: dict[str, list[str]] = {
    # 1971 实践一号: a squat drum with four paddles and two pairs of whips
    "sj1": [
        "   #             #   ",
        "    ##   ##    ##    ",
        " ################### ",
        "##  ###  ##  ###   ##",
        "###  ###  ##  ###  ##",
        "##  ###  ##  ###   ##",
        " ################### ",
        "    ##   ##    ##    ",
        "   #             #   ",
    ],
    # 1975 返回式卫星: a blunt re-entry capsule with a small instrument ring behind it
    "fs": [
        "        #######      ",
        "      ##-------##    ",
        "     ##---------##   ",
        "    ##-----------##  ",
        "   ##-------------## ",
        "   ##------------### ",
        "   ##+++++++++++#### ",
        "    ###++++++++####  ",
        "      ###########    ",
        "        #######      ",
    ],
    # 1984 东方红二号: a spinning drum, two long wings, and the big dish she broadcast with
    "dfh2": [
        " ########              ",
        "##......##     /#####\\",
        "###########   /#######\\",
        " ##......##  |#########|",
        " ##########   \\#######/",
        "##......##     \\#####/ ",
        "########            ###",
        " ######             ## ",
    ],
    # 1988 风云一号: a flat box with two long scanning wings
    "fy1": [
        "                    ###",
        " ######################",
        "########################",
        "########################",
        " ######################",
        "                    ###",
        "        ########       ",
        "       ##########      ",
    ],
    # 2000 北斗: a three-axis box, two wings, and the navigation antenna facing down
    "bd": [
        " ###              ###  ",
        "######   ########   ###",
        "##########....########",
        "##########....########",
        "######   ########   ###",
        " ###              ###  ",
        "         \\..../       ",
        "          \\  /        ",
        "           \\/         ",
    ],
    # 2003 神舟五号: escape tower, orbital module, the capsule, the service module -- a stack
    "sz5": [
        "          /\\          ",
        "          ||          ",
        "          ||          ",
        "        ######        ",
        "        #....#        ",
        "        ######        ",
        "       ########       ",
        "      ##......##      ",
        "      ##########      ",
        "      ##########      ",
        "     ##........##     ",
        "     ############     ",
        "      ||      ||      ",
    ],
    # 2007 嫦娥一号: a box, two wings, and the big dish that talked to the ground
    "ce1": [
        "  ###              ###",
        "################################",
        "#####  ############  #####",
        "  ###  ############  ###",
        "        ######        ",
        "      /########\\      ",
        "     /##########\\     ",
        "      \\########/      ",
    ],
    # 2020 天问一号: orbiter wings, the lander ring, and the rover underneath
    "tq1": [
        "        ########        ",
        "########################",
        "##....................##",
        "########################",
        "     ##############     ",
        "    ##..##..##..##..##  ",
        "    ##################  ",
        "       ##      ##       ",
        "      ##############    ",
        "      #  ##  ##  #      ",
    ],
    # 2022 天宫: core module plus two labs -- the T -- and four solar arrays
    "tg": [
        " #####                            #####",
        "########################################",
        "#########   ##########   #############",
        "########################################",
        " #####                            #####",
        "                  ##                    ",
        "              ##########                ",
        "              ##########                ",
    ],
}


# ---------------------------------------------------------------- the people and the events
# Same idea, one size down. A figure is a head and shoulders; a meeting is a table with people at
# it; a train is a locomotive. Nobody is being caricatured -- they are pictograms.

STORY: dict[str, list[str]] = {
    # 1958-05 「我们也要搞人造卫星」 -- a megaphone, and the sound coming out of it
    "slogan": [
        "            ..         ",
        "          .####.       ",
        "        .#########.    ",
        "      .#############.  ",
        "      .#############.  ",
        "        .#########.    ",
        "          .####.       ",
        "            ..         ",
    ],
    # a figure at a lectern: the person who is speaking
    "speaker": [
        "        ###      ",
        "       #####     ",
        "       #####     ",
        "        ###      ",
        "     #########   ",
        "    ###########  ",
        "    ###########  ",
        "   ############# ",
    ],
    # a figure behind a lectern, with the microphones: for the one who is not just speaking
    # but chairing the thing. 1968-02 空间技术研究院成立  院长 钱学森.
    "rostrum": [
        "      ##  ##     ",
        "       ####      ",
        "       ####      ",
        "        ##       ",
        "      ######     ",
        "     ########    ",
        "  ############## ",
        "  ############## ",
        "  ############## ",
    ],
    # 1959-01 「卫星明后年不放，与国力不相称」 -- a programme put on hold
    "pause": [
        "###############",
        "##           ##",
        "##  ### ###  ##",
        "##  ### ###  ##",
        "##  ### ###  ##",
        "##  ### ###  ##",
        "##  ### ###  ##",
        "##           ##",
        "###############",
    ],
    # a rocket with a hold bar across it
    "grounded": [
        "     ######     ",
        "     ######     ",
        "     ######     ",
        "##||||||||||||||##",
        "##||||||||||||||##",
        "     ######     ",
        "     ######     ",
        "     ######     ",
    ],
    # 1960-02 T-7M 探空火箭, 8 km -- short, and a low arc
    "t7m": [
        "        /\\      ",
        "        ||      ",
        "       ####     ",
        "       ####     ",
        "       ####     ",
        "     ########   ",
        "     ########   ",
        "   -----..------",
    ],
    # 1965-01 two proposals on one desk
    "desk": [
        "  ###    ###    ",
        "  ###    ###    ",
        "   #      #     ",
        "                ",
        "################",
        "################",
        "##############  ",
        "##############  ",
    ],
    # 1965-10 友谊宾馆 42 days of argument -- a long table, many at it
    "meeting": [
        " #   #   #   #  ",
        " #   #   #   #  ",
        " #   #   #   #  ",
        "                ",
        "################",
        "###..###..###..;",
        "################",
        " %%%%  %%%%  %%%",
    ],
    # 1966-01 / 1968-02 设计院 / 研究院 stands up -- a building with a flag
    "building": [
        "         ##     ",
        "        ####    ",
        "      ########  ",
        "   #############",
        " ################",
        " ## ## ## ## ## ",
        " ################",
        " ## ## ## ## ## ",
        " ################",
    ],
    # 1968 十八勇士 -- several figures standing together
    "team": [
        " #  #  #  #  #  ",
        " #  #  #  #  #  ",
        " #  #  #  #  #  ",
        "##### ##### #####",
        "##### ##### #####",
        "##### ##### #####",
        "##### ##### #####",
        "##### ##### #####",
    ],
    # 1969-09 三级试车通过 -- a test stand firing
    "teststand": [
        "   ##########   ",
        "   ##########   ",
        "   ##      ##   ",
        "   ##      ##   ",
        "   ##      ##   ",
        "   ##  /\\  ##   ",
        "   ##  ||  ##   ",
        "   ##  ||  ##   ",
        " ###   ####   ###",
        " %%%           %%",
    ],
    # 1970-04 专列抵达酒泉 -- a locomotive on a track
    "train": [
        "      ####      ",
        " ############   ",
        "##############  ",
        "###  ###  ###   ",
        "##############  ",
        "  O          O  ",
        "=================",
        "=================",
    ],
    # 1970-04-09 星箭对接 -- the satellite being mated to the top of the rocket
    "dock": [
        "     ######     ",
        "     ######     ",
        "   ##########   ",
        "   ##########   ",
        "----------------",
        "     ####       ",
        "     ####       ",
        "    ######      ",
        "   ########     ",
        "     ####       ",
    ],
    # 1970-04-23 总理来电 -- a telephone handset
    "phone": [
        "  #############  ",
        " ############## ",
        "###          ###",
        "##            ##",
        "##            ##",
        "###          ###",
        " ############## ",
        "  ############   ",
    ],
    # 1970-04-24 主席批准 -- a document with a seal on it
    "approve": [
        " ################",
        " #..............#",
        " #..######......#",
        " #..#....#......#",
        " #..######......#",
        " #..............#",
        " #..../####\\....#",
        " #.../######\\...#",
        " #....\\####/....#",
        " ################",
    ],
    # 1970-04-24 21:35 点火 -- the vehicle lifting off
    "liftoff": [
        "      ####      ",
        "      ####      ",
        "     ######     ",
        "     ######     ",
        "     ######     ",
        "    ########    ",
        "   ##########   ",
        "  ####    ####  ",
        " %%%%      %%%% ",
        "%%%%%%%%%%%%%%%%",
    ],
    # the ground station that listened
    "dish": [
        "     /######\\   ",
        "    /########\\  ",
        "   /##########\\ ",
        "    \\########/  ",
        "      \\####/    ",
        "       ####     ",
        "       ####     ",
        "      ######    ",
        "     ########   ",
    ],
    # her, the one the whole film is about: the 72-faced sphere on its whips
    "sphere": [
        "     ######     ",
        "   ##########   ",
        "  ############  ",
        " ############## ",
        " ############## ",
        "  ############  ",
        "   ##########   ",
        "     ######     ",
        "  #          #  ",
        " #            # ",
    ],
    # ---- her own record (see bigscene.py). Same seven events the record panel lists, small: what
    # carried her up, where she ended up, what she sent down, how often she went round, the day the
    # battery finished, the day the ground found her again, and today.
    "ascent": [
        "       #       ",
        "      ###      ",
        "      ###      ",
        "      ###      ",
        "      ###      ",
        "     #####     ",
        "  ...........  ",
        "   .........   ",
    ],
    "orbit1": [
        "  ..........   ",
        "     #####     ",
        "   #########   ",
        "   #########   ",
        "     #####     ",
        "  #    #    #  ",
        "  -----------  ",
        "   ---------   ",
    ],
    "radio": [
        "     #####     ",
        "   #########   ",
        "   #########   ",
        "     #####     ",
        "    -     -    ",
        "   -       -   ",
        "  -         -  ",
        "  -----------  ",
    ],
    "loop": [
        "   ---------   ",
        " --         -- ",
        " -  ##       - ",
        " -           - ",
        " -        ## - ",
        " --         -- ",
        "   ---------   ",
        "               ",
    ],
    "silent": [
        "  #            ",
        "  ###          ",
        "  #  ###       ",
        "  #     ###    ",
        "  #        ### ",
        "  #############",
        " ##############",
        "               ",
    ],
    "retrack": [
        "          ###  ",
        "       ###     ",
        "    ####       ",
        "  ####         ",
        "  /####\\       ",
        "  \\####/       ",
        "  ######       ",
        "               ",
    ],
    "still56": [
        "  -----------  ",
        " -           - ",
        " .          ##-",
        " -         ####",
        " -          ##-",
        " -           - ",
        "  -----------  ",
        "               ",
    ],
}


# ---------------------------------------------------------------- her own parts
# The right-hand column sections the satellite, so it needs the parts themselves, not the missions.
# Six of them, one per subsystem the film's story actually turns on: what she was made of, what
# powered her, what she spoke with, what she sang with, and the thing that made her visible.

PARTS: dict[str, list[str]] = {
    # 天线 ×4 -- four whip antennae, two metres and more, on the sphere
    "p_ant": [
        " #             # ",
        "  #           #  ",
        "   #         #   ",
        "    #       #    ",
        "     #######     ",
        "    #########    ",
        "   ###  #  ###   ",
        "   ###  #  ###   ",
        "    #########    ",
        "     #######     ",
        "    #       #    ",
        "   #         #   ",
        "  #           #  ",
    ],
    # 壳体 -- the 72-facet shell, one metre across, temperature-treated aluminium
    "p_shell": [
        "     #####     ",
        "   #########   ",
        "  ###########  ",
        " ####-#-#-#-## ",
        " ############# ",
        " ###-#-#-#-#-# ",
        " ############# ",
        " ##-#-#-#-#-## ",
        "  ###########  ",
        "   #########   ",
        "     #####     ",
    ],
    # 银锌电池 -- silver-zinc cells, 27.3 V on the bus
    "p_batt": [
        "    +       -   ",
        "    #       #   ",
        " ############## ",
        " #============# ",
        " # ||| ||| ||| #",
        " # ||| ||| ||| #",
        " # ||| ||| ||| #",
        " #============# ",
        " ############## ",
        "   ##########   ",
    ],
    # 短波发射机 -- 20.009 MHz, the band the whole film is tuned to
    "p_tx": [
        "        #       ",
        "        #       ",
        " ############## ",
        " #            # ",
        " #  ~###~     # ",
        " # ~     ~    # ",
        " #~       ~   # ",
        " #            # ",
        " #   ######   # ",
        " ############## ",
        "   ###    ###   ",
    ],
    # 乐音装置 -- the audio oscillator built at Chongqing 289, which is what actually sang
    "p_osc": [
        " ############## ",
        " #            # ",
        " #  #-#-#-#   # ",
        " # #       #  # ",
        " ##         ## #",
        " #           # #",
        " #   #####   # #",
        " #  #     #  # #",
        " #            # ",
        " ############## ",
        "   ###    ###   ",
    ],
    # 观测裙 -- the 4 m cone on the spent third stage: magnitude 2-3, the thing you could see
    "p_skirt": [
        "       #       ",
        "      ###      ",
        "      ###      ",
        "     #####     ",
        "     #####     ",
        "    #######    ",
        "   #########   ",
        "  ###########  ",
        " ############# ",
        " ###       ### ",
        " ###       ### ",
        " ###       ### ",
    ],
}

ALL = {**CRAFT, **STORY, **PARTS}


# ---------------------------------------------------------------- rendering

def grid(name: str) -> list[str]:
    return ALL[name]


@lru_cache(None)
def sprite(name: str, cell: int = 4, tint: str = "amber", gap: bool = True) -> Image.Image:
    """One icon, rasterised to blocks. Cached: there are only a couple of dozen of them."""
    g = ALL[name]
    rows, cols = len(g), max(len(r) for r in g)
    lum = Image.new("L", (cols, rows), 0)
    px = lum.load()
    for r, line in enumerate(g):
        for c, ch in enumerate(line):
            v = LEVELS.get(ch, 0.0)
            if v > 0:
                px[c, r] = int(round(v * 255))
    big = lum.resize((cols * cell, rows * cell), Image.NEAREST)
    if gap and cell >= 3:
        # the same one-pixel gutter the sprite grid uses, so the icon reads as terminal cells
        mask = Image.new("L", big.size, 255)
        d = ImageDraw.Draw(mask)
        for x in range(cell - 1, big.width, cell):
            d.line([x, 0, x, big.height], fill=0)
        for y in range(cell - 1, big.height, cell):
            d.line([0, y, big.width, y], fill=0)
        big = ImageChops.multiply(big, mask)
    rgb = tk.tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(big.point(lambda v: 0 if v < 8 else min(255, int(v * 1.25))))
    return rgb


def size_of(name: str, cell: int = 4) -> tuple[int, int]:
    sp = sprite(name, cell)
    return sp.size


def fit_cell(name: str, max_w: int, max_h: int, cap: int = 14) -> int:
    """The largest block size at which an icon still fits a box. Icons differ in shape, and one
    fixed cell size makes the wide ones (天宫, 天问一号) overflow while the tall ones look lost."""
    g = ALL[name]
    rows, cols = len(g), max(len(r) for r in g)
    return max(2, min(cap, int(max_w / cols), int(max_h / rows)))


def draw(c, xy, name: str, cell: int = 4, tint: str = "amber", alpha: float = 1.0,
         x0: int | None = None, y0: int | None = None, x1: int | None = None, y1: int | None = None) -> tuple[int, int]:
    """Paste an icon with its top-left at xy (or CENTRED on xy when x0/x1/y0/y1 are given)."""
    sp = sprite(name, cell, tint)
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    if x0 is not None:
        assert x1 is not None and y0 is not None and y1 is not None
        px = int((x0 + x1 - sp.width) / 2)
        py = int((y0 + y1 - sp.height) / 2)
    else:
        px, py = int(xy[0]), int(xy[1])
    c.img.paste(sp, (px, py), sp)
    return px, py
