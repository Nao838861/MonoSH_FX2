"""PPU合成後のRGBを、FX・地面・独立二層遠景・空のHDMAと照合する。"""
import json
import re
from pathlib import Path
import struct
import sys
from PIL import Image
from build_game import BUILD, GAME
from verify_game_objects import object_pixels

def hdma(raw, size, lines=224, indirect=None):
    result=[];position=0;last=bytes(size)
    while len(result)<lines:
        count=raw[position];position+=1
        if not count:break
        source=raw;cursor=position
        if indirect:
            source,base=indirect;cursor=struct.unpack_from('<H',raw,position)[0]-base;position+=2
        for row in range(count&127 or 128):
            if row==0 or count&128:
                last=source[cursor:cursor+size];cursor+=size
                assert len(last)==size
            result.append(last)
        if not indirect:position=cursor
    return result+[last]*(lines-len(result))

def pixel(vram, layer, x, y, fx_map_base=0x8000):
    mapbase,chrbase,width=[(0x8000,0,32),(0xa000,0x4000,64),(0xb000,0x6000,64),(0x9000,0x6000,64)][layer]
    if layer==0:mapbase=fx_map_base
    x%=width*8;y%=256
    tx,ty=x//8,y//8
    address=mapbase+(tx//32)*0x800+(ty*32+tx%32)*2
    tile=struct.unpack_from('<H',vram,address)[0]
    xx=x&7;yy=y&7
    if tile&0x4000:xx=7-xx
    if tile&0x8000:yy=7-yy
    pos=chrbase+(tile&1023)*16+yy*2;bit=7-xx
    color=((vram[pos]>>bit)&1)|(((vram[pos+1]>>bit)&1)<<1)
    return ([32,64,96,0][layer]+((tile>>10)&7)*4+color) if color else None

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
        assert any(min(rgb(word))>220 for word in palette[96:128]),'white mountain ridge lost during quantization'
        objects=object_pixels(vram,data('oam'))
        v,h,far=[hdma(data(name),2) for name in ('v','h','far')]
        # VRAM一致だけでなく、原本の地上物と同じ投影・横移動を要求する。
        for physical in range(106+meta['offset'],205):
            span=100-meta['offset']
            source=127+((physical-104-meta['offset'])*80+span//2)//span
            assert struct.unpack('<H',v[physical])[0]==(source-physical)&65535
            assert struct.unpack('<H',h[physical])[0]==128+32*(source-127)*51//(64*80)
        c1,c3=[hdma(data(name),4) for name in ('c1','c3')]
        sky=hdma(data('sky'),4,indirect=(data('skycolors'),meta['skyBase']))
        assert meta['nearX']==meta['farX']*2 and all(struct.unpack('<H',row)[0]==meta['farX'] for row in far),'two BG scroll rates'
        # 実装をなぞるRGB参照だけでなく、ユーザー指摘の三条件を独立に要求する。
        horizon=106+meta['offset']
        assert meta['farY']==21-meta['offset'],'scenery must move down by two pixels'
        for x in range(512):
            for y in range(horizon,horizon+8):
                assert pixel(vram,3,x,y+meta['farY']) is None,'forest occludes ground'
            for y in range(horizon-7,horizon):
                assert pixel(vram,2,x,y+meta['farY']) is not None,'hole in purple mountain base'
            # スクロール表の隠した2行は、本当に透明な地面タイルを読む。
            for physical in range(horizon-2,horizon):
                vo=struct.unpack('<H',v[physical])[0]
                assert pixel(vram,1,x,physical+vo) is None,'ground top two rows not clipped'
        # 山と森林の上端・下端を含む、元画像の全不透明画素を復元する。
        for name,layer in [('near',3),('far',2)]:
            original=Image.open(GAME/'assets/recorded_effects'/f'{name}_source.png').convert('RGBA')
            for y in range(108,130):
                for x in range(512):
                    opaque=bool(original.getpixel((x,y))[3])
                    assert (pixel(vram,layer,x,y) is not None)==opaque,('scenery restoration',name,x,y)
        # 山に遮られない空色列は原作の130..150行と同じ長さ・RGB5を持つ。
        reference=json.loads((GAME/'assets/recorded_effects/source.json').read_text(encoding='utf-8'))['skyRgb5']
        start=104+meta['offset']-29
        for row,(r,g,b) in enumerate(reference):
            assert struct.unpack('<BBH',sky[start-1+row])[2]==r|(g<<5)|(b<<10),'sky gradient extent/color'
        image=Image.open(base.with_suffix('.png')).convert('RGB')
        greens={image.getpixel((x,y)) for y in range(image.height) for x in range(image.width)
                if image.getpixel((x,y))[1]>max(image.getpixel((x,y))[0],image.getpixel((x,y))[2])}
        # ユーザー指定の四つのRGBに最も近いRGB5。明度順。
        words=[r+(g<<5)+(b<<10) for r,g,b in [(14,23,13),(16,25,16),(18,27,18),(19,29,20)]]
        assert {rgb(word) for word in words}.issubset(greens),'ground colors missing'
        pairs=set()
        for y in range(horizon+1,203):
            bright=struct.unpack('<BBH',c1[y-1])[2]
            dark=struct.unpack('<BBH',c3[y-1])[2]
            assert bright in words[2:] and dark in words[:2],'depth column brightness group switched'
            pairs.add((dark,bright))
        assert pairs=={(words[0],words[3]),(words[1],words[2])},pairs
        expected=Image.new('RGB',image.size)
        for y in range(224):
            line=max(0,y-1)  # HDMA first data is used by scanline 1.
            vo,ho,fo=[struct.unpack('<H',table[line])[0] for table in (v,h,far)]
            for table in (c1,c3,sky):
                address,address2,color=struct.unpack('<BBH',table[line]);assert address==address2
                palette[address]=color
            for x in range(256):
                color=(0,0,0)
                if 23<=y<203:
                    index=objects.get((x,y))
                    if index is None:index=pixel(vram,0,x,y-13,meta.get('fxMapBase',0x8000))
                    if index is None:index=pixel(vram,3,x+meta['nearX'],y+meta['farY'])
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
    print(f'{len(samples)} camera heights: BG1/BG2/BG3/BG4 + sky HDMA final RGB matches')

if __name__=='__main__':verify(BUILD/(sys.argv[1] if len(sys.argv)>1 else 'display'))
