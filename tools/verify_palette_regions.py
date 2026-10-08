"""Exercise source-anchored colors through the real GSU and final Mesen PPU.

1,536 isolated requested-asset scenes cover three sizes, both horizontal
orientations, and every x/y tile phase. Additional unchanged-art scenes catch
red default-palette leakage. This is independent of the attribute-cell-center
algorithm: every opaque source pixel must arrive with its intended palette.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import numpy as np
from PIL import Image
import capture_visual_fixtures as capture
from verify_game_display import rgb

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'game/v001/assets'
COLOR = ASSETS/'bg_color'
PALETTES = {0:1,1:1,2:3,3:0,4:2,5:4,6:6,7:5,8:4,11:3,12:3,
            13:2,14:7,31:4,32:3,33:3,34:3,35:3,36:3,37:6,39:4,40:4,41:4,42:3}
SIZES = {3:[(28,15),(55,30),(110,60)],4:[(17,39),(34,79),(61,142)],
         13:[(48,32),(64,43),(110,74)],14:[(24,37),(42,64),(55,84)]}


def fixtures():
    out=[]
    for asset,pal in PALETTES.items():
        aw,ah=Image.open(ASSETS/f'{asset:02d}.png').size
        sizes=SIZES.get(asset,[(max(1,aw//2),max(1,ah//2))])
        for size,(w,h) in enumerate(sizes):
            for flags in ([0,16] if asset in SIZES else [0]):
                for phase in range(64 if asset in SIZES else 8):
                    left=72+(phase%8);top=24+(phase//8 if asset in SIZES else (3*phase)%8)
                    out.append({'name':f'a{asset:02d}_s{size}_f{flags}_p{phase}',
                        'draw':[[left+w//2,top+h+20,w,h,asset,flags,20,0]]})
    return out


def decode_fb(raw):
    # SNES planar bytes are column-major tiles, then row-major pixels.
    a=np.frombuffer(raw,dtype=np.uint8).reshape(32,24,8,2)
    shifts=np.arange(7,-1,-1,dtype=np.uint8)
    p=((a[:,:,:,0,None]>>shifts)&1)|(((a[:,:,:,1,None]>>shifts)&1)<<1)
    return p.transpose(1,2,0,3).reshape(192,256)


def verify(out):
    meta=json.loads((out/'manifest.json').read_text())
    palbytes=(COLOR/'palette.bin').read_bytes()
    rows=[];checked=0;red=0
    for fixture in meta['fixtures']:
        name=fixture['name'];cx,bottom,w,h,asset,flags,_,_=fixture['draw'][0]
        a=np.array(Image.open(COLOR/f'{asset:02d}.png'))
        du=a.shape[1]*256//w;dv=a.shape[0]*256//h
        sx=np.arange(w)*du
        if flags&16:sx=a.shape[1]*256-1-sx
        sy=np.arange(h)*dv
        expected=a[(sy>>8)[:,None],(sx>>8)[None,:]]
        left=cx-w//2;top=bottom-h-20
        fb=decode_fb((out/(name+'_vram.bin')).read_bytes()[:12288])
        full=np.zeros((192,256),dtype=np.uint8);full[top:top+h,left:left+w]=expected
        assert np.array_equal(fb,full),(name,'source projection / alpha changed')
        cg=(out/(name+'_cgram.bin')).read_bytes()
        assert cg[64:128]==palbytes,(name,'wrong CGRAM')
        planned=np.array([rgb(v) for v in struct.unpack('<4H',palbytes[PALETTES[asset]*8:PALETTES[asset]*8+8])],dtype=np.uint8)
        screen=np.array(Image.open(out/(name+'.png')).convert('RGB'))
        actual=screen[top+19:top+19+h,left:left+w]
        mask=expected!=0
        mismatches=np.any(actual!=planned[expected],axis=2)&mask
        if mismatches.any():
            ys,xs=np.nonzero(mismatches)
            raise AssertionError((name,'isolated PPU palette leakage',int(mismatches.sum()),[(int(x),int(y),actual[y,x].tolist(),planned[expected[y,x]].tolist()) for y,x in zip(ys[:8],xs[:8])]))
        if asset==3:
            visible_red=np.all(actual==planned[2],axis=2)
            assert np.array_equal(visible_red,expected==2),(name,'red outside projected lens')
            red+=int(visible_red.sum())
        checked+=int(mask.sum())
        rows.append({'fixture':name,'asset':asset,'size':[w,h],'flip':flags,
                     'opaque_pixels':int(mask.sum()),'ppu_color_errors':0,'alpha_errors':0})
    result={'rom_sha256':meta['rom_sha256'],'scenes':len(rows),'opaque_ppu_pixels':checked,
            'red_lens_ppu_pixels':red,'ppu_color_errors':0,'alpha_errors':0,
            'all_64_x_y_tile_phase_pairs':True,'horizontal_flips':[0,16],
            'requested_assets_three_sizes':[3,4,13,14],
            'overlap_limitation':'Different objects still share one palette per screen tile; checked separately in the fixed overlap scene.',
            'fixtures':rows}
    (out/'semantic_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='fixtures'}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/palette_regions')
    p.add_argument('--reuse-captures',action='store_true')
    args=p.parse_args();out=args.output.resolve()
    if not args.reuse_captures:
        capture.FIXTURES=fixtures()
        capture.SCRIPT=capture.SCRIPT.replace('field//60','field//12').replace('field%60==50','field%12==10').replace('#fixtures*60','#fixtures*12')
        sys.argv=[sys.argv[0],'--output',str(out),'--timeout','600']
        capture.main()
    assert json.loads((out/'manifest.json').read_text())['rom_sha256']==hashlib.sha256((ROOT/'build/game_v001/MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    verify(out)

if __name__=='__main__':main()
