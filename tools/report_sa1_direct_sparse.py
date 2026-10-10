"""ゲーム処理分離とVRAM直接疎転送の比較証拠を保存する。"""
from pathlib import Path
import collections,json,statistics,zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_direct_sparse'
SCENARIOS=(
    'movestress_sa1game_boot_tracepalette',
    'movestress_sa1game_tracepalette',
    'movestress_sa1game_overlap_raw_tracepalette',
    'movestress_directsparse3_tracepalette',
    'movestress_directsparse3_unroll_valid_tracepalette',
    'movestress_directsparse3_prefix_beam_tracepalette',
    'movestress_directsparse3_prefix_c1_tracepalette',
    'movestress_directsparse3_mapoverlap_tracepalette',
    'movestress_directsparse3_prefixtable_fixed_tracepalette',
)


def main():
    DEST.mkdir(parents=True,exist_ok=True);index=[]
    with zipfile.ZipFile(DEST/'measurements.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in SCENARIOS:
            folder=BUILD/name;d=json.loads((folder/'summary.json').read_text())
            assert d.get('pixelMatchedPresents',0)>=120,name
            p=d['presentationTimes']
            entry={k:d[k] for k in ('fields','logic','presents','pixelMatchedPresents','goal60fpsAchieved')}
            gaps=[b['visibleField']-a['visibleField'] for a,b in zip(p,p[1:])]
            entry.update(scenario=name,intervals=dict(collections.Counter(gaps)),
                         pauses=[{'generation':i+2,'fields':gap} for i,gap in enumerate(gaps) if gap!=1],
                         maxSa1Ms=max(j['totalSa1Ms'] for j in d['sa1Jobs']),
                         meanSa1Ms=statistics.mean(j['totalSa1Ms'] for j in d['sa1Jobs']))
            index.append(entry)
            for path in folder.iterdir():
                if path.is_file() and path.suffix in ('.json','.jsonl','.bin','.lbl','.lua','.txt','.log'):
                    archive.write(path,Path(name)/path.name)
        for name in ('manifest.json','game.lbl','aligned_bounds_verified.json','left_hints_verified.json'):
            archive.write(BUILD/name,Path('current_build')/name)
        for name in ('movestress_directsparse3_prefix_tracepalette',
                     'movestress_directsparse3_prefix_bank1_retry_tracepalette',
                     'movestress_directsparse3_prefixtable_tracepalette'):
            for path in (BUILD/name).iterdir():
                if path.name in ('failure.txt','failure_state.txt','pixel_failure.txt','manifest.json','game.lbl','test.lua','emulator.log') or path.name.startswith('present00002_'):
                    archive.write(path,Path('failed')/name/path.name)
    (DEST/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    for row in index:print(row['scenario'],row['presents'],row['intervals'])


if __name__=='__main__':main()
