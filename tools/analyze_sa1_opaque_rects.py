"""爆発の完全不透明矩形で、奥の行を安全に省ける上限を測る。"""
import argparse,json,struct
from pathlib import Path
import numpy as np
from analyze_sa1_occlusion import pixels,word_rows
from test_sa1_probe import reference


def largest_rectangle(mask):
    heights=np.zeros(mask.shape[1],dtype=np.int32);best=(0,0,0,0);area=0
    for y,row in enumerate(mask):
        heights=np.where(row,heights+1,0);stack=[]
        for x in range(len(heights)+1):
            h=int(heights[x]) if x<len(heights) else 0;start=x
            while stack and stack[-1][1]>h:
                left,height=stack.pop();start=left
                if (x-left)*height>area:area=(x-left)*height;best=(left,y+1-height,x,y+1)
            if not stack or stack[-1][1]<h:stack.append((start,h))
    x0,y0,x1,y1=best
    assert not area or mask[y0:y1,x0:x1].all()
    return best


def analyze(directory):
    rows=[]
    for path in sorted(directory.glob('present*_meta.bin')):
        generation=int(path.name[7:12])
        if not 530<=generation<=570:continue
        raw=path.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(n)]
        rects=[];covered=np.zeros((192,256),dtype=bool);objects=[]
        for draw in reversed(draws):
            opaque=pixels(reference(dict(draws=[draw])))!=0;visible=opaque&~covered
            words=word_rows(opaque,draw).sum(axis=1)
            ideal=int(words[opaque.any(axis=1)&~visible.any(axis=1)].sum());safe=0
            for y,row in enumerate(opaque):
                xs=np.flatnonzero(row)
                if len(xs) and any(y0<=y<y1 and x0<=xs[0] and xs[-1]<x1 for x0,y0,x1,y1 in rects):safe+=int(words[y])
            objects.append(dict(asset=draw[4],width=draw[2],height=draw[3],words=int(words.sum()),idealHiddenRowWords=ideal,rectHiddenRowWords=safe))
            if draw[4] in (39,40,41) and draw[2]>=64:rects.append(largest_rectangle(opaque))
            covered|=opaque
        rows.append(dict(generation=generation,objects=objects))
    assert len(rows)==41
    totals={k:sum(o[k] for row in rows for o in row['objects']) for k in ('words','idealHiddenRowWords','rectHiddenRowWords')}
    return dict(source=str(directory),frames=rows,totals=totals,
        idealHiddenRowFraction=totals['idealHiddenRowWords']/totals['words'],
        rectHiddenRowFraction=totals['rectHiddenRowWords']/totals['words'],
        costModel='largest visible opaque rectangle per foreground explosion; setup/tests and changed row dispatch excluded',
        gameIntegrated=False,goal60fpsAchieved=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=analyze(args.directory);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:result[k] for k in ('totals','idealHiddenRowFraction','rectHiddenRowFraction')})
