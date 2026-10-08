"""Summarize measured presentation rate from exact DMA-start fields.

This never infers game FPS from emulator wall time or CPU/GSU time alone.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from analyze_boss_profile import absolute_clock, physical_frame, HZ, FRAME_CLOCKS
from build_game import BUILD

NTSC_HZ = HZ / (FRAME_CLOCKS - 2)


def report(directory):
    summary = json.loads((directory / 'summary.json').read_text())
    rows = [json.loads(line) for line in (directory / 'timings.jsonl').read_text().splitlines()]
    assert rows and len(rows) == summary['rendered']
    frames = [physical_frame(row['dmaStart']) for row in rows]
    gaps = [b-a for a,b in zip(frames, frames[1:])]
    assert all(gap >= 0 for gap in gaps)
    unique = sorted(set(frames))
    display_gaps = [b-a for a,b in zip(unique, unique[1:])]
    output = {
        'romSha256': summary['romSha256'],
        'emulatorSha256': summary['mesenSha256'],
        'fieldsRequested': summary['framesRequested'],
        'presentations': len(unique),
        'extraWritesInSameBlank': len(rows) - len(unique),
        'presentationIntervals': dict(sorted(Counter(display_gaps).items())),
        'presentationFps': (len(unique)-1) * NTSC_HZ / (unique[-1]-unique[0]),
        'intervalBasis': 'DMA start physical field, startup excluded',
        'fullFramebufferTransfers': sum(row['bytes'] == 12288 for row in rows),
        'sections': {},
        'physicalHardware': False,
    }
    for name, predicate in [('all', lambda r: True), ('road', lambda r: r['boss'] == 0),
                            ('bossAlive', lambda r: r['boss'] == 1),
                            ('bossDying', lambda r: r['boss'] == 2),
                            ('bossDone', lambda r: r['boss'] == 3)]:
        selected = [r for r in rows if predicate(r)]
        if not selected:
            continue
        indices = [i for i,r in enumerate(rows) if i > 0 and predicate(r) and predicate(rows[i-1])]
        section_gaps = [frames[i]-frames[i-1] for i in indices]
        cpu = [(absolute_clock(r['cpuEnd'])-absolute_clock(r['start'])) / HZ * 1000 for r in selected]
        gsu = [(absolute_clock(r['gsuEnd'])-absolute_clock(r['start'])) / HZ * 1000 for r in selected]
        output['sections'][name] = {
            'images': len(selected), 'intervals': dict(sorted(Counter(section_gaps).items())),
            'cpuMeanMs': statistics.mean(cpu), 'cpuMaxMs': max(cpu),
            'gsuMeanMs': statistics.mean(gsu), 'gsuMaxMs': max(gsu),
        }
    output['steady60Hz'] = all(gap == 1 for gap in gaps)
    (directory / 'performance.json').write_text(json.dumps(output, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--require-60hz', action='store_true')
    parser.add_argument('--require-boss', action='store_true')
    args = parser.parse_args()
    result = report(args.directory)
    print(json.dumps(result, indent=2))
    if args.require_60hz:
        assert result['steady60Hz'], 'Not every post-startup presentation interval is one NTSC field'
    if args.require_boss:
        assert result['sections'].get('bossAlive', {}).get('images', 0) >= 3000, 'Insufficient sustained boss coverage'


if __name__ == '__main__':
    main()
