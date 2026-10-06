"""観測したボス戦の締切・CPU/GSU時間から必要短縮率を計算する。"""
import argparse
import json
from pathlib import Path
import statistics

from build_game import BUILD

HZ = 21_477_272
LINE_CLOCKS = 1364
FRAME_CLOCKS = LINE_CLOCKS * 262


def physical_frame(stamp):
    # NTSC非interlace、NMI=225。PPU frameCountは225行で増える。
    return stamp['ppuFrame'] - (stamp['line'] >= 225)


def frame_origin(frame):
    # 奇数fieldの240行目だけ4clock短い。uint32のmasterClockも復元できる。
    return frame * FRAME_CLOCKS - 4 * (frame // 2)


def absolute_clock(stamp):
    frame = physical_frame(stamp)
    line_origin = frame_origin(frame) + stamp['line'] * LINE_CLOCKS
    if frame % 2 and stamp['line'] > 240:
        line_origin -= 4
    reconstructed_h = (stamp['clock'] - line_origin) & 0xffffffff
    assert 0 <= reconstructed_h < LINE_CLOCKS, stamp
    if 'hclock' in stamp:
        assert stamp['hclock'] == reconstructed_h, stamp
    return line_origin + reconstructed_h


def milliseconds(clocks):
    return clocks / HZ * 1000


def improvement(work, budget):
    assert budget > 0
    return {'timeReductionPercent': max(0, (1 - budget / work) * 100),
            'speedIncreasePercent': max(0, (work / budget - 1) * 100)}


def analyze(path):
    records = [json.loads(line) for line in (path / 'timings.jsonl').read_text().splitlines()]
    source_summary = json.loads((path / 'summary.json').read_text())
    assert len(records) == source_summary['rendered']
    if 'joinedMaxMs' not in source_summary:
        # 従来test.luaのcpuMaxMsは合流時刻だった。解析結果では名称を正す。
        source_summary['joinedMaxMs'] = source_summary.pop('cpuMaxMs')
    source_summary['cpuMaxMs'] = max(milliseconds(absolute_clock(row['cpuEnd']) - absolute_clock(row['start']))
                                    for row in records)
    calibration_path = path.parent / 'boss_profile_serial'
    calibration_summary = json.loads((calibration_path / 'summary.json').read_text())
    assert calibration_summary['romSha256'] == source_summary['romSha256']
    calibration = [json.loads(line) for line in (calibration_path / 'timings.jsonl').read_text().splitlines()]
    admission_costs = [absolute_clock(row['dmaStart']) - absolute_clock(row['admitted']) for row in calibration]
    # 待ちを除いた固定設定＋OAM転送。同じROM・固定68byte OAM経路の最大を使用。
    admission_cost = max(admission_costs)
    output = []
    for index, record in enumerate(records):
        points = {name: absolute_clock(record[name]) for name in
                  ('start', 'cpuEnd', 'gsuEnd', 'joined', 'ready', 'dmaStart', 'dmaEnd')}
        assert points['joined'] >= max(points['cpuEnd'], points['gsuEnd'])
        assert points['start'] <= points['ready'] <= points['dmaStart'] <= points['dmaEnd']
        if not record.get('previousDma'):
            continue
        prev = record['previousDma']
        prev_start, prev_end = absolute_clock(prev['start']), absolute_clock(prev['finish'])
        # 直前の画像を提示した物理fieldの次fieldが60Hz更新の目標。
        target_frame = physical_frame(prev['start']) + 1
        # 締切行の末尾を上限とする。ポーリングの命令時間は別途余裕が必要。
        deadline = frame_origin(target_frame) + (record['deadline'] + 1) * LINE_CLOCKS
        post_join = points['ready'] - max(points['cpuEnd'], points['gsuEnd'])
        allowed = deadline - points['start'] - post_join
        assert allowed > 0
        cpu, gsu = points['cpuEnd'] - points['start'], points['gsuEnd'] - points['start']
        current_frame = physical_frame(record['dmaStart'])
        interval = current_frame - physical_frame(prev['start'])
        assert interval >= 1
        row = {'image': index + 1, 'logic': record['logic'], 'boss': record['boss'], 'hp': record['hp'],
               'player': record['player'], 'x': record['x'], 'y': record['y'],
               'commands': record['commands'], 'enemyShots': record['enemyShots'], 'shots': record['shots'],
               'dmaBytes': record['bytes'], 'dmaSpans': record['spans'], 'deadlineLine': record['deadline'],
               'cpuMs': milliseconds(cpu), 'gsuMs': milliseconds(gsu),
               'joinedMs': milliseconds(points['joined'] - points['start']),
               'dmaMs': milliseconds(points['dmaEnd'] - points['dmaStart']),
               'previousDmaMs': milliseconds(prev_end - prev_start),
               'preparationMs': milliseconds(points['start'] - prev_end),
               'postJoinMs': milliseconds(post_join),
               'overlapBudgetMs': milliseconds(allowed),
               'deadlineMissMs': milliseconds(points['ready'] - deadline),
               'dmaStartFrame': current_frame, 'presentationIntervalFields': interval,
               'bottleneck': 'GSU' if gsu > cpu else 'CPU',
               'requiredGsu': improvement(gsu, allowed), 'requiredCpu': improvement(cpu, allowed),
               'simpleGsuVs16ms': improvement(gsu, FRAME_CLOCKS - 2), 'raw': record}
        row['requiredBoth'] = improvement(max(cpu, gsu), allowed)
        # 1scanline（約0.064ms）の余裕を追加した、保守的な目標も併記する。
        row['withOneLineReserve'] = {
            'overlapBudgetMs': milliseconds(allowed - LINE_CLOCKS),
            'requiredGsu': improvement(gsu, allowed - LINE_CLOCKS),
            'requiredCpu': improvement(cpu, allowed - LINE_CLOCKS)}
        # 220行までの開始猶予は単発の締切には効くが、繰り返し加算はできない。
        # 連続60Hzでは非並行部分＋max(CPU,GSU)を1field以内へ収める。
        serial = (prev_end - prev_start) + (points['start'] - prev_end) + post_join + admission_cost
        steady_allowed = FRAME_CLOCKS - 2 - serial
        row['steady'] = {
            'serialMs': milliseconds(serial), 'overlapBudgetMs': milliseconds(steady_allowed),
            'requiredGsu': improvement(gsu, steady_allowed), 'requiredCpu': improvement(cpu, steady_allowed),
            'requiredBoth': improvement(max(cpu, gsu), steady_allowed),
            'withOneLineReserve': improvement(max(cpu, gsu), steady_allowed - LINE_CLOCKS)}
        output.append(row)
    fights = [row for row in output if row['boss'] in (1, 2)]
    assert fights, 'no boss frames measured'
    def distribution(name):
        values = sorted(row[name] for row in fights)
        return {'mean': statistics.mean(values), 'p95': values[int((len(values) - 1) * .95)], 'max': values[-1]}
    worst_work = max(fights, key=lambda row: max(row['cpuMs'], row['gsuMs']))
    worst_budget = max(fights, key=lambda row: row['requiredBoth']['timeReductionPercent'])
    worst_steady = max(fights, key=lambda row: row['steady']['requiredBoth']['timeReductionPercent'])
    # 60物理field窓。DMA開始で数え、DMA終了が次fieldにまたぐ影響を除く。
    frame_set = {row['dmaStartFrame'] for row in fights}
    windows = [(sum(frame + i in frame_set for i in range(60)), frame) for frame in sorted(frame_set)
               if frame + 59 <= max(frame_set)
               and all(any(frame + i + k in frame_set for k in range(3)) for i in range(58))]
    worst_window = min(windows) if windows else None
    result = {'measurement': source_summary, 'masterHz': HZ,
              'fieldPeriodMs': milliseconds(FRAME_CLOCKS - 2), 'nativeFieldsPerSecond': HZ / (FRAME_CLOCKS - 2),
              'bossImages': len(fights), 'activeBossImages': sum(row['boss'] == 1 for row in fights),
              'dyingBossImages': sum(row['boss'] == 2 for row in fights),
              'cpuMs': distribution('cpuMs'), 'gsuMs': distribution('gsuMs'),
              'intervals': {str(n): sum(row['presentationIntervalFields'] == n for row in fights)
                            for n in sorted({row['presentationIntervalFields'] for row in fights})},
              'worstWork': worst_work, 'worstRequiredReduction': worst_budget,
              'worstSteady60Hz': worst_steady,
              'worstAliveActiveBoss': max((row for row in fights if row['boss'] == 1 and row['player'] == 0),
                                         key=lambda row: row['requiredBoth']['timeReductionPercent']),
              'maximumRequiredCpuReductionPercent': max(row['requiredCpu']['timeReductionPercent'] for row in fights),
              'maximumRequiredSteadyCpuReductionPercent': max(row['steady']['requiredCpu']['timeReductionPercent'] for row in fights),
              'admissionCalibration': {'scenario': calibration_path.name, 'images': len(calibration),
                  'meanMs': milliseconds(statistics.mean(admission_costs)), 'maxMs': milliseconds(admission_cost),
                  'romSha256': calibration_summary['romSha256']},
              'worst60FieldWindow': None if worst_window is None else {
                  'images': worst_window[0], 'startPhysicalFrame': worst_window[1],
                  'fps': worst_window[0] / 60 * HZ / (FRAME_CLOCKS - 2)},
              'limitations': ['締切行末を上限にした局所推定。速度変更後のDMA位相やゲーム状態は再計測が必要。',
                              'CPUとGSUは並行実行。処理時間は加算しない。',
                              '現在のMesen・ROM・パッド入力で観測した最大。全入力や実機の最悪保証ではない。']}
    (path / 'budget.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (path / 'analyzed.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in fights), encoding='utf-8')
    print(path.name, 'boss images', len(fights))
    for name, row in [('worstWork', worst_work), ('worstRequiredReduction', worst_budget), ('worstSteady60Hz', worst_steady)]:
        goal = row['steady'] if name == 'worstSteady60Hz' else row
        print(name, 'image', row['image'], 'CPU', round(row['cpuMs'], 4), 'GSU', round(row['gsuMs'], 4),
              'budget', round(goal['overlapBudgetMs'], 4), 'required', goal['requiredBoth'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=('boss_profile', 'boss_profile_linger'))
    args = parser.parse_args()
    analyze(BUILD / args.scenario)


if __name__ == '__main__':
    main()
