"""採取した同一packetを一面・左面・右面で再生し、描画費を比較する。"""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from test_sa1_probe import reference


def load(directory):
    jobs=[];sources=[]
    for p in sorted(directory.glob('present*_meta.bin')):
        g=int(p.name[7:12])
        if not 530<=g<=570:continue
        raw=p.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(n)]
        sources.append(dict(generation=g,metadataSha256=hashlib.sha256(raw).hexdigest(),draws=draws))
        jobs.append(dict(generation=g,mode='baseline',draws=draws))
        for lo,mode in ((0,'left'),(128,'right')):
            objects=[]
            for d in draws:
                x,b,w,h,a,f,*_=d;left=x-w//2
                # 寸法全体で保守的に選択。透明部分しか掛からない物体も元の描画器へ渡す。
                if left+w>lo and left<lo+128:objects.append([x+64-lo,*d[1:]])
            jobs.append(dict(generation=g,mode=mode,draws=objects))
    assert len(sources)==41 and len(jobs)==123
    return jobs,sources


def verify(dest,jobs,summary):
    paths=sorted(dest.glob('present*_meta.bin'))
    assert len(paths)>=370
    encoded=[b''.join(struct.pack('<hh6B',*d) for d in j['draws']) for j in jobs]
    # 起動直後はpacketがfixture hookより先に取得される。以後の全列との一致で位相を確定する。
    candidates=[offset for offset in range(len(jobs)) if all(p.read_bytes()[10:]==encoded[(offset+i)%len(jobs)] for i,p in enumerate(paths[1:10]))]
    assert len(candidates)==1,candidates
    offset=candidates[0]
    pairs=[];modes=set();generations=set()
    for index,path in enumerate(paths):
        if index==0:continue # 通常の初回画像は共通の全画素照合で確認済み。
        job=jobs[(index-1+offset)%len(jobs)]
        raw=path.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        expected=encoded[(index-1+offset)%len(jobs)]
        assert n==len(job['draws']) and raw[10:]==expected,(path.name,job['mode'],job['generation'])
        modes.add(job['mode']);generations.add(job['generation'])
        if job['mode']!='baseline' or index+2>=len(paths):continue
        images=[]
        for j,p in enumerate(paths[index:index+3]):
            source=jobs[(index-1+j+offset)%len(jobs)]
            sprite=np.frombuffer(reference(dict(draws=source['draws'])),np.uint8).reshape(192,128)
            sprite=np.stack((sprite&15,sprite>>4),axis=2).reshape(192,256)
            packed=np.frombuffer(p.with_name(p.name.replace('_meta.bin','_fb.bin')).read_bytes(),np.uint8).reshape(192,128)
            actual=np.stack((packed&15,packed>>4),axis=2).reshape(192,256)
            # rawには地面の中央stripも含む。その位置は今回のprobeでは移さない。
            # 共通PPU checkerはstripも含む各画面の全画素を検証し、ここではspriteを再合成する。
            assert np.array_equal(actual[sprite!=0],sprite[sprite!=0])
            images.append(np.where(sprite!=0,actual,0))
        assert np.array_equal(images[0],np.concatenate((images[1][:,64:192],images[2][:,64:192]),axis=1))
        timings=summary['sa1Jobs'][index:index+3]
        assert len(timings)==3
        pairs.append(dict(generation=job['generation'],cycle=(index-1+offset)//len(jobs),
            **{key:dict(baseline=timings[0][key],left=timings[1][key],right=timings[2][key],
                splitSum=timings[1][key]+timings[2][key]) for key in ('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')}))
    assert modes=={'baseline','left','right'} and generations==set(range(530,571))
    assert len(pairs)>=123
    sums={key:{mode:sum(p[key][mode] for p in pairs) for mode in ('baseline','splitSum')} for key in ('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')}
    return dict(sourceGenerations=41,fixtureJobs=len(paths)-1,pairedSpriteReconstructionChecks=len(pairs),
        firstReplayJobIndex=offset,allSubsequentPacketOrderVerified=True,
        gameIntegrated=False,concurrentTwoHalfBuffersTested=False,originalGroundStripPositionRetained=True,
        hostSpriteDrawingUsed=False,sourceCoordinatesChangedForReplay=True,
        timingIncludesIndependentIrqAndPpuContention=True,
        goal60fpsAchieved=False,totals=sums,pairs=pairs)
