"""実測packetから3面VRAMの先行転送の上限を調べる。実機速度の合格判定ではない。"""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from build_sa1_probe import ART
from build_sa1_game import BUILD,BASE


def frames(path):
    raw=path.read_bytes();offset=0
    while offset<len(raw):
        far,near,ground,count=struct.unpack_from('<4H',raw,offset);offset+=8
        draws=[struct.unpack_from('<hh6B',raw,offset+i*10)for i in range(count)];offset+=count*10
        yield far,near,ground,draws
    assert offset==len(raw)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('scenario');args=parser.parse_args()
    folder=BUILD/args.scenario
    rgb=np.array(json.loads((ART/'palette.json').read_text())['rgb5'],np.int32);rgb=rgb*8+(rgb>>2)
    images={}
    for p in ART.glob('*.png'):
        a=np.array(Image.open(p).convert('RGBA'))
        images[p.stem]=np.where(a[:,:,3]>=128,1+((a[:,:,:3,None].astype(np.int32)-rgb[1:].T[None,None,:,:])**2).sum(axis=2).argmin(axis=2),0).astype(np.uint8)
    source=(BASE/'assets4/background4.bin').read_bytes();strip=np.frombuffer(source[0x8000:0x8000+9*512],np.uint8).reshape(9,512)
    entries=[]
    for generation,(far,near,ground,draws)in enumerate(frames(folder/'packet_trace.bin'),1):
        pix=np.zeros((192,256),np.uint8);fine=near&7;left=(112-fine)&~3;right=(163-fine)&~3
        layer=strip[:,(np.arange(256)+near)&511];top=82+ground;y0=max(0,top);y1=min(192,top+9)
        if y0<y1:pix[y0:y1,left:right]=layer[y0-top:y1-top,left:right]
        for center,bottom,w,h,asset,flags,*_ in draws:
            if not w or not h:continue
            variant=flags&3;key=f'{asset:02d}_hue{variant}'if variant and asset in(6,7,8,31,37)else f'{asset:02d}'
            a=images[key];ah,aw=a.shape;u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
            if flags&16:u=aw*256-1-u
            if flags&32:v=ah*256-1-v
            left=center-w//2;top=bottom-h-20;x0=max(0,left);x1=min(256,left+w);y0=max(0,top);y1=min(192,top+h)
            if x0<x1 and y0<y1:
                patch=a[(v[y0-top:y1-top]>>8)[:,None],u[x0-left:x1-left]>>8];dest=pix[y0:y1,x0:x1];dest[patch!=0]=patch[patch!=0]
        tiles=pix.reshape(24,8,32,8).transpose(0,2,1,3).reshape(768,64)[32:]
        count=int(np.count_nonzero(np.any(tiles,axis=1)))
        # 透明文字32B、表示用map1472B、2DMAの管理を仮定する楽観的な費用。
        byte_count=(count+1)*32+1472
        entries.append(dict(generation=generation,tiles=count,bytes=byte_count,cost=byte_count*1.0390625+600))
    models=[]
    for pages in (2,3,4):
        queue=[];next_job=0;misses=[];budget=12100
        # 最初のpages-1枚を転送済みとして開始する。各fieldで1枚を要求する。
        for i in range(pages-1):queue.append(0);next_job+=1
        for generation in range(1,len(entries)+1):
            if not queue or queue[0]>0:misses.append(generation)
            else:queue.pop(0)
            available=budget
            while available>0:
                if len(queue)<pages-1 and next_job<len(entries):queue.append(entries[next_job]['cost']);next_job+=1
                pending=next((i for i,n in enumerate(queue)if n>0),None)
                if pending is None:break
                used=min(available,queue[pending]);queue[pending]-=used;available-=used
        models.append(dict(pages=pages,misses=len(misses),firstMisses=misses[:30]))
    result=dict(scenario=args.scenario,frames=len(entries),maxTiles=max(x['tiles']for x in entries),maxBytes=max(x['bytes']for x in entries),models=models,heavy=[x for x in entries if x['bytes']>11000])
    (folder/'vram_prefetch_model.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items()if k!='heavy'});print('heavy',result['heavy'][:15])


if __name__=='__main__':main()
