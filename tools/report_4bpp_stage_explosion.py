"""地上物体の爆発先頭が影になる不具合を、修正前後の実PPUで記録する。"""
import argparse
import hashlib
import json
import struct
import io
import zipfile
from PIL import Image, ImageDraw
from build_game import ROOT, BUILD, GAME

DEST=GAME/'results/stage_explosion_20261009'

def capture(before):
    src=BUILD/'four_stage_effects' if before else GAME/'results/four_bpp_20261008/color/stage_effects'
    summary=json.loads((src/'summary.json').read_text())
    assert summary['romSha256']==hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    samples=None if before else zipfile.ZipFile(src/'samples.zip')
    screens=None if before else zipfile.ZipFile(src/'screens.zip')
    names=sorted(p.name for p in src.glob('frame*_meta.json')) if before else sorted(n for n in samples.namelist() if n.endswith('_meta.json'))
    read=lambda name:(src/name).read_bytes() if before else samples.read(name)
    for name in names:
        meta=json.loads(read(name))
        if meta['effectPhase']!=0 or meta['field']<200:continue
        # DMA完了直後のPNGには前の表示が残るため、次の同位相の標本を選ぶ。
        if json.loads(read(names[names.index(name)-1]))['effectPhase']!=0:continue
        packet=read(name.replace('_meta.json','_packet.bin'))
        draws=[struct.unpack_from('<hh6B',packet,32+i*10) for i in range(struct.unpack_from('<H',packet)[0])]
        stage=[r for r in draws if r[0]==128 and r[3]!=8 and r[4] in (5,38,39,40,41)]
        assert len(stage)==1,stage
        assert stage[0][4]==(38 if before else 5),stage
        field=(meta['field']//2+1)*2
        shot=f'anim{field:05d}.png'
        image=Image.open(src/shot if before else io.BytesIO(screens.read(shot))).convert('RGB')
        DEST.mkdir(parents=True,exist_ok=True)
        mode='before' if before else 'after'
        image.save(DEST/f'{mode}.png')
        (DEST/f'{mode}_packet.bin').write_bytes(packet)
        record={'romSha256':summary['romSha256'],'phase':0,'asset':stage[0][4],'field':field,'stageDraw':stage[0]}
        (DEST/f'{mode}.json').write_text(json.dumps(record,indent=2)+'\n')
        return
    raise AssertionError('no first explosion phase')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--capture-before',action='store_true');args=parser.parse_args()
    capture(args.capture_before)
    if args.capture_before:return
    panel=Image.new('RGB',(1024,472),(24,24,24));d=ImageDraw.Draw(panel)
    for col,mode in enumerate(('before','after')):
        data=json.loads((DEST/f'{mode}.json').read_text())
        d.text((col*512+8,5),f"{mode}: stage explosion phase 0 / asset {data['asset']}",fill='white')
        panel.paste(Image.open(DEST/f'{mode}.png').resize((512,448),Image.Resampling.NEAREST),(col*512,24))
    panel.save(DEST/'comparison.png')
    print('Ground-object explosion: first phase selects asset 5 instead of shadow 38')

if __name__=='__main__':main()
