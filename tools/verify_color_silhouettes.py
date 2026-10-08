"""Independent shape/detail regression checks against untouched pre-color PNGs.

Optional fixed-state emulator captures additionally prove rendered silhouettes
match the released pre-color ROM. SELECT alone is not a pre-color reference.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'game/v001/assets'
COLOR=ASSETS/'bg_color'


def check_structure(original,indices):
    opaque=original[:,:,3]>=128
    assert np.array_equal(indices!=0,opaque),'alpha/silhouette changed'
    dark=opaque & (original[:,:,:3].astype(int).sum(axis=2)<384)
    light=opaque & ~dark
    assert np.all(indices[dark]==1),'dark structural detail changed'
    assert np.all((indices[light]==2)|(indices[light]==3)),'light structural detail changed'


def plane_mask(raw):
    a=np.frombuffer(raw,dtype=np.uint8)
    assert len(a)==12288
    return a[::2] | a[1::2]


def verify_captures(root):
    reports=[]
    for path in sorted((root/'visual_fixed').glob('*_fb.bin')):
        name=path.name[:-7]
        fixed=path.read_bytes();mono=(root/'visual_fixed_mono'/path.name).read_bytes()
        original=(root/'visual_precolor'/path.name).read_bytes();before=(root/'visual_before'/path.name).read_bytes()
        mask=plane_mask(fixed);ref=plane_mask(original)
        assert np.array_equal(mask,ref),(name,'pre-color rendered silhouette differs')
        assert fixed==mono,(name,'SELECT changes bitmap')
        # The player and its shots use OBJ. Check their actual final PPU image
        # and OAM across all four builds, not just an empty FX framebuffer.
        if name=='player_shots':
            baseline=(root/'visual_before'/(name+'.rgb')).read_bytes()
            for variant in ['visual_fixed','visual_fixed_mono','visual_precolor']:
                assert (root/variant/(name+'.rgb')).read_bytes()==baseline,(variant,'player/shot PPU changed')
                assert (root/variant/(name+'_oam.bin')).read_bytes()==(root/'visual_before'/(name+'_oam.bin')).read_bytes()
        changed=np.unpackbits(plane_mask(before)^ref).sum()
        reports.append({'fixture':name,'before_mask_errors':int(changed),'after_mask_errors':0,'select_bitmap_errors':0})
    assert len(reports)==6,'expected six paired PPU fixtures'
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--captures',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    checked=[];pixels=0
    for path in sorted(COLOR.glob('[0-9][0-9].png')):
        asset=int(path.stem);base=np.array(Image.open(ASSETS/path.name).convert('RGBA'));im=Image.open(path);indices=np.array(im)
        assert im.mode=='P' and im.size==(base.shape[1],base.shape[0]);assert indices.max()<=3
        assert im.info.get('transparency')==0,'PNG transparent index must be zero'
        check_structure(base,indices);checked.append(asset);pixels+=base.shape[0]*base.shape[1]
    offsets=struct.unpack('<44H',(COLOR/'offsets.bin').read_bytes());cells=(COLOR/'cells.bin').read_bytes()
    for asset in checked:
        im=np.array(Image.open(COLOR/f'{asset:02d}.png'))
        for y in range((im.shape[0]+7)//8):
            for x in range((im.shape[1]+7)//8):
                occupied=im[y*8:(y+1)*8,x*8:(x+1)*8].any()
                cell=y*16+x;pal=(cells[offsets[asset]+cell//2]>>(4*(cell&1)))&15
                assert (pal!=15)==occupied,(asset,'palette-cell coverage mismatch')
                if occupied:
                    assert 0<=pal<=7,(asset,'invalid palette')
                    if asset in [6,7,8,37]:assert 1<=pal<=7,(asset,'grayscale projectile phase')
    # Negative controls prove the checker catches precisely the original class
    # of mistake instead of merely agreeing with rebuilt color assets.
    base=np.array(Image.open(ASSETS/'07.png').convert('RGBA'));indices=np.array(Image.open(COLOR/'07.png'))
    opaque=np.argwhere(base[:,:,3]>=128)[0];dark=np.argwhere((base[:,:,3]>=128)&(base[:,:,:3].sum(axis=2)<384))[0]
    for yx,value in [(opaque,0),(dark,3)]:
        bad=indices.copy();bad[tuple(yx)]=value
        try:check_structure(base,bad)
        except AssertionError:pass
        else:raise AssertionError('negative control missed')
    result={'assets_checked':checked,'source_pixels_checked':pixels,'alpha_errors':0,'dark_detail_errors':0,'negative_controls':2,'projectile_phases_colored':4}
    if args.captures:result['emulator_captures']=verify_captures(args.captures)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
