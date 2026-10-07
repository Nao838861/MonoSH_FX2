"""録画の二層遠景をMode0の2bpp BGとRGB5パレットへ変換する。"""
import itertools
import json
import struct
import numpy as np
from PIL import Image
from build_ground import GAME

def build():
    assets=GAME/'assets';source=assets/'recorded_effects'
    vram=bytearray((assets/'ppu.bin').read_bytes());vram[0x6000:0x8000]=bytes(8192)
    tiles={bytes(16):0};palette_words=[]
    for name,mapbase in [('near',0x9000),('far',0xb000)]:
        image=Image.open(source/f'{name}_source.png');a=np.array(image);mask=a[:,:,3]>0
        q=Image.fromarray(a[:,:,:3][mask][None,:,:]).quantize(12,method=Image.Quantize.MEDIANCUT)
        rgb5=np.unique(np.rint(np.array(q.getpalette()).reshape(-1,3)[:12]*31/255).astype(np.int16),axis=0)
        # 面積の小さい白い稜線がmedian cutで薄紫に吸収されないよう実色を残す。
        snow=mask&(a[:,:,:3].min(axis=2)>220)
        if name=='far' and snow.any():
            white=np.rint(np.median(a[:,:,:3][snow],axis=0)*31/255).astype(np.int16)
            rgb5=np.unique(np.vstack([rgb5,white]),axis=0)
        colors=rgb5*8+(rgb5>>2)
        distances=((a[:,:,:3,None].astype(np.int32)-colors.T[None,None,:,:])**2).sum(axis=2)
        nearest=distances.argmin(axis=2)
        counts=[]
        for ty in range(32):
            for tx in range(64):
                n=nearest[ty*8:ty*8+8,tx*8:tx*8+8];m=mask[ty*8:ty*8+8,tx*8:tx*8+8]
                counts.append(np.bincount(n[m],minlength=len(colors)))
        counts=np.array(counts);combos=list(itertools.combinations(range(len(colors)),3))
        pair=((colors[:,None,:].astype(np.int32)-colors[None,:,:])**2).sum(axis=2)
        errors=counts@np.array([pair[:,c].min(axis=1) for c in combos]).T
        chosen=[];best=np.full(len(counts),1e20)
        for _ in range(8):
            ix=int(np.minimum(errors,best[:,None]).sum(axis=0).argmin());chosen.append(combos[ix]);best=np.minimum(best,errors[:,ix]);errors[:,ix]=10**12
        for combo in chosen:
            palette_words.append(0)
            palette_words.extend(int(r|(g<<5)|(b<<10)) for r,g,b in rgb5[list(combo)])
        assigned=np.array([counts@pair[:,combo].min(axis=1) for combo in chosen]).argmin(axis=0)
        rendered=np.zeros_like(a)
        for ty in range(32):
            for tx in range(64):
                selection=int(assigned[ty*64+tx]);combo=chosen[selection]
                cut=a[ty*8:ty*8+8,tx*8:tx*8+8];m=mask[ty*8:ty*8+8,tx*8:tx*8+8]
                c=colors[list(combo)]
                ix=((cut[:,:,:3,None].astype(np.int32)-c.T[None,None,:,:])**2).sum(axis=2).argmin(axis=2)
                pix=(ix+1)*m;raw=bytearray()
                for yy in range(8):
                    for plane in range(2):raw.append(sum(((int(pix[yy,x])>>plane)&1)<<(7-x) for x in range(8)))
                raw=bytes(raw)
                if raw not in tiles:tiles[raw]=len(tiles)
                assert len(tiles)<=512,'BG CHR exceeds 8KiB'
                address=mapbase+(tx//32)*0x800+(ty*32+tx%32)*2
                struct.pack_into('<H',vram,address,tiles[raw]|(selection<<10))
                rendered[ty*8:ty*8+8,tx*8:tx*8+8]=np.dstack([c[ix].astype(np.uint8),m.astype(np.uint8)*255])
        Image.fromarray(rendered).save(source/f'{name}.png')
    # BG2のFX画素はhigh priority。低優先のBG1森林より手前へ置く。
    for address in range(0x8000,0x8800,2):
        tile=struct.unpack_from('<H',vram,address)[0];struct.pack_into('<H',vram,address,tile|0x2000)
    for raw,ix in tiles.items():vram[0x6000+ix*16:0x6010+ix*16]=raw
    (assets/'scenery_palette.bin').write_bytes(struct.pack('<64H',*palette_words))
    metadata=json.loads((source/'source.json').read_text(encoding='utf-8'))
    sky=metadata['skyRgb5'];mountains=metadata['mountains']
    far_y=mountains['mapHorizon']-mountains['screenHorizon']
    sky_start=metadata['skyNativeStart']-mountains['nativeHorizon']+mountains['screenHorizon']-1
    assert 0<len(sky)<128 and 0<sky_start<127
    (assets/'scenery.inc').write_text(f'FX_SCENERY_V = {far_y}\nFX_SKY_START = {sky_start}\nFX_SKY_COLORS = {len(sky)}\n')
    words=[r|(g<<5)|(b<<10) for r,g,b in sky]
    # 間接HDMA。色列は全カメラで共有し、可変の開始行だけ10byte表へ書く。
    data=b''.join(struct.pack('<BBH',0,0,word) for word in words)
    (assets/'sky_hdma.bin').write_bytes(data);(assets/'ppu.bin').write_bytes(vram)
    (source/'scenery_layout.json').write_text(json.dumps({'bg1':'near: map9000, low priority','bg4':'far: mapB000',
        'width':512,'chrBase':24576,'tiles':len(tiles),'skyColors':len(sky),'skyTableBytes':10,
        'farY':far_y,'skyStart':sky_start+1,'groundStart':mountains['screenHorizon']},indent=2)+'\n')
    print(f'Scenery: {len(tiles)}/512 shared 2bpp tiles, two 512px BGs, {len(sky)} shared sky HDMA colors')

if __name__=='__main__':build()
