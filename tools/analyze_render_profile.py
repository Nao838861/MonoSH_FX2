"""自然なプレイの提示間隔を道中・ボス別に集計する。DMA開始fieldを基準とする。"""
import argparse
from bisect import bisect_left
import gzip
import json
from pathlib import Path
import statistics

from analyze_boss_profile import absolute_clock, physical_frame, milliseconds, FRAME_CLOCKS, HZ


def analyze(path):
    summary=json.loads((path/'summary.json').read_text())
    source=path/'timings.jsonl'
    raw=source.read_bytes() if source.exists() else gzip.decompress(source.with_suffix('.jsonl.gz').read_bytes())
    records=[json.loads(line) for line in raw.splitlines()]
    assert len(records)==summary['rendered']
    output={'romSha256':summary['romSha256'],'fields':summary['fields'],
            'nativeFps':HZ/(FRAME_CLOCKS-2),'images':len(records),'groups':{}}
    previous=None;intervals=[];segments=[];segment=[]
    for row in records:
        row['dmaField']=physical_frame(row['dmaStart'])
        row['cpuMs']=milliseconds(absolute_clock(row['cpuEnd'])-absolute_clock(row['start']))
        row['gsuMs']=milliseconds(absolute_clock(row['gsuEnd'])-absolute_clock(row['start']))
        row['group']='road' if row['boss']==0 else 'boss' if row['boss'] in (1,2) else 'transition'
        if previous and row['group']==previous['group']:
            gap=row['dmaField']-previous['dmaField'];assert gap>=1
            intervals.append({**row,'gap':gap})
        if segment and row['group']!=segment[-1]['group']:
            segments.append(segment);segment=[]
        segment.append(row);previous=row
    if segment:segments.append(segment)
    for group in ('road','boss','transition'):
        all_rows=[r for r in records if r['group']==group]
        pairs=[r for r in intervals if r['group']==group]
        if not pairs:continue
        missed=sum(r['gap']-1 for r in pairs);fields=sum(r['gap'] for r in pairs)
        windows=[]
        for seg in segments:
            if seg[0]['group']!=group:continue
            presented=[r['dmaField'] for r in seg]
            for start in range(presented[0],presented[-1]-58):
                count=bisect_left(presented,start+60)-bisect_left(presented,start)
                windows.append((count,start))
        worst=min(windows) if windows else None
        values=[r['gsuMs'] for r in all_rows]
        worst_row=max(all_rows,key=lambda r:r['gsuMs'])
        output['groups'][group]={'images':len(all_rows),'intervalsMeasured':len(pairs),
            'presentationIntervals':{str(n):sum(r['gap']==n for r in pairs) for n in sorted({r['gap'] for r in pairs})},
            'slowImages':sum(r['gap']>1 for r in pairs),
            'slowImagePercent':100*sum(r['gap']>1 for r in pairs)/len(pairs),
            'repeatedFields':missed,'repeatedFieldPercent':100*missed/fields,
            'averageFps':len(pairs)/fields*output['nativeFps'],
            'observedSeconds':fields/output['nativeFps'],
            'cpuMaxMs':max(r['cpuMs'] for r in all_rows),
            'gsuMeanMs':statistics.mean(values),'gsuP95Ms':sorted(values)[int((len(values)-1)*.95)],
            'gsuMaxMs':max(values),'worstGsuScene':worst_row,
            'worst60FieldWindow':None if worst is None else {'images':worst[0],
                'startPhysicalField':worst[1],'fps':worst[0]/60*output['nativeFps']},
            'alive':{'images':sum(r['player']==0 for r in pairs),
                     'slowImages':sum(r['player']==0 and r['gap']>1 for r in pairs)}}
    output['definitions']={'road':'GSU開始時boss=0。起動・死亡・復帰も含む。',
        'boss':'GSU開始時boss=1または2。撃破後boss=3はtransitionへ分離。',
        'slowImages':'同じ区分の連続画像間でDMA開始の間隔が2field以上になった画像数。',
        'averageFps':'区分が切り替わる境界を除外し、同区分内の提示間隔を時間加重して算出。',
        'worstWindow':'区分をまたがない60field（約0.998秒）窓の新画像数。',
        'limitation':'今回のMesenと入力で観測した頻度。任意のプレイや実機の保証ではない。'}
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=analyze(args.path)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,group in result['groups'].items():
        print(name,'slow',group['slowImages'],'/',group['intervalsMeasured'],round(group['slowImagePercent'],3),
              'percent; fps',round(group['averageFps'],3),'worst window',group['worst60FieldWindow'])


if __name__=='__main__':main()
