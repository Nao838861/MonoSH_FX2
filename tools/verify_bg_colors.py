"""CPUの属性を独立したソート・UV・clip参照と全タイル/CGRAMで照合する。"""
import json
import struct
from pathlib import Path
from PIL import Image
from build_game import BUILD,GAME

def reference(draw,logic):
    cells=(GAME/'assets/bg_color/cells.bin').read_bytes()
    offsets=struct.unpack('<44H',(GAME/'assets/bg_color/offsets.bin').read_bytes())
    high=bytearray(0x20|((x*24+y)>>8) for y in range(24) for x in range(32))
    objects=list(struct.iter_unpack('<hh6B',draw));objects.sort(key=lambda d:(d[7],-d[6]))
    for cx,bottom,w,h,asset,flags,z,priority in objects:
        if flags&128 and logic&1:continue
        if priority==2 and (asset in [9,10,*range(15,31)]):continue
        if not w or not h:continue
        left=cx-w//2;top=bottom-h-20
        right=left+w;end=top+h
        if right<=0 or end<=0 or left>=256 or top>=192:continue
        aw,ah=Image.open(GAME/'assets'/f'{asset:02d}.png').size
        du=aw*256//w;dv=ah*256//h
        for ty in range(max(0,top)//8,(min(192,end)-1)//8+1):
            sy=min(h-1,max(0,ty*8+4-top))*dv
            if flags&32:sy=ah*256-1-sy
            for tx in range(max(0,left)//8,(min(256,right)-1)//8+1):
                sx=min(w-1,max(0,tx*8+4-left))*du
                if flags&16:sx=aw*256-1-sx
                cell=(sy>>11)*16+(sx>>11)
                value=cells[offsets[asset]+cell//2]
                pal=(value>>(4*(cell&1)))&15
                if pal!=15:high[ty*32+tx]=((tx*24+ty)>>8)|0x20|pal<<2
    return high

def main():
    directory=BUILD/'color';rows=[];cases=set();modes=set()
    color=(GAME/'assets/bg_color/palette.bin').read_bytes()
    mono=struct.pack('<4H',0,0,0x7fff,0x7fff)*8
    for path in sorted(directory.glob('color[0-9]*.json')):
        meta=json.loads(path.read_text());base=path.with_suffix('')
        data=lambda n:Path(str(base)+'_'+n+'.bin').read_bytes()
        expected=reference(data('draw'),meta['logic']);actual=data('ram')
        assert actual==expected,(path.name,'CPU map',[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:8])
        vram=data('map')
        for i in range(768):
            x=i%32;y=i//32
            assert vram[i*2]==(x*24+y)&255,(path.name,'tile low',i)
            assert vram[i*2+1]==expected[i],(path.name,'VRAM high',i)
        assert data('cgram')==(color if meta['mode'] else mono),(path.name,'CGRAM')
        assert meta['line']<=21 or meta['line']>=203,(path.name,'DMA deadline')
        rows.append(meta);cases.add(meta['case']);modes.add(meta['mode'])
    assert cases==set(range(8)),cases
    assert modes=={0,1},modes
    transitions=[rows[0]['mode']]+[b['mode'] for a,b in zip(rows,rows[1:]) if a['mode']!=b['mode']]
    assert transitions==[1,0,1],transitions
    result={'samples':len(rows),'cases':sorted(cases),'transitions':transitions,'tiles_checked':len(rows)*768,
        'palette_bytes_checked':len(rows)*64,'monochromeOpaqueRgb5':[[0,0,0],[31,31,31],[31,31,31]],
        'map_errors':0,'vram_errors':0,'palette_errors':0,'physical_hardware':False}
    (directory/'color_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)

if __name__=='__main__':main()
