"""EV 教程配套工具：重掷游戏模拟、EV 计算器、Kelly 计算器。

用法：
    python ev_tools.py reroll 3            # 最多掷 3 次骰子的最优门槛 + 模拟
    python ev_tools.py ev 10:1/6 -2:5/6    # 收益:概率，概率可写分数
    python ev_tools.py kelly 0.55 1        # 胜率 p，赔率 b
只依赖 Python 标准库。
"""
from __future__ import annotations

import math
import random
import sys
from fractions import Fraction


def parse_num(s: str) -> float:
    """把 '1/6'、'0.25'、'3' 之类的字符串转成数字。"""
    return float(Fraction(s.strip()))


# ---------- 重掷游戏（最优停止） ----------

def reroll_values(n: int) -> list[float]:
    """v[k-1] = 最多还能掷 k 次时的最优期望。v_1 = 3.5，v_k = E[max(X, v_{k-1})]。"""
    v = [3.5]
    for _ in range(1, n):
        v.append(sum(max(x, v[-1]) for x in range(1, 7)) / 6)
    return v


def reroll_policy(n: int) -> list[tuple[int, float | None, str]]:
    """每一次掷骰子的（序号, 继续的期望值, 最优动作）。"""
    v = reroll_values(n)
    rows = []
    for i in range(1, n + 1):
        left = n - i
        if left == 0:
            rows.append((i, None, "必须接受"))
        else:
            c = v[left - 1]
            rows.append((i, c, f"掷出 ≥ {math.floor(c) + 1} 就停"))
    return rows


def simulate_reroll(n: int, games: int = 20000, seed: int | None = None) -> float:
    """按最优策略模拟 games 局，返回平均得分。"""
    rng = random.Random(seed)
    v = reroll_values(n)
    total = 0
    for _ in range(games):
        for i in range(1, n + 1):
            r = rng.randint(1, 6)
            left = n - i
            if left == 0 or r > v[left - 1]:
                total += r
                break
    return total / games


# ---------- EV 计算器 ----------

def ev_stats(outcomes: list[tuple[float, float]]) -> dict[str, float]:
    """outcomes = [(收益, 概率), ...]，返回期望、标准差和概率合计。"""
    e = sum(x * p for x, p in outcomes)
    e2 = sum(x * x * p for x, p in outcomes)
    ps = sum(p for _, p in outcomes)
    return {"ev": e, "sd": math.sqrt(max(e2 - e * e, 0.0)), "prob_sum": ps}


# ---------- Kelly 计算器 ----------

def kelly(p: float, b: float) -> dict[str, float]:
    """赢时每 1 元赚 b 元，输时赔 1 元，胜率 p。"""
    q = 1 - p
    f = p - q / b

    def g(fr: float) -> float:
        return p * math.log(1 + b * fr) + q * math.log(1 - fr)

    ok = 0 < f < 1
    return {
        "ev_per_unit": p * b - q,
        "f_star": f,
        "g_full": g(f) if ok else float("nan"),
        "g_half": g(f / 2) if ok else float("nan"),
    }


# ---------- 命令行 ----------

def _fmt(x: float) -> str:
    if math.isfinite(x) and abs(x) < 5e-5:
        x = 0.0
    return f"{x:.4f}" if math.isfinite(x) else "—"


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "reroll":
        n = int(args[0]) if args else 3
        games = int(args[1]) if len(args) > 1 else 20000
        print(f"最多可掷 {n} 次")
        for i, c, act in reroll_policy(n):
            print(f"  第 {i} 次 | 继续的期望值 {'—' if c is None else f'{c:.3f}'} | {act}")
        print(f"理论最优期望：{reroll_values(n)[-1]:.4f}")
        print(f"模拟 {games} 局平均得分：{simulate_reroll(n, games):.4f}")
    elif cmd == "ev":
        outs = []
        for a in args:
            x, p = a.split(":")
            outs.append((parse_num(x), parse_num(p)))
        r = ev_stats(outs)
        print(f"期望 EV：{_fmt(r['ev'])}")
        print(f"标准差：{_fmt(r['sd'])}")
        ok = abs(r["prob_sum"] - 1) < 1e-9
        print(f"概率合计：{'1（正确）' if ok else _fmt(r['prob_sum']) + '（应为 1）'}")
    elif cmd == "kelly":
        p = parse_num(args[0]) if args else 0.55
        b = parse_num(args[1]) if len(args) > 1 else 1.0
        r = kelly(p, b)
        print(f"每 1 元的 EV：{_fmt(r['ev_per_unit'])}")
        print(f"Kelly 比例 f*：{r['f_star'] * 100:.2f}%" if r["f_star"] > 0 else "Kelly 比例 f*：≤ 0，不下注")
        print(f"全 Kelly 每次对数增长：{_fmt(r['g_full'])}")
        print(f"半 Kelly 每次对数增长：{_fmt(r['g_half'])}")
    else:
        print(f"未知命令：{cmd}\n{__doc__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
