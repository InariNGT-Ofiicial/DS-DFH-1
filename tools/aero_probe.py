"""空气动力学 / 轨道力学标定 —— 把东方红一号的真实参数代进公式，看数字立不立得住。

口径声明（写死在文件头，避免以后自己都说不清）：
  [事实]  来自 pv/facts.py，可查证（CNSA / CAST 参数表）
  [推论]  由事实代入公认公式算出。不是新事实，是事实的必然结果，但"算出"这个动作是
          我们做的 —— 所以片子里若出现，要标成推算而非记录。
  [假定]  教科书典型值，我们选的，东方红一号实物数据没有公开。必须标注，不许冒充记录。

用法： python tools/aero_probe.py
"""
import math

# ----------------------------------------------------------------- 常数
MU = 398600.4418          # km^3/s^2   地球引力常数
R_E = 6371.0              # km         平均地球半径
RHO0 = 1.225              # kg/m^3     海平面密度
H_SCALE = 7.0             # km         对流层标高（指数大气）
R_AIR = 287.05            # J/kg/K

# ----------------------------------------------------------------- 她的记录 [事实]
M_SAT = 173.0             # kg
D_SAT = 1.0               # m
PERI, APO = 439.0, 2384.0                 # km, 1970 入轨
PERI09, APO09 = 430.0, 2075.0             # km, 2009 重测
PERIOD_MIN = 114.0                        # min
SKIRT_D = 4.0                             # m, 末级观测裙
THRUST_T = 104.0                          # t, 长征一号起飞推力
LIFT_T = 81.5                             # t, 起飞质量
LEN_M = 29.46
DIA_M = 2.25

print("=" * 74)
print("A. 1970 入轨轨道  [事实 -> 推论]")
r_p, r_a = R_E + PERI, R_E + APO
a = (r_p + r_a) / 2.0
T_s = 2 * math.pi * math.sqrt(a ** 3 / MU)
v_p = math.sqrt(MU * (2 / r_p - 1 / a))
v_a = math.sqrt(MU * (2 / r_a - 1 / a))
ecc = (r_a - r_p) / (r_a + r_p)
print(f"  半长轴 a        = {a:9.2f} km")
print(f"  偏心率 e        = {ecc:9.5f}")
print(f"  周期 (开普勒)   = {T_s/60:9.3f} min   [记录 114 min]")
print(f"  近地点速度      = {v_p:9.3f} km/s")
print(f"  远地点速度      = {v_a:9.3f} km/s")
print(f"  比能量 ε        = {(-MU/(2*a)):9.3f} km^2/s^2")

print()
print("=" * 74)
print("B. 2009 重测: 39 年掉了多少  [事实 -> 推论]")
a09 = (R_E + PERI09 + R_E + APO09) / 2.0
T09 = 2 * math.pi * math.sqrt(a09 ** 3 / MU)
d_peri, d_apo, d_a = PERI - PERI09, APO - APO09, a - a09
years = 39.0
revs = years * 365.25 * 24 * 60 / PERIOD_MIN
print(f"  近地点  439 -> {PERI09:.0f} km    降 {d_peri:.0f} km")
print(f"  远地点 2384 -> {APO09:.0f} km    降 {d_apo:.0f} km")
print(f"  半长轴 {a:.1f} -> {a09:.1f} km    降 {d_a:.1f} km")
print(f"  周期 {T_s/60:.3f} -> {T09/60:.3f} min   39 年累计慢 {(T_s-T09):.1f} s")
print(f"  39 年绕行圈数   = {revs:,.0f} 圈   ({revs/365.25/years:.2f} 圈/天)")
print(f"  >> 平均每圈半长轴降 = {d_a*1000/revs:.3f} m/圈 = {d_a*1000/revs*1000:.1f} mm/圈")
# 每圈的周期变化率 dT/da = 3*pi*sqrt(a/mu)
dTda = 3 * math.pi * math.sqrt(a / MU) / 60          # min per km -> 转成 s per m 见下
dT_per_rev = 3 * math.pi * math.sqrt((a * 1000) / (MU * 1e9)) * (d_a * 1000 / revs)  # s
print(f"  >> 平均每圈周期增加 = {dT_per_rev*1000:.2f} ms/圈")
print(f"  近地点降 {d_peri:.0f} km 但远地点降 {d_apo:.0f} km —— 阻力集中在近地点附近，")
print(f"     在那里削速度，先削掉的是远地点 (圆化)。这是大气衰减的典型特征。")

print()
print("=" * 74)
print("C. 大气阻力: 为什么电停了轨道没停  [事实 + 假定]")
A_sat = math.pi * (D_SAT / 2) ** 2
am = A_sat / M_SAT
print(f"  迎风面积 (球)   = {A_sat:.4f} m^2")
print(f"  面积质量比 A/m  = {am:.6f} m^2/kg   (越小越抗衰减)")
v = v_p
# 反推有效密度: 用 2009 实测的 da/dt 解出 rho
da_dt = (a09 - a) * 1000 / (years * 365.25 * 86400)     # m/s (负)
CD = 2.2                                                # [假定] 自由分子流典型值
# da/dt = -2 a^2/mu * (a_drag * v);  a_drag = 0.5 rho v^2 CD A/m
# => rho = -da_dt * mu / (2 a^2 v * 0.5 v^2 CD A/m)
rho_eff = -da_dt * (MU * 1e9) / (2 * (a * 1000) ** 2 * v * 1000 * 0.5 * (v * 1000) ** 2 * CD * am)
print(f"  半长轴衰减率    = {da_dt*1000:.4f} mm/s = {da_dt*365.25*86400/1000:.2f} km/yr")
print(f"  >> 反推有效密度 = {rho_eff:.3e} kg/m^3  (取 C_D={CD} [假定])")
print(f"     对照: 海平面 {RHO0} / 200 km 约 2.5e-10 / 她所在 439 km 量级 1e-13")
a_drag = 0.5 * rho_eff * (v * 1000) ** 2 * CD * am
print(f"  近地点阻力加速度 = {a_drag:.3e} m/s^2 = {a_drag/9.80665:.3e} g")
print(f"  >> 对照: 她受到的阻力是重力的 {a_drag/9.80665:.1e} 倍")

print()
print("=" * 74)
print("D. 上升段: 104 t 推力推 81.5 t  [事实 + 假定]")
T_N = THRUST_T * 1000 * 9.80665
W_N = LIFT_T * 1000 * 9.80665
twr = T_N / W_N
a_liftoff = (T_N - W_N) / (LIFT_T * 1000)
print(f"  起飞推力        = {T_N/1000:.0f} kN")
print(f"  起飞推重比      = {twr:.4f}   (大于 1 才离得开架)")
print(f"  离架加速度      = {a_liftoff:.3f} m/s^2 = {a_liftoff/9.80665:.3f} g")
print(f"  尾焰动压 (海平面, 喷口) 量级 q = 0.5 rho v_e^2 ... 见 E")
print(f"  箭体长细比      = {LEN_M/DIA_M:.2f}")

print()
print("=" * 74)
print("E. 最大动压 max-Q  [假定弹道 -> 推论]")
# 一维竖直积分: 牛顿 + 变质量 + 指数大气。低空竖直段够准，max-Q 就在这一段。
A_ref = math.pi * (DIA_M / 2) ** 2      # m^2   箭体迎风
CD_body = 0.30                          # [假定] 亚声速钝体
ISP = 260.0                             # s     [假定] 一级 煤油/硝酸
mdot = T_N / (ISP * 9.80665)
m0 = LIFT_T * 1000
m = m0
hh = vv = 0.0
tt = 0.0
step = 0.05
best = (0.0, 0.0, 0.0, 0.0)
while tt < 200 and m > m0 * 0.2:
    rho = RHO0 * math.exp(-hh / (H_SCALE * 1000)) if hh < 120000 else 0.0
    D = 0.5 * rho * vv * vv * CD_body * A_ref
    acc = (T_N - D) / m - 9.80665
    vv += acc * step
    hh += vv * step
    m -= mdot * step
    qq = 0.5 * rho * vv * vv
    if qq > best[0]:
        best = (qq, tt, hh, vv)
    tt += step
q, tq, hq, vq = best
print(f"  max-Q 量级      ~ {q/1000:.1f} kPa   在 t~{tq:.0f} s, h~{hq/1000:.1f} km, v~{vq:.0f} m/s")
T_inf = 288.15 - 6.5 * (hq / 1000) if hq / 1000 < 11 else 216.65
cs = math.sqrt(1.4 * R_AIR * T_inf)
Mach = vq / cs
T_stag = T_inf * (1 + 0.2 * Mach ** 2)
print(f"  当地声速/温度   = {cs:.0f} m/s / {T_inf:.1f} K    马赫 M = {Mach:.2f}")
print(f"  滞止温度 T0     = {T_stag:.1f} K = {T_stag-273.15:.0f} C")
print(f"  >> 对照: 再入式飞行器驻点动辄上千度；她在这个马赫数下是【常温】——")
print(f"     所以她的热障不在气动加热，而在真空里的太阳辐照与自旋热控。")

print()
print("=" * 74)
print("F. 一句话结论")
per_rev_m = d_a * 1000 / revs
print("  电波活了 28 天，轨道活了 56 年；每绕地球一圈，她只掉了 %.2f 米。" % per_rev_m)
