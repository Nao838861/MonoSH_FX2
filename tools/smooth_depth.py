"""NES由来の段階寸法を、奥行きに沿った単調な曲線へ置き換える。"""
from fractions import Fraction
from pathlib import Path
import re

# 遠方の元画像frameの下限制限を曲線へ焼き込まないよう、最後はZ110までつなぐ。
# 近景の大きさ・中景の形・遠景の最小サイズは元データから取る。
ANCHORS = (0, 12, 24, 36, 48, 60, 72, 110)
TABLES = {
    'monosh_stage_data': [(f'stage_{name}_geometry', 4) for name in
                          ('bush0', 'bush1', 'flystone', 'em0', 'tree0', 'bom0')],
    'monosh_enemy_data': [(f'monosh_{name}_geometry', 2) for name in
                          ('enemy', 'bom', 'em1_closed', 'ebullet_animation', 'ebullet4')],
    'monosh_boss_data': [(f'monosh_boss_{name}_geometry', 2) for name in ('face', 'body', 'bom')],
}


def curve(values, anchors=ANCHORS):
    """単調3次Hermite補間。分数で生成し、出力画素へ最後に一度だけ丸める。"""
    assert len(values) == 111
    y = [Fraction(values[z]) for z in anchors]
    h = [b-a for a, b in zip(anchors, anchors[1:])]
    delta = [(b-a)/n for a, b, n in zip(y, y[1:], h)]
    assert all(d <= 0 for d in delta), values
    # 端は隣接区間の傾き。遠端の傾きを0にして長い停止区間を再導入しない。
    slope = [delta[0]]
    for i in range(1, len(y)-1):
        left, right = delta[i-1:i+1]
        if left == 0 or right == 0:
            slope.append(Fraction(0))
        else:
            w1 = 2*h[i] + h[i-1]
            w2 = h[i] + 2*h[i-1]
            slope.append((w1+w2)/(w1/left+w2/right))
    slope.append(delta[-1])
    result = []
    for z in range(111):
        i = next((i for i, right in enumerate(anchors[1:]) if z <= right), len(h)-1)
        t = Fraction(z-anchors[i], h[i])
        result.append((2*t**3-3*t**2+1)*y[i] + (t**3-2*t**2+t)*h[i]*slope[i]
                      + (-2*t**3+3*t**2)*y[i+1] + (t**3-t**2)*h[i]*slope[i+1])
    assert result[0] == values[0] and result[-1] == values[-1]
    assert all(a >= b for a, b in zip(result, result[1:]))
    return result


def rounded(values):
    return [(value+Fraction(1, 2)).numerator//(value+Fraction(1, 2)).denominator
            for value in curve(values)]


def tree_heights(values):
    # 木は接地Yの丸めと高さを別々に丸めると、樹冠が一瞬後退する。
    # 地面の伸びが最大のcamera行で樹冠を補間し、固定した接地Yから高さを戻す。
    text = (Path(__file__).resolve().parents[1]/'game/v001/upstream/monosh_projection_data.asm').read_text()
    data = text.split('_monosh_ground_depth_rows:', 1)[1]
    rows = []
    for line in data.splitlines():
        if line.strip().startswith('defb'):
            rows.extend(map(int, line.split('defb')[1].strip().split(',')))
        elif rows and line.strip() and not line.lstrip().startswith(';'):
            break
    assert len(rows) == 65*81
    bottom = [207-rows[219-values[z*4+2]]
              + (0 if z < 2 else 1 if z < 6 else 2 if z < 9 else 3) for z in range(111)]
    negative_top = [values[z*4+1]-bottom[z] for z in range(111)]
    top = [-v for v in rounded(negative_top)]
    return [b-t for b, t in zip(bottom, top)]


def parse_table(text, name):
    pattern = r'(const unsigned char ' + name + r'\[(\d+)\] = \{)(.*?)(\};)'
    match = re.search(pattern, text, re.S)
    assert match, name
    values = [int(v, 0) for v in re.findall(r'0x[0-9a-fA-F]+|\d+', match[3])]
    assert len(values) == int(match[2])
    return match, values


def open_enemy_sizes(text):
    """開いたEM1の5pose×3距離段階を、5pose×111奥行きへ展開する。"""
    _, original = parse_table(text, 'monosh_em1_open_geometry')
    curves = []
    for pose in range(5):
        dimensions = []
        for axis in (0, 1):
            source = [original[(pose+(10 if z < 54 else 5 if z < 80 else 0))*2+axis]
                      for z in range(111)]
            dimensions.append([int(v+Fraction(1, 2)) for v in curve(source, (0, 66, 110))])
        curves.append(list(zip(*dimensions)))
    return bytes(value for z in range(111) for pose in range(5) for value in curves[pose][z])


def transform(name, text):
    """固定upstreamは保持し、ビルドへ渡す幅・高さと半幅だけを更新する。"""
    for table, stride in TABLES.get(name, []):
        match, values = parse_table(text, table)
        assert len(values) == 111*stride
        result = list(values)
        for axis in (0, 1):
            result[axis::stride] = rounded(values[axis::stride])
        if table == 'stage_tree0_geometry':
            result[1::stride] = tree_heights(values)
        if stride == 4:
            result[3::stride] = [width//2 for width in result[::stride]]
        body = '\n' + ''.join('    '+','.join(map(str, result[i:i+16]))+',\n'
                              for i in range(0, len(result), 16))
        text = text[:match.start(3)] + body + text[match.end(3):]
    return text
