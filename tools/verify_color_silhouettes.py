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


def check_structure(original,indices,asset=None):
    opaque=original[:,:,3]>=128
    assert np.array_equal(indices!=0,opaque),'alpha/silhouette changed'
    dark=opaque & (original[:,:,:3].astype(int).sum(axis=2)<384)
    light=opaque & ~dark
    allowed = np.zeros(dark.shape,dtype=bool)
    if asset == 3:
        fixture=json.loads((COLOR/'03_eye_mask.json').read_text())
        coords=fixture['coordinates_yx']
        assert hashlib.sha256(bytes(n for pair in coords for n in pair)).hexdigest()=='4a0f2216758a4c1f79e9f9a0ef3bd76f1e99fbd1669f2464afe50956e30dc2ea','reviewed eye mask changed'
        for y,x in coords: allowed[y,x]=True
        assert int(allowed.sum())==47 and np.all(dark[allowed]),'invalid reviewed eye mask'
        assert np.array_equal(indices==2,allowed),'red outside reviewed eye / eye interior changed'
    assert np.all(indices[dark & ~allowed]==1),'dark structural detail changed outside reviewed eye'
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
        check_structure(base,indices,asset);checked.append(asset);pixels+=base.shape[0]*base.shape[1]
    offsets=struct.unpack('<44H',(COLOR/'offsets.bin').read_bytes());cells=(COLOR/'cells.bin').read_bytes()
    for asset in checked:
        im=np.array(Image.open(COLOR/f'{asset:02d}.png'))
        for y in range((im.shape[0]+7)//8):
            for x in range((im.shape[1]+7)//8):
                occupied=im[y*8:(y+1)*8,x*8:(x+1)*8].any()
                cell=y*16+x;pal=(cells[offsets[asset]+cell//2]>>(4*(cell&1)))&15
                assert pal!=15,(asset,'palette-cell bounding coverage mismatch')
                if occupied:
                    assert 0<=pal<=7,(asset,'invalid palette')
                    if asset in [6,7,8,37]:assert 1<=pal<=7,(asset,'grayscale projectile phase')
    # User-requested region colors, independent of renderer references.
    palette=np.frombuffer((COLOR/'palette.bin').read_bytes(),dtype='<u2').reshape(8,4)
    def word(r,g,b):return r | g<<5 | b<<10
    assert list(palette[2,1:])==[word(1,7,2),word(3,21,4),word(22,14,10)],'tree/body palette changed'
    assert list(palette[0,1:])==[word(3,3,3),word(31,3,2),word(22,23,25)],'enemy metal must be gray'
    assert list(palette[7,1:])==[word(1,7,2),word(7,23,6),word(25,25,20)],'head must use muted ivory'
    for asset,pal in [(3,0),(4,2),(13,2),(14,7),(42,3)]:
        im=np.array(Image.open(COLOR/f'{asset:02d}.png'))
        for ty in range((im.shape[0]+7)//8):
            for tx in range((im.shape[1]+7)//8):
                cell=ty*16+tx;actual=(cells[offsets[asset]+cell//2]>>(4*(cell&1)))&15
                assert actual==pal,(asset,'mixed per-asset palette')
    head=np.array(Image.open(COLOR/'14.png'))
    assert all(np.count_nonzero(head[y0:y1,x0:x1]==3)>0 for x0,y0,x1,y1 in [(24,37,36,51),(53,37,67,48),(13,0,29,22),(41,0,65,14),(66,0,84,21)]),'eyes/horns lack ivory'
    assert np.count_nonzero(np.array(Image.open(COLOR/'13.png'))==3)>0,'body lacks brown'
    # Negative controls prove the checker catches precisely the original class
    # of mistake instead of merely agreeing with rebuilt color assets.
    base=np.array(Image.open(ASSETS/'07.png').convert('RGBA'));indices=np.array(Image.open(COLOR/'07.png'))
    opaque=np.argwhere(base[:,:,3]>=128)[0];dark=np.argwhere((base[:,:,3]>=128)&(base[:,:,:3].sum(axis=2)<384))[0]
    for yx,value in [(opaque,0),(dark,3)]:
        bad=indices.copy();bad[tuple(yx)]=value
        try:check_structure(base,bad)
        except AssertionError:pass
        else:raise AssertionError('negative control missed')
    # A red pixel outside the reviewed lens must never become a new exception.
    base=np.array(Image.open(ASSETS/'03.png').convert('RGBA'));indices=np.array(Image.open(COLOR/'03.png'))
    bad=indices.copy();bad[18,30]=2
    try:check_structure(base,bad,3)
    except AssertionError:pass
    else:raise AssertionError('eye spill negative control missed')
    result={'assets_checked' :checked,'source_pixels_checked':pixels,'alpha_errors':0,'dark_detail_errors_outside_reviewed_eye':0,'reviewed_red_lens_pixels':47,'negative_controls':3,'projectile_phases_colored':4}
    if args.captures:result['emulator_captures']=verify_captures(args.captures)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
