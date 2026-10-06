"""録画の3倍表示をドット格子へ戻し、固定原画と16色OBJを生成する。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'game/v001/assets'
SOURCE = ASSETS / 'player_recording'
DEST = ASSETS / 'obj_color'
# index 0は透明。既存の弾の5/7/8はRGB5まで保存する。
PALETTE = [[0,0,0], [1,0,3], [22,13,13], [31,3,4], [12,21,31],
           [31,31,31], [0,1,18], [31,12,0], [31,28,2], [17,0,0],
           [27,0,0], [30,15,13], [31,26,23], [31,31,18], [10,4,5],
           [20,24,31]]
# 1始まりの30fpsフレーム番号。320x224内の確認済み矩形。
CAPTURES = [
    (0, 1741, (144,77,184,143), False),
    (1, 2086, (248,90,298,157), True),
    (2, 1816, (11,81,61,150), False),
    (3, 1819, (12,57,62,125), False),
    (10,31, (140,162,185,221), False),
    (11,32, (140,162,185,221), False),
    (12,34, (140,162,185,221), False),
    (13,36, (140,162,185,221), False),
]
POSE_ASSET = {0:9, 1:28, 2:29, 3:30, 10:15, 11:16, 12:17, 13:18}

def rgb8():
    return [tuple(c*8+(c>>2) for c in color) for color in PALETTE]

def indexed(image):
    colors = rgb8()
    out = Image.new('P', image.size)
    out.putpalette([c for p in colors for c in p] + [0]*720)
    pixels = []
    rgba=image.convert('RGBA')
    for r,g,b,a in rgba.getdata():
        if a < 128:
            pixels.append(0)
        else:
            pixels.append(min(range(1,16), key=lambda i:
                (r-colors[i][0])**2 + (g-colors[i][1])**2 + (b-colors[i][2])**2))
    out.putdata(pixels)
    return out

def cut_sprite(frame, box, mirror):
    crop = frame.crop(box).convert('RGBA')
    pixels=[]
    for y in range(crop.height):
        gy = y+box[1]
        # 画面左右の空を背景見本にし、地平線の縦グラデーションも除く。
        bg=frame.getpixel((220,gy)) if box[0]<200 else frame.getpixel((80,gy))
        for x in range(crop.width):
            r,g,b,_=crop.getpixel((x,y))
            purple=b>r+18 and r>g+20
            green=g>r+10 and g>b+5
            background=sum((v-w)**2 for v,w in zip((r,g,b),bg))<45**2
            mountain=box[1]>=160 and gy<170 and b>r+10
            pixels.append((r,g,b,0 if purple or green or background or mountain else 255))
    crop.putdata(pixels)
    # 背景の孤立した圧縮ノイズを除く。手足・髪の対角接続は残す。
    remaining={(x,y) for y in range(crop.height) for x in range(crop.width)
               if crop.getpixel((x,y))[3]}
    components=[]
    while remaining:
        seed=remaining.pop(); component={seed}; stack=[seed]
        while stack:
            x,y=stack.pop()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    neighbor=(x+dx,y+dy)
                    if neighbor in remaining:
                        remaining.remove(neighbor);component.add(neighbor);stack.append(neighbor)
        components.append(component)
    keep=max(components,key=len)
    crop.putdata([(r,g,b,a if (i%crop.width,i//crop.width) in keep else 0)
                  for i,(r,g,b,a) in enumerate(pixels)])
    # 選んだ矩形内に自機以外はない。格子は維持して透明余白だけ切る。
    bbox=crop.getbbox()
    assert bbox is not None
    crop=crop.crop(bbox)
    if mirror: crop=crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return crop

def extract(video):
    SOURCE.mkdir(exist_ok=True)
    ffmpeg=shutil.which('ffmpeg')
    assert ffmpeg, '録画の再取込にはffmpegが必要'
    records=[]
    with tempfile.TemporaryDirectory() as temporary:
        for pose,frame,box,mirror in CAPTURES:
            path=Path(temporary)/f'{pose}.png'
            subprocess.run([ffmpeg,'-hide_banner','-loglevel','error',
                '-i',str(video),'-vf',f'select=eq(n\\,{frame-1}),crop=960:672:480:204,scale=320:224:flags=neighbor',
                '-frames:v','1',str(path)],check=True)
            crop=cut_sprite(Image.open(path).convert('RGB'),box,mirror)
            crop.save(SOURCE/f'pose{pose:02d}.png')
            records.append({'pose':pose,'asset':POSE_ASSET[pose],'frame':frame,
                            'seconds':(frame-1)/30,'crop':list(box),'mirror':mirror,
                            'nativeSize':list(crop.size)})
    metadata={'videoName':video.name,'videoSha256':hashlib.sha256(video.read_bytes()).hexdigest(),
              'videoSize':[1920,1080],'fps':30,'screenRect':[480,204,960,672],
              'nativeScreenSize':[320,224],'captures':records,'scale':0.75,
              'destinationSize':[32,48], 'unrecordedPoses':[4,5,6,7,8,9,14,15,16],
              'note':'録画にない死亡・つまずきは既存の固定原画を維持。動画自体は同梱しない。'}
    (SOURCE/'source.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build():
    # 再実行時も旧パレットを正しく読む。死亡・つまずきの輪郭を変えない。
    for asset in [9,*range(15,31)]:
        if asset not in POSE_ASSET.values():
            old=Image.open(DEST/f'{asset:02d}.png').convert('RGBA')
            indexed(old).save(DEST/f'{asset:02d}.png',transparency=0)
    for pose,asset in POSE_ASSET.items():
        original=Image.open(SOURCE/f'pose{pose:02d}.png').convert('RGBA')
        indexed(original).save(SOURCE/f'native16_pose{pose:02d}.png',transparency=0)
        size=tuple(round(n*0.75) for n in original.size)
        assert size[0]<=32 and size[1]<=48, (pose,size)
        small=original.resize(size,Image.Resampling.NEAREST)
        canvas=Image.new('RGBA',(32,48))
        canvas.paste(small,((32-size[0])//2,48-size[1]))
        indexed(canvas).save(DEST/f'{asset:02d}.png',transparency=0)
    (DEST/'palette.json').write_text(json.dumps({'rgb5':PALETTE},indent=2)+'\n',encoding='utf-8')
    metadata=json.loads((DEST/'source.json').read_text(encoding='utf-8'))
    if 'legacyNesImport' not in metadata:
        legacy_keys=['sourceSha256','poses','bases','assets','upperIndices','lowerIndices','paletteRuleReference']
        metadata['legacyNesImport']={key:metadata.pop(key) for key in legacy_keys if key in metadata}
    metadata['sourceType']='録画8ポーズ＋既存NES由来9ポーズ＋既存弾'
    metadata['recordedPlayer']='../player_recording/source.json'
    metadata['recordedPoses']=list(POSE_ASSET)
    metadata['paletteRule']='録画の金髪・赤服・青ズボンの陰影。透明1+不透明15色。弾の5/7/8は保持。'
    metadata['sourceImageSha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.glob('*.png'))}
    (DEST/'source.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet=Image.new('RGB',(8*128,240),(72,64,88));draw=ImageDraw.Draw(sheet)
    for i,(pose,asset) in enumerate(POSE_ASSET.items()):
        im=Image.open(DEST/f'{asset:02d}.png').convert('RGBA').resize((128,192),Image.Resampling.NEAREST)
        sheet.paste(im,(i*128,24),im)
        draw.text((i*128+6,6),f'pose {pose} / {asset:02d}',fill='white')
    sheet.save(SOURCE/'preview.png')
    print('録画の飛行4・走行4ポーズを32x48/16色へ変換')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',type=Path)
    args=parser.parse_args()
    if args.video:extract(args.video)
    build()
