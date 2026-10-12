"""128pxずつの可視域と左右64px余白を持つ二面方式の費用を算定する。

実装・速度測定ではない。通常の256px幅CC1を二面へ使えるようにし、
512px幅から中央をコピーし直す旧方式との違いと重複描画量を確認する。
"""
import argparse,hashlib,json,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from sa1_left_hints import physical
from test_sa1_probe import reference


def analyze(directory,rom_path,boundary=128):
    assert boundary in (64,128,192)
    rom=rom_path.read_bytes()
    def u16(p):return struct.unpack_from('<H',rom,p)[0]
    def pointer(p):return physical(int.from_bytes(rom[p:p+3],'little'))
    @lru_cache(None)
    def geometry(a,w,h):
        p=0x7f0000+u16(0x7f0000+a*512+w*2)
        for i in range(rom[p]):
            q=p+1+i*10
            if rom[q]==h:return q
        raise AssertionError((a,w,h))
    @lru_cache(None)
    def row_bytes(a,w,h,phase,parity,first,last):
        if a in (6,7,8,37):return 0 # 弾は圧縮データと専用worker。native命令量に混ぜない。
        q=geometry(a,w,h);desc=0x7f0000+u16(q+1)
        chain=pointer(desc+(phase*2+parity)*3)
        return sum(11+rom[pointer(chain+y*11+8)-2] for y in range(first,last))
    def bounds(draw):
        x,b,w,h,a,f,*_=draw
        q=geometry(a,w,h);l,t,r,bt=rom[q+3:q+7]
        if f&16:l,r=w-r,w-l
        if f&32:t,bt=h-bt,h-t
        return l,t,r,bt
    def selected(draw,lo,hi,shift):
        x,b,w,h,a,f,*_=draw;left=x-w//2;top=b-h-20
        l,t,r,bt=bounds(draw)
        if left+r<=lo or left+l>=hi or top+bt<=0 or top+t>=192:return None
        return [x+shift,*draw[1:]]
    def measure(draw):
        x,b,w,h,a,f,*_=draw;left=x-w//2;top=b-h-20
        l,t,r,bt=bounds(draw)
        first=max(0,-top);last=min(h,192-top)
        assert first<last
        phase=(f&3) if a in (6,7,8,31,37) else 0
        assert a in (6,7,8,37) or not f&48, 'native flip needs a separate instruction-volume model'
        return dict(objects=1,nativeBytes=row_bytes(a,w,h,phase,left&1,first,last),
            leftClipped=int(left+l<0),rightClipped=int(left+r>256),
            bullets=int(a in (6,7,8,37)))
    raw=(directory/'packet_trace.bin').read_bytes();offset=0;frames=[];index=0
    while offset<len(raw):
        assert offset+8<=len(raw)
        n=struct.unpack_from('<H',raw,offset+6)[0];end=offset+8+n*10
        assert end<=len(raw)
        draws=[list(struct.unpack_from('<hh6B',raw,offset+8+i*10)) for i in range(n)]
        offset=end;index+=1
        base=[d for d in draws if selected(d,0,256,0) is not None]
        halves=[[d for o in draws if (d:=selected(o,lo,hi,shift)) is not None] for lo,hi,shift in ((0,boundary,64),(boundary,256,-64))]
        costs=[]
        for objects in (base,halves[0]+halves[1]):
            total={k:0 for k in ('objects','nativeBytes','leftClipped','rightClipped','bullets')}
            for d in objects:
                for k,v in measure(d).items():total[k]+=v
            costs.append(total)
        checked=False
        if 530<=index<=570:
            original=np.frombuffer(reference(dict(draws=draws)),dtype=np.uint8).reshape(192,128)
            parts=[np.frombuffer(reference(dict(draws=d)),dtype=np.uint8).reshape(192,128)[:,lo:hi] for d,lo,hi in zip(halves,(32,boundary//2-32),(32+boundary//2,96))]
            assert np.array_equal(original,np.concatenate(parts,axis=1)),index
            checked=True
        frames.append(dict(generation=index,baseline=costs[0],split=costs[1],hostPixelReconstructionChecked=checked))
    totals={mode:{k:sum(f[mode][k] for f in frames) for k in frames[0][mode]} for mode in ('baseline','split')}
    assert sum(f['hostPixelReconstructionChecked'] for f in frames)==41
    return dict(source=str(directory),sourceRomSha256=hashlib.sha256(rom).hexdigest(),frames=frames,totals=totals,
        nativeByteRatio=totals['split']['nativeBytes']/totals['baseline']['nativeBytes'],
        hostPixelReconstructionChecks=41,framebufferBytesPerGameFrame=2*192*128,
        threeFramebufferPairsBytes=3*2*192*128,
        cC1WidthPixels=256,splitBoundary=boundary,visiblePixelsPerViewport=[boundary,256-boundary],
        viewportBiases=[64,-64],viewportHorizontalPadding=[[64,192-boundary],[boundary-64,64]],
        **({'visiblePixelsPerHalf':128,'horizontalPaddingPixelsPerSide':64} if boundary==128 else {}),
        estimatedTiming=False,gameIntegrated=False,hardwareTransferVerified=False,goal60fpsAchieved=False,
        exclusions='nativeBytes counts visible rows only; excludes bottom slack, compressed bullet workers, dispatch/clear/dirty, CC1/PPU and queue effects; no fps inferred')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('rom',type=Path);ap.add_argument('--boundary',type=int,choices=[64,128,192],default=128);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=analyze(args.directory,args.rom,args.boundary);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:result[k] for k in ('totals','nativeByteRatio','hostPixelReconstructionChecks')})
