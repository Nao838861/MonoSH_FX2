"""OAM/静的4bppを復号し、元の描画矩形の画素・反転・点滅と照合する。"""
import json
from pathlib import Path
import struct
import sys
from PIL import Image
from build_game import BUILD,GAME
from verify_game_pixels import is_obj

def object_pixels(vram,oam):
    out={}
    for i in reversed(range(16)):
        x,y,tile,attr=oam[i*4:i*4+4]
        high=(oam[512+i//4]>>(2*(i%4)))&3
        x|=(high&1)<<8
        if x>=256:x-=512
        assert not high&2,'unexpected large OBJ'
        tile|=(attr&1)<<8
        for screen_y in range(224):
            sy=(screen_y-y-1)&255
            if sy>=16:continue
            yy=15-sy if attr&128 else sy
            for dx in range(16):
                screen_x=x+dx
                if not 0<=screen_x<256:continue
                xx=15-dx if attr&64 else dx
                number=tile+(yy//8)*16+xx//8
                address=0xc000+number*32+(yy%8)*2
                bit=7-xx%8
                color=sum(((vram[address+(p//2)*16+(p%2)]>>bit)&1)<<p for p in range(4))
                if color:out[screen_x,screen_y]=(128+((attr>>1)&7)*16+color)
    return out

def reference(draw,meta):
    out={}
    items=[struct.unpack_from('<hh6B',draw,i*10) for i in range(meta['count'])]
    for d in sorted(items,key=lambda v:(v[7],-v[6])):
        if not is_obj(d):continue
        x,bottom,w,h,asset,flags,_,_=d
        if flags&128 and meta['logic']&1:continue
        image=Image.open(GAME/'assets/obj_color'/f'{asset:02d}.png')
        du=image.width*256//w;dv=image.height*256//h
        for dy in range(h):
            sy=((image.height*256-1-dy*dv) if flags&32 else dy*dv)>>8
            for dx in range(w):
                sx=((image.width*256-1-dx*du) if flags&16 else dx*du)>>8
                color=image.getpixel((sx,sy))
                if color==0:continue
                px=x-w//2+dx;py=bottom-h-7+dy
                if 0<=px<256 and 23<=py<203:out[px,py]=128+color
    return out

def verify(directory):
    vram=(GAME/'assets/ppu.bin').read_bytes()
    samples=[directory/('obj'+p.stem[5:]+'.bin') for p in sorted(directory.glob('frame[0-9]*.bin'))]
    assert samples,'missing OBJ snapshots'
    poses=set();flips=set();sizes=set();max_count=0
    for path in samples:
        n=path.stem[3:]
        draw=(directory/f'draw{n}.bin').read_bytes()
        meta=json.loads((directory/f'meta{n}.json').read_text())
        oam=(directory/f'oam{n}.bin').read_bytes()
        assert oam[:64]+oam[512:516]==path.read_bytes(),'OAM generation differs'
        actual={p:c for p,c in object_pixels(vram,oam).items() if 23<=p[1]<203}
        expected=reference(draw,meta)
        diff={p for p in actual.keys()|expected.keys() if actual.get(p)!=expected.get(p)}
        assert not diff,f'OBJ pixels differ: {n}: {len(diff)}, examples {sorted(diff)[:8]}'
        for i in range(meta['count']):
            d=struct.unpack_from('<hh6B',draw,i*10)
            if is_obj(d):
                if d[4]==10:sizes.add(d[2])
                else:poses.add(d[4]);flips.add(d[5]&48)
        max_count=max(max_count,sum(oam[i*4+1]!=240 for i in range(16)))
    if directory.name=='objects':
        assert poses=={9,*range(15,31)} and flips=={0,16,32,48}
        assert sizes==set(range(1,17))
        views=sorted(directory.glob('objview[0-9]*_oam.bin'))
        assert views,'missing final PPU OBJ captures'
        pixels=0;bank1=False;view_flips=set();colors=set()
        planned=json.loads((GAME/'assets/obj_color/palette.json').read_text())['rgb5']
        planned_words=[r|(g<<5)|(b<<10) for r,g,b in planned]
        assert (GAME/'assets/obj_palette.bin').read_bytes()==struct.pack('<16H',*planned_words)
        for path in views:
            oam=path.read_bytes()
            cgram=path.with_name(path.name.replace('_oam.bin','_cgram.bin')).read_bytes()
            palette=struct.unpack('<256H',cgram)
            assert list(palette[128:144])==planned_words,'PPU OBJ palette differs from requested colors'
            screen=Image.open(path.with_name(path.name.replace('_oam.bin','.png'))).convert('RGB')
            for (x,y),color in object_pixels(vram,oam).items():
                if 23<=y<203:
                    word=palette[color]
                    expected=tuple(((word>>s)&31)*8+(((word>>s)&31)>>2) for s in (0,5,10))
                    assert screen.getpixel((x,y+6))==expected,f'final PPU OBJ pixel differs: {path.name} {(x,y)}'
                    pixels+=1
                    colors.add(color-128)
            for i in range(16):
                if oam[i*4+1]!=240:
                    bank1|=bool(oam[i*4+3]&1)
                    view_flips.add(oam[i*4+3]&192)
        assert bank1 and view_flips=={0,64,128,192}
        expected_colors=set()
        for asset in [9,10,*range(15,31)]:
            with Image.open(GAME/'assets/obj_color'/f'{asset:02d}.png') as image:
                expected_colors.update(c for _,c in image.getcolors() if c)
        assert colors==expected_colors,f'player/bullet colors missing in actual PPU captures: {colors} / {expected_colors}'
        (directory/'objects_ppu.json').write_text(json.dumps({'screens':len(views),'checkedObjectPixels':pixels,
                    'secondChrTableSeen':bank1,'flips':sorted(view_flips),'opaquePaletteIndices':sorted(colors),
                    'objPaletteRgb5':planned},indent=2)+'\n')
        print(f'objects: final PPU {len(views)} screens/{pixels} OBJ pixels match, second CHR table and all flips checked')
    print(f'{directory.name}: {len(samples)} OBJ scenes match, max {max_count} OBJ, {len(poses)} poses/{len(flips)} flips/{len(sizes)} bullet sizes')

if __name__=='__main__':
    for name in sys.argv[1:] or ['play']:verify(BUILD/name)
