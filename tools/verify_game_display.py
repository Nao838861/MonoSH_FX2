"""PPU合成後のRGBを、BG2一対一・BG3行別投影・BG4独立遠景と照合する。"""
import json
import re
from pathlib import Path
import struct
import sys
from PIL import Image
from build_game import BUILD, GAME
from verify_game_objects import object_pixels

def hdma(raw, size, lines=224):
    result=[];position=0;last=bytes(size)
    while len(result)<lines:
        count=raw[position];position+=1
        if not count:break
        for row in range(count&127 or 128):
            if row==0 or count&128:
                last=raw[position:position+size];position+=size
                assert len(last)==size
            result.append(last)
    return result+[last]*(lines-len(result))

def pixel(vram, layer, x, y):
    mapbase,chrbase,width=[(0x8000,0,32),(0xa000,0x4000,64),(0xb000,0x6000,32)][layer]
    x%=width*8;y%=256
    tx,ty=x//8,y//8
    address=mapbase+(tx//32)*0x800+(ty*32+tx%32)*2
    tile=struct.unpack_from('<H',vram,address)[0]
    xx=x&7;yy=y&7
    if tile&0x4000:xx=7-xx
    if tile&0x8000:yy=7-yy
    pos=chrbase+(tile&1023)*16+yy*2;bit=7-xx
    color=((vram[pos]>>bit)&1)|(((vram[pos+1]>>bit)&1)<<1)
    return (32+layer*32+((tile>>10)&7)*4+color) if color else None

def rgb(word):
    # Mesen's 5-bit RGB expansion uses bit replication.
    return tuple(((word>>shift)&31)*8+(((word>>shift)&31)>>2) for shift in (0,5,10))

def verify(directory):
    def frozen_array(path,name):
        body=re.search(name+r'\[\d+\] = \{(.*?)\}',path.read_text(),re.S)[1]
        return [int(n,0) for n in re.findall(r'0x[\da-fA-F]+|\b\d+\b',body)]
    tree=frozen_array(GAME/'upstream/monosh_stage_data.c','stage_tree0_geometry')
    scales=frozen_array(GAME/'upstream/monosh_projection.c','full_scale')
    depth_text=(GAME/'upstream/monosh_projection_data.asm').read_text().split('_monosh_ground_depth_rows:',1)[1]
    depths=[]
    for line in depth_text.splitlines():
        if line.strip().startswith('defb'):depths.extend(map(int,line.split('defb')[1].strip().split(',')))
        elif depths and line.strip() and not line.lstrip().startswith(';'):break
    assert len(depths)==65*81
    samples=sorted(directory.glob('display[0-9]*.json'))
    assert len(samples)>=3,'missing camera samples'
    offsets=[]
    for path in samples:
        base=path.with_suffix('');meta=json.loads(path.read_text());offsets.append(meta['offset'])
        data=lambda name:Path(str(base)+'_'+name+'.bin').read_bytes()
        vram=data('vram');cgram=data('cgram');palette=list(struct.unpack('<256H',cgram))
        objects=object_pixels(vram,data('oam'))
        v,h,far=[hdma(data(name),2) for name in ('v','h','far')]
        # VRAM一致だけでなく、原本の地上物と同じ投影・横移動を要求する。
        for physical in range(104+meta['offset'],205):
            span=100-meta['offset']
            source=127+((physical-104-meta['offset'])*80+span//2)//span
            assert struct.unpack('<H',v[physical])[0]==(source-physical)&65535
            assert struct.unpack('<H',h[physical])[0]==128+32*(source-127)*51//(64*80)
        c1,c3=[hdma(data(name),4) for name in ('c1','c3')]
        image=Image.open(base.with_suffix('.png')).convert('RGB')
        greens={image.getpixel((x,y)) for y in range(image.height) for x in range(image.width)
                if image.getpixel((x,y))[1]>max(image.getpixel((x,y))[0],image.getpixel((x,y))[2])}
        # ユーザー指定の四つのRGBに最も近いRGB5。明度順。
        words=[r+(g<<5)+(b<<10) for r,g,b in [(14,23,14),(16,25,15),(18,27,18),(19,29,20)]]
        assert greens=={rgb(word) for word in words},greens
        pairs=set()
        for y in range(104+meta['offset']+1,203):
            bright=struct.unpack('<BBH',c1[y-1])[2]
            dark=struct.unpack('<BBH',c3[y-1])[2]
            assert bright in words[2:] and dark in words[:2],'depth column brightness group switched'
            pairs.add((dark,bright))
        assert pairs=={(words[0],words[3]),(words[1],words[2])},pairs
        assert palette[0]==24+(14<<5)+(31<<10),'purple sky'
        expected=Image.new('RGB',image.size)
        for y in range(224):
            line=max(0,y-1)  # HDMA first data is used by scanline 1.
            vo,ho,fo=[struct.unpack('<H',table[line])[0] for table in (v,h,far)]
            for table in (c1,c3):
                address,address2,color=struct.unpack('<BBH',table[line]);assert address==address2
                palette[address]=color
            for x in range(256):
                color=(0,0,0)
                if 23<=y<203:
                    index=objects.get((x,y))
                    if index is None:index=pixel(vram,0,x,y-13)
                    if index is None:index=pixel(vram,1,x+ho,y+vo)
                    if index is None:index=pixel(vram,2,x+fo,y+meta['farY'])
                    color=rgb(palette[index or 0])
                # Mesen's 239-line buffer includes its six-line top overscan border.
                expected.putpixel((x,y+6),color)
        expected.save(Path(str(base)+'_expected.png'))
        mismatch=sum(image.getpixel((x,y))!=expected.getpixel((x,y)) for y in range(image.height) for x in range(256))
        if mismatch:
            rows=[sum(image.getpixel((x,y))!=expected.getpixel((x,y)) for x in range(256)) for y in range(image.height)]
            print(base.name,'different RGB pixels',mismatch,'rows',[(i,n) for i,n in enumerate(rows) if n][:12])
        assert not mismatch,base
    assert offsets==[0,32,64],offsets
    print(f'{len(samples)} camera heights: BG2/BG3/BG4 final RGB matches')

if __name__=='__main__':verify(BUILD/(sys.argv[1] if len(sys.argv)>1 else 'display'))
