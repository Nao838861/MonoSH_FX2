"""完成画像の世代と描画・本体転送の費用を並べて確認する。"""
import argparse,collections,json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('scenario')
    args=parser.parse_args()
    d=json.loads((Path(__file__).resolve().parents[1]/'build/sa1_game'/args.scenario/'summary.json').read_text())
    print('slow draw jobs')
    jobs=sorted(enumerate(d['sa1Jobs'],1),key=lambda x:x[1]['totalSa1Ms'],reverse=True)[:12]
    for gen,job in jobs:
        print(gen,{k:round(v,3) if isinstance(v,float) else v for k,v in job.items() if k!='cpuParts'})
        print([x for x in d['objectJobs'] if x['job']==gen])
    print('stage jobs', sorted(d.get('cpuStageJobs',[]),key=lambda x:x['ms'],reverse=True)[:10])
    print('pauses',[(i+2,b['visibleField']-a['visibleField']) for i,(a,b) in enumerate(zip(d['presentationTimes'],d['presentationTimes'][1:])) if b['visibleField']-a['visibleField']!=1])
    totals=collections.defaultdict(float)
    for x in d['objectJobs']:totals[x['asset']]+=x['ms']
    print('object time',dict(sorted(totals.items(),key=lambda x:x[1],reverse=True)))


if __name__=='__main__':main()
