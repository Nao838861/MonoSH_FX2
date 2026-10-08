"""配色の独立条件を検査し、録画の参照コマと実PPUの色アニメを保存する。"""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
from PIL import Image,ImageDraw
from color4_legacy_shape import PALETTE

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'game/v001/assets'
DEST=ROOT/'game/v001/results/color_review_20261008'

def main():
    manifest=json.loads((ROOT/'releases/4bpp30_color.json').read_text())
    rom=(ROOT/manifest['rom']).read_bytes()
    assert hashlib.sha256(rom).hexdigest()==manifest['sha256']
    palette=np.array(PALETTE,dtype=np.uint8);palette=palette*8+(palette>>2)
    def pixels(asset):
        a=np.array(Image.open(ASSETS/f'color4/{asset:02d}.png').convert('RGBA'))
        match=np.all(a[:,:,:3,None]==palette.T[None,None,:,:],axis=2)
        assert match.any(2).all(),f'{asset}: unexpected color'
        return match.argmax(2),a[:,:,3]>=128
    for asset in (0,1):
        p,opaque=pixels(asset)
        assert set(p[opaque])<={3,4},f'{asset}: grass includes non-green pixels'
    face,mask=pixels(14);green=float(np.isin(face[mask],[3,4]).mean())
    assert green>.90,'boss face is not predominantly green'
    body,mask=pixels(13)
    assert np.isin(body[:body.shape[0]//2][mask[:body.shape[0]//2]],[3,4]).all()
    assert np.isin(body[-body.shape[0]//4:][mask[-body.shape[0]//4:]],[5,6]).mean()>.65
    for asset in (6,7,8,31,37):
        p,mask=pixels(asset)
        assert set(p[mask])=={2,9,10},f'{asset}: bullet mixes hues or lacks white center'
    data=ROOT/'game/v001/results/four_bpp_20261008/color'
    player_cases=set();bullet_ages=set()
    for scenario in ('players','bullets'):
        assert manifest['scenarios'][scenario]['romSha256']==manifest['sha256']
        with zipfile.ZipFile(data/scenario/'samples.zip') as z:
            for name in z.namelist():
                if not name.endswith('_meta.json'):continue
                meta=json.loads(z.read(name));p=meta.get('playerInput')
                if scenario=='players' and p:player_cases.add((p['asset'],p['flags'],p['center'],p['bottom']))
                if meta.get('bulletAges'):bullet_ages.update(meta['bulletAges'])
    assert len(player_cases)==408 and bullet_ages==set(range(64))
    DEST.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(data/'bullets/screens.zip') as z:
        frames=[Image.open(io.BytesIO(z.read(f'anim{i:05d}.png'))).convert('RGB').crop((32,24,224,144)).resize((576,360),Image.Resampling.NEAREST) for i in range(160,224,2)]
    frames[0].save(DEST/'bullet_cycle.gif',save_all=True,append_images=frames[1:],duration=[30 if i%3!=2 else 40 for i in range(len(frames))],loop=0,optimize=False)
    panel=Image.new('RGB',(960,496),(40,40,40));draw=ImageDraw.Draw(panel)
    # 元動画の参照コマは採取に使った動画から再生成できる。
    from import_4bpp_recording import frame
    times=[10,32.133333,32.4,32.5,88,94]
    for n,t in enumerate(times):
        x=(n%3)*320;y=(n//3)*248
        draw.text((x+4,y+4),f'recording {t:.3f}s',fill='white')
        panel.paste(frame(t),(x,y+24))
    panel.save(DEST/'reference_frames.png')
    examples=[(14,'Boss face'),(13,'Boss body'),(0,'Grass 0'),(1,'Grass 1'),
              (9,'Player fly'),(15,'Player run'),(28,'Player turn'),(30,'Player turn'),
              (6,'Purple'),(7,'Red'),(37,'Blue'),(31,'Boss light shot')]
    panel=Image.new('RGB',(896,744),(40,40,40));draw=ImageDraw.Draw(panel)
    for n,(asset,title) in enumerate(examples):
        im=Image.open(ASSETS/f'color4/{asset:02d}.png').convert('RGBA')
        if asset in (9,15,28,30):im=Image.open(ASSETS/f'obj_color/{asset:02d}.png').convert('RGBA')
        if asset in (7,37):
            a=np.array(im);shift=4 if asset==7 else 2
            for idx in (9,10):a[np.all(a[:,:,:3]==palette[idx],axis=2),:3]=palette[idx+shift]
            im=Image.fromarray(a)
        scale=min(212/im.width,216/im.height)
        im=im.resize((int(im.width*scale),int(im.height*scale)),Image.Resampling.NEAREST)
        x=(n%4)*224;y=(n//4)*248
        draw.text((x+4,y+4),title,fill='white');panel.paste(im,(x+(224-im.width)//2,y+27),im)
    panel.save(DEST/'materials.png')
    report={'romSha256':manifest['sha256'],'grassAssetsGreen':[0,1],
            'bossFaceGreenFraction':green,'bossBody':'green back / brown belly',
            'bulletCycleTicks':32,'rotationTicks':64,'bulletAgesVerified':len(bullet_ages),
            'playerCasesVerified':len(player_cases),'playerPalette':'original OBJ 15 colors',
            'referenceSeconds':times,'videoSha256':json.loads((ASSETS/'color4/source.json').read_text())['sha256']}
    (DEST/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Colors: face {green:.1%} green, both grasses green, 64 bullet ages, 408 player cases; actual PPU animation saved')

if __name__=='__main__':main()
