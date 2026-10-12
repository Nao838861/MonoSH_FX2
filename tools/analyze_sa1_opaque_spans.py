"""事前保持できる不透明spanで、奥のnative wordを省く上限を測る。"""
import argparse,json,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from analyze_sa1_occlusion import pixels,word_rows
from test_sa1_probe import reference,ART


@lru_cache(maxsize=None)
def spans(asset,w,h,flags,maximum):
    variant=flags&3
    name=f'{asset:02d}'+(f'_hue{variant}' if variant and asset in (6,7,8,31,37) else '')+'.png'
    alpha=np.asarray(Image.open(ART/name).convert('RGBA'))[:,:,3]>=128;ah,aw=alpha.shape
    u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
    if flags&16:u=aw*256-1-u
    if flags&32:v=ah*256-1-v
    scaled=alpha[v>>8][:,u>>8];result=[]
    for row in scaled:
        edges=np.diff(np.pad(row.astype(np.int8),(1,1)))
        runs=list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
        selected=sorted(runs,key=lambda pair:(-(pair[1]-pair[0]),pair[0]))[:maximum]
        for left,right in selected:assert row[left:right].all()
        result.append(tuple((int(left),int(right)) for left,right in selected))
    return tuple(result)


def analyze(directory,maximum):
    frames=[]
    for path in sorted(directory.glob('present*_meta.bin')):
        generation=int(path.name[7:12])
        if not 530<=generation<=570:continue
        raw=path.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(n)]
        expected=pixels(reference(dict(draws=draws)))
        actual=pixels(path.with_name(path.name.replace('_meta.bin','_fb.bin')).read_bytes())
        assert np.array_equal(expected[expected!=0],actual[expected!=0])
        covered=np.zeros((192,256),dtype=bool);span_cover=covered.copy();objects=[];fronts=[];culled=[]
        for draw in reversed(draws):
            x,bottom,w,h,asset,flags,*_=draw;opaque=pixels(reference(dict(draws=[draw])))!=0
            active=word_rows(opaque,draw)
            hidden=active&~word_rows(opaque&~covered,draw)
            span_hidden=active&~word_rows(opaque&~span_cover,draw)
            assert not np.any(span_cover&~covered) and not np.any(span_hidden&~hidden)
            phase=((x-w//2)//2*2)%4
            candidates=[]
            for front,layer in fronts:
                complete=np.roll(layer,-phase,axis=1).reshape(192,64,4).all(axis=2)
                removed=active&complete
                fx,fb,fw,fh,*_=front;fl=fx-fw//2;ft=fb-fh-20;left=x-w//2;top=bottom-h-20
                area=max(0,min(left+w,fl+fw)-max(left,fl))*max(0,min(top+h,ft+fh)-max(top,ft))
                candidates.append((int(removed.sum()),front,removed,area))
            best=max(candidates,key=lambda c:c[0]) if candidates else (0,None,np.zeros_like(active),0)
            cheap=max(candidates,key=lambda c:c[3]) if candidates else best
            cheap_rows=active.any(axis=1)&~(active&~cheap[2]).any(axis=1)
            # 現在のnative順の先頭だけを省く方式ならprefixコピーが要らない。
            # roll後のword列をspriteのleft byteから並べ直し、viewport wrapを先頭扱いしない。
            first_word=(((x-w//2)//2*2-phase)//4)%64
            aa=np.roll(active,-first_word,axis=1);hh=np.roll(cheap[2],-first_word,axis=1)
            leading=aa&~np.maximum.accumulate(aa&~hh,axis=1)
            trailing=(aa[:,::-1]&~np.maximum.accumulate((aa&~hh)[:,::-1],axis=1))[:,::-1]
            fixed=trailing if asset in (40,41) and w>=91 else leading
            eligible_fragment=asset in (39,40,41) and w<91 and x-w//2>=0 and x-w//2+w<=256 and not flags
            eligible_left=asset==39 and w>=79 and x-w//2<0
            eligible_right=asset in (40,41) and x-w//2>=0 and x-w//2+w>256
            objects.append(dict(asset=asset,width=w,height=h,words=int(active.sum()),idealHiddenWords=int(hidden.sum()),spanHiddenWords=int(span_hidden.sum()),
                singleFrontFullWordHidden=best[0],existingHelperEligible=bool(eligible_left or (eligible_right and w>=91)),
                extendedHelperEligible=bool(eligible_left or (eligible_right and w>=76)),fragmentEligible=eligible_fragment,
                bboxSelectedHiddenWords=cheap[0],bboxSelectedHiddenWholeRowWords=int(active[cheap_rows].sum()),
                bboxSelectedHiddenWholeRows=int(cheap_rows.sum()),bboxSelectedHiddenRowRuns=int(np.count_nonzero(np.diff(np.pad(cheap_rows.astype(np.int8),(1,1)))==1))))
            objects[-1].update(noCopyLeadingWordsFixedDirection=int(fixed.sum()),
                noCopyLeadingWordsBestObjectDirection=max(int(leading.sum()),int(trailing.sum())))
            assert not np.any(fixed&~hh)
            removed=np.roll(np.repeat(best[2][:,:,None],4,axis=2).reshape(192,256),phase,axis=1)
            assert not np.any(removed&opaque&~covered)
            color=pixels(reference(dict(draws=[draw]))).copy();color[removed]=0;culled.append(color)
            if asset in (39,40,41) and w>=64:
                layer=np.zeros_like(span_cover)
                left=x-w//2;top=bottom-h-20
                for row,runs in enumerate(spans(asset,w,h,flags,maximum)):
                    sy=top+row
                    if not 0<=sy<192:continue
                    for a,b in runs:
                        x0=max(0,left+a);x1=min(256,left+b)
                        if x0<x1:
                            assert opaque[sy,x0:x1].all()
                            span_cover[sy,x0:x1]=True
                            layer[sy,x0:x1]=True
                fronts.append((draw,layer))
            covered|=opaque
        recomposed=np.zeros((192,256),dtype=np.uint8)
        for color in reversed(culled):recomposed[color!=0]=color[color!=0]
        assert np.array_equal(recomposed,expected), 'word culling changed final sprite pixels'
        frames.append(dict(generation=generation,objects=objects))
    assert len(frames)==41
    totals={k:sum(o[k] for f in frames for o in f['objects']) for k in ('words','idealHiddenWords','spanHiddenWords','singleFrontFullWordHidden','bboxSelectedHiddenWords','bboxSelectedHiddenWholeRowWords','bboxSelectedHiddenWholeRows','bboxSelectedHiddenRowRuns','noCopyLeadingWordsFixedDirection','noCopyLeadingWordsBestObjectDirection')}
    for field in ('existingHelperEligible','extendedHelperEligible'):
        totals[field+'HiddenWords']=sum(o['singleFrontFullWordHidden'] for f in frames for o in f['objects'] if o[field])
    totals['fragmentEligibleHiddenWords']=sum(o['bboxSelectedHiddenWords'] for f in frames for o in f['objects'] if o['fragmentEligible'])
    return dict(source=str(directory),maximumSpansPerRow=maximum,frames=frames,totals=totals,
        spanHiddenWordFraction=totals['spanHiddenWords']/totals['words'],
        costModel='precomputed local opaque spans on foreground explosions only; setup/tests/fragment execution excluded',
        gameIntegrated=False,goal60fpsAchieved=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    results=[analyze(args.directory,n) for n in (1,2)]
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(cases=results),indent=2)+'\n')
    for r in results:print({k:r[k] for k in ('maximumSpansPerRow','totals','spanHiddenWordFraction')})
