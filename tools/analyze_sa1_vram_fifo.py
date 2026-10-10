"""実測済みのタイル数から可変長VRAM FIFOの容量とCHR参照範囲を調べる。"""
import argparse,json,struct
from pathlib import Path

VRAM_END=0xbc20
VRAM_GAP=0x10000-VRAM_END


def allocation(write, size):
    assert write%32==size%32==0 and 0<size<=352*32
    base=write&~0x1fff
    virtual_end=write+size+(VRAM_GAP if write+size>VRAM_END else 0)
    padding=0
    if virtual_end-base>0x8000:
        padding=VRAM_END-write
        write=base=0
    end=(write+size)%VRAM_END
    for offset in range(0,size,32):
        physical=(write+offset)%VRAM_END
        tile=((physical-base)&65535)//32
        assert tile<1024 and ((base+tile*32)&65535)==physical
    return dict(start=write,base=base,end=end,bytes=size,cost=size+padding,padding=padding)


def analyze(directory):
    frames=[]
    for path in sorted(directory.glob('present*_meta.bin')):
        generation=int(path.name[7:12])
        if not 530<=generation<=570:continue
        page=struct.unpack_from('<H',path.read_bytes(),8)[0]*2
        vram=(directory/(path.name[:-9]+'_vram.bin')).read_bytes()
        entries=struct.unpack_from('<736H',vram,0xc040)
        parity=128*((page//0x3000)&1)
        count=max((entry&1023)-parity for entry in entries)
        assert 0<=count<=351
        frames.append(dict(generation=generation,tiles=count,bytes=(count+1)*32))
    assert len(frames)==41
    for size in {frame['bytes'] for frame in frames}:
        for write in range(0,VRAM_END,32):allocation(write,size)
    # 常に未来の全データが即座に用意できる楽観的容量試算。時間は扱わない。
    queue=[];write=used=read=0;rows=[]
    for index,frame in enumerate(frames):
        while read<len(frames):
            item=allocation(write,frames[read]['bytes'])
            if used+item['cost']>VRAM_END:break
            queue.append(item);used+=item['cost'];write=item['end'];read+=1
        rows.append(dict(**frame,readyIncludingFront=len(queue),usedBytes=used))
        item=queue.pop(0);used-=item['cost']
        if queue and queue[0]['padding']:
            padding=queue[0]['padding']
            queue[0]['cost']-=padding;queue[0]['padding']=0;used-=padding
    return dict(source=str(directory),vramEnd=VRAM_END,layout='fixed-map static assets; maps retained outside VRAM',
        scope='capacity and tile-index bounds only; excludes rendering, map relocation/copy and DMA time',frames=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=analyze(args.directory);text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
