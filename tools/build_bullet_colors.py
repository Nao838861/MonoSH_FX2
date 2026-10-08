"""原作の同じ自弾を追った四色の見本から、静的OBJパレットを作る。"""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'game/v001/assets/recorded_effects'

def build():
    old=json.loads((ASSETS/'bullet_palette.json').read_text())['rgb5']
    used=sorted(c for count,c in Image.open(ASSETS/'bullet.png').getcolors() if c)
    rank=sorted(used,key=lambda i:sum(a*b for a,b in zip(old[i],(299,587,114))))
    palettes=[]
    for name in ['cyan','mint','lemon','warm']:
        rgba=np.array(Image.open(ASSETS/'shot_color_reference'/f'{name}.png').convert('RGBA'))
        colors=rgba[:,:,:3][rgba[:,:,3]>0]
        luminance=colors@np.array([299,587,114])
        ordered=colors[np.argsort(luminance)]
        palette=[[0,0,0] for _ in range(16)]
        for j,index in enumerate(rank):
            # 小さな圧縮ノイズではなく、その明度帯の実画素の中央値を採る。
            center=(j+.5)/len(rank)
            lo=max(0,int((center-.045)*len(ordered)))
            hi=min(len(ordered),max(lo+1,int((center+.045)*len(ordered))))
            palette[index]=np.rint(np.median(ordered[lo:hi],axis=0)*31/255).astype(int).tolist()
        # 中央の発光芯は各フレームの白い部分。青色のまま暗く固定しない。
        core=Image.open(ASSETS/'bullet.png').getpixel((28,16))
        palette[core]=np.rint(np.median(ordered[int(len(ordered)*.9):],axis=0)*31/255).astype(int).tolist()
        palettes.append(palette)
    meta={'rgb5':palettes,'clock':'globalLogicFrame','framesPerPhase':4,'cycleFrames':16,
          'names':['cyan','mint','lemon','warm'],'source':'shot_color_reference/source.json',
          'note':'距離・サイズに依存せず、ゲーム全体の論理時間で水色→薄緑→黄緑→黄色。4更新ごとに切替。周期は仮設定で、ポーズ中は進まない。四組を起動時に転送し、OAM属性で選ぶ。'}
    (ASSETS/'bullet_color_phases.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    preview=Image.new('RGB',(4*224,160),(80,64,96));draw=ImageDraw.Draw(preview)
    for i,(name,pal) in enumerate(zip(meta['names'],palettes)):
        im=Image.open(ASSETS/'bullet.png').copy()
        im.putpalette([c*8+(c>>2) for p in pal for c in p]+[0]*720)
        rgba=im.convert('RGBA').resize((224,128),Image.Resampling.NEAREST)
        preview.paste(rgba,(i*224,24),rgba);draw.text((i*224+5,5),name,fill='white')
    preview.save(ASSETS/'bullet_color_phases.png')
    return palettes

if __name__=='__main__':build()
