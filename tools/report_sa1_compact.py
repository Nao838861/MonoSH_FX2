"""疎タイル転送・左端クリップの比較を保存する。未達の結果も残す。"""
from pathlib import Path
import collections,json,statistics,zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_compact'
SCENARIOS=[
    'movestress_bottomslack_tracepalette',
    'movestress_densefastirq_tracepalette',
    'movestress_densedirtyiram_tracepalette',
    'movestress_cpupack_newonly64_tracepalette',
    'movestress_cpupack_hintmemo_tracepalette',
    'leftfixture_cpupack_hintiram_tracepalette',
    'movestress_cpupack_sa1map_tracepalette',
    'movestress_cpupack_fullfastrom_tracepalette',
    'movestress_cpupack_fullfastrom_long_tracepalette',
    'movestress_cpupack_sa1map_long_tracepalette',
    'leftfixture_rightjit_tracepalette',
    'movestress_rightjit_tracepalette',
    'movestress_leftall_tracepalette',
    'movestress_irqfastunroll_tracepalette',
    'movestress_irqfastunroll_long_tracepalette',
    'movestress_fallbackmask_tracepalette',
    'movestress_fallbackmask_fast_tracepalette',
    'movestress_fallbackearly_tracepalette',
    'movestress_fallbackearly_long_tracepalette',
]


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    index=[]
    with zipfile.ZipFile(DEST/'measurements.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in SCENARIOS:
            folder=BUILD/name
            summary=folder/'summary.json'
            if not summary.exists():continue
            d=json.loads(summary.read_text())
            p=d['presentationTimes']
            gaps=[b['visibleField']-a['visibleField'] for a,b in zip(p,p[1:])]
            entry={k:d[k] for k in ('fields','logic','presents','pixelMatchedPresents','goal60fpsAchieved') if k in d}
            entry.update(scenario=name,intervals=dict(collections.Counter(gaps)),
                         maxSa1Ms=max(x['totalSa1Ms'] for x in d['sa1Jobs']),
                         meanSa1Ms=statistics.mean(x['totalSa1Ms'] for x in d['sa1Jobs']),
                         meanOutputMs=statistics.mean(x['totalOutputMs'] for x in d['outputJobs']),
                         pauses=[{'generation':i+2,'fields':gap} for i,gap in enumerate(gaps) if gap!=1])
            index.append(entry)
            for f in sorted(folder.iterdir()):
                if f.is_file() and f.suffix in ('.json','.jsonl','.bin','.lbl','.lua','.txt','.log'):
                    archive.write(f,Path(name)/f.name)
        for name in ('movestress_cpupack_ppuguard_tracepalette',):
            folder=BUILD/name
            for f in folder.iterdir():
                if f.name in ('failure.txt','failure_state.txt','manifest.json','test.lua'):
                    archive.write(f,Path('failed')/name/f.name)
        for name in ('manifest.json','game.lbl','left_hints_verified.json','left_hints_packing.json','aligned_bounds_verified.json','right_clip_verified.json'):
            f=BUILD/name
            if f.exists():archive.write(f,Path('current_build')/name)
    (DEST/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    for entry in index:
        print(entry['scenario'],entry['presents'],entry['intervals'],entry['meanSa1Ms'],entry['maxSa1Ms'])


if __name__=='__main__':main()
