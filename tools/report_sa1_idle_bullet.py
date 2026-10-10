"""先行消去・敵弾・連続転送の試験を、ROMごとの証拠と一緒に残す。"""
from pathlib import Path
import collections,json,statistics,zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_idle_bullet'
SCENARIOS=(
    'movestress_directsparse3_prefix_c1_long_tracepalette',
    'movestress_directsparse3_gap32_tracepalette',
    'movestress_directsparse3_gap64_tracepalette',
    'movestress_directsparse3_idleclear_tracepalette',
    'movestress_directsparse3_idleclear_long_tracepalette',
    'movestress_directsparse3_bulletleft_long_tracepalette',
    'movestress_directsparse3_contiguous_tracepalette',
    'flipfixture_bulletopacity_tracepalette',
    'movestress_directsparse3_opacity_long_tracepalette',
    'movestress_directsparse3_opacity_timing_tracepalette',
    'movestress_directsparse3_contiguoustable_tracepalette',
    'movestress_directsparse3_table_iram_tracepalette',
    'movestress_directsparse3_cputable_iram_tracepalette',
    'movestress_directsparse3_cputable_nomath_tracepalette',
)


def main():
    DEST.mkdir(parents=True,exist_ok=True);index=[]
    with zipfile.ZipFile(DEST/'measurements.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in SCENARIOS:
            folder=BUILD/name;d=json.loads((folder/'summary.json').read_text())
            config=json.loads((folder/'manifest.json').read_text())
            assert d['pixelMatchedPresents']>=120,name
            times=d['presentationTimes']
            gaps=[b['visibleField']-a['visibleField'] for a,b in zip(times,times[1:])]
            eligible=not (config.get('prefixTable') or config.get('prefixCpuTable')) or d.get('irqMathRegistersVerified',False)
            row={k:d[k] for k in ('fields','logic','presents','pixelMatchedPresents','goal60fpsAchieved','romSha256')}
            row.update(scenario=name,intervals=dict(collections.Counter(gaps)),
                       pauses=[{'generation':i+2,'fields':gap} for i,gap in enumerate(gaps) if gap!=1],
                       maxSa1Ms=max(x['totalSa1Ms'] for x in d['sa1Jobs']),
                       meanClearMs=statistics.mean(x['clearMs'] for x in d['sa1Jobs']),
                       performanceComparisonEligible=eligible,
                       irqMathRegistersVerified=d.get('irqMathRegistersVerified',False))
            index.append(row)
            for path in folder.iterdir():
                if path.is_file() and path.suffix in ('.json','.jsonl','.bin','.lbl','.lua','.txt','.log'):
                    archive.write(path,Path(name)/path.name)
        for name in ('manifest.json','game.lbl','aligned_bounds_verified.json','left_hints_verified.json'):
            archive.write(BUILD/name,Path('current_build')/name)
    (DEST/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    for row in index:print(row['scenario'],row['presents'],row['intervals'],row['performanceComparisonEligible'])


if __name__=='__main__':main()
