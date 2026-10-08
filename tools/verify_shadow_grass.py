"""影と草の両描画順・8種類のタイル位置を、実PPUの全不透明画素で照合する。"""
import argparse
import json
import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import capture_visual_fixtures as capture
from verify_palette_regions import decode_fb
from verify_game_display import rgb

ROOT=Path(__file__).resolve().parents[1]
COLOR=ROOT/'game/v001/assets/bg_color'

def fixtures():
    out=[{'name':'shadow_alone','draw':[[128,174,32,8,38,0,0,0]]}]
    for grass in (0,1):
        for order in (0,1):
            for phase in range(8):
                dx=phase;dy=(phase*3)%8
                out.append({'name':f'grass{grass}_order{order}_phase{phase}',
                    'draw':[[128+dx,174+dy,32,8,38,0,40 if order else 20,0],
                            [128+dx,186+dy,48,28,grass,0,20 if order else 40,0]]})
    return out

def verify(out,baseline):
    meta=json.loads((out/'manifest.json').read_text())
    palette=np.array([rgb(v) for v in struct.unpack('<4H',(COLOR/'palette.bin').read_bytes()[8:16])])
    errors=0;checked=0;overlap=0
    for fixture in meta['fixtures']:
        name=fixture['name'];expected=np.zeros((192,256),dtype=np.uint8)
        masks=[]
        for cx,bottom,w,h,asset,flags,z,priority in sorted(fixture['draw'],key=lambda d:(d[7],-d[6])):
            a=np.array(Image.open(COLOR/f'{asset:02d}.png'))
            sample=a[(np.arange(h)*(a.shape[0]*256//h)>>8)[:,None],
                     (np.arange(w)*(a.shape[1]*256//w)>>8)[None,:]]
            x=cx-w//2;y=bottom-h-20;mask=sample!=0
            expected[y:y+h,x:x+w][mask]=sample[mask]
            full=np.zeros_like(expected,dtype=bool);full[y:y+h,x:x+w]=mask;masks.append(full)
        if len(masks)==2:
            assert (masks[0]&masks[1]).any(),'fixture must really overlap opaque grass and shadow'
            overlap+=int((masks[0]&masks[1]).sum())
        actual=decode_fb((out/(name+'_vram.bin')).read_bytes()[:12288])
        assert np.array_equal(actual,expected),(name,'bitmap changed')
        screen=np.array(Image.open(out/(name+'.png')).convert('RGB'))[19:211,:]
        mask=expected!=0
        errors+=int((np.any(screen!=palette[expected],axis=2)&mask).sum())
        checked+=int(mask.sum())
    if baseline:assert errors>0,'baseline must reproduce wrong palette'
    else:assert errors==0,('grass/shadow palette leakage',errors)
    result={'romSha256':meta['rom_sha256'],'scenes':len(meta['fixtures']),'opaquePpuPixels':checked,
            'overlappingSourcePixels':overlap,'ppuColorErrors':errors,'bitmapErrors':0,
            'grassAssets':[0,1],'drawOrders':2,'tilePositions':8,'palette':1,'shadowIndex':1,
            'shadowRgb5':[1,7,2],'shadowRgb':palette[1].tolist(),'baseline':baseline,'hardwareTested':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--baseline',action='store_true')
    args=p.parse_args();out=args.output.resolve()
    capture.FIXTURES=fixtures()
    capture.SCRIPT=capture.SCRIPT.replace('field//60','field//12').replace('field%60==50','field%12==10').replace('#fixtures*60','#fixtures*12')
    sys.argv=[sys.argv[0],'--output',str(out),'--timeout','180']
    capture.main()
    assert not (out/'error.txt').exists(),'emulator script error'
    verify(out,args.baseline)

if __name__=='__main__':main()
