"""切り抜き採用後の最終ROMと、そのROMに対する計測だけを報告する。"""
import gzip
import hashlib
import io
import json
import zipfile
from PIL import Image,ImageDraw
from build_game import ROOT,GAME

DEST=GAME/'results/four_bpp_20261008'

def shot(mode,scenario,name):
 with zipfile.ZipFile(DEST/mode/scenario/'screens.zip') as z:
  return Image.open(io.BytesIO(z.read(name))).convert('RGB')

def main():
 manifests={m:json.loads((ROOT/f'releases/4bpp30_{m}.json').read_text()) for m in ('color','mono')}
 proof=json.loads((GAME/'results/cutouts_20261009/summary.json').read_text())
 colors=json.loads((GAME/'results/color_review_20261009/summary.json').read_text())
 assert proof['romSha256']==colors['romSha256']==manifests['color']['sha256']
 assert proof['sourceAlphaChanges']==proof['packedAlphaChanges']==proof['nearestPaletteChanges']==0
 for m in manifests.values():
  assert hashlib.sha256((ROOT/m['rom']).read_bytes()).hexdigest()==m['sha256']
  assert all(s['romSha256']==m['sha256'] for s in m['scenarios'].values())
 panel=Image.new('RGB',(1024,944),(20,20,20));d=ImageDraw.Draw(panel)
 for n,(scenario,name,label) in enumerate((('play','screen02400.png','Stage'),('boss_hold','screen01200.png','Boss'),('boss','screen00720.png','Explosion'),('death','screen00480.png','Player'))):
  x=n%2*512;y=n//2*472;d.text((x+5,y+5),label,fill='white')
  panel.paste(shot('color',scenario,name).resize((512,448),Image.Resampling.NEAREST),(x,y+24))
 panel.save(DEST/'overview.png')
 panel=Image.new('RGB',(1024,472),(20,20,20));d=ImageDraw.Draw(panel)
 for n,mode in enumerate(('mono','color')):
  d.text((n*512+5,5),mode+' / 4bpp',fill='white')
  panel.paste(shot(mode,'controls','screen00480.png').resize((512,448),Image.Resampling.NEAREST),(n*512,24))
 panel.save(DEST/'comparison.png')
 labels={'controls':'移動と連射','boss':'ボス撃破・次周','boss_hold':'ボス継続','death':'死亡と復帰','pause':'ポーズ',
  'assets':'全素材・四反転・clip','players':'自機17姿勢','bullets':'弾の色周期・回転','full':'全量転送','play':'通常進行'}
 rows=[];total=0
 for mode,m in manifests.items():
  for key,s in m['scenarios'].items():
   total+=s['pixelSamples']
   rows.append(f"|{'カラー' if mode=='color' else '白黒'}|{labels[key]}|{s['fields']:,}|{s['renderFPS']:.4f}|{s['delayedPresents']}|{s['pixelSamples']}|")
 long=manifests['color']['scenarios']['play'];packing=manifests['color']['packing']
 full=manifests['color']['scenarios']['full'];upstream=manifests['color']['upstream']
 records=[json.loads(l) for l in gzip.decompress((DEST/'color/full/trace.jsonl.gz').read_bytes()).decode().splitlines()]
 dma=[r for r in records if 'dmaMs' in r];dma_ms=max(r['dmaMs'] for r in dma)
 limitation='通常進行でも表示の遅延が残る。常時30fpsの達成とはしない。' if long['delayedPresents'] else '今回の通常進行では遅延0回。人工的な全画面拡大など任意の物量まで保証するものではない。'
 default=json.loads((GAME/'results/cutouts_20261009/default_build.json').read_text())
 result=f'''# 4bpp・30fps版：録画切り抜き素材への切り替え（2026年10月9日）

ユーザーが承認した物体だけの黒背景・16色実験を、実際の4bppカラーROMへ反映した。採取後の二色塗り直しと固定ディザを外し、録画の色画素と陰影を減色の入力にする。木、草、岩、飛行敵、小型敵の開閉、ボス、爆発、炎形のボス弾が対象。自機は専用OBJ色とmainの服の透明穴修正を継承する。

![実ROMの画面](results/four_bpp_20261008/overview.png)

## 起動と分岐

- [カラーROM](../../releases/MonoSHFX2_4bpp30_color.sfc)／[白黒素材の比較ROM](../../releases/MonoSHFX2_4bpp30_mono.sfc)
- [起動cmd](../../play_4bpp30.cmd)／[エディタ起動cmd](../../edit_4bpp30.cmd)
- [ビルド・操作・同期手順](../../README_4BPP30.md)

作業場所は `D:\\HomeBrew\\MonoSHFX2_4bpp30_20261008`、ブランチは `experiment/4bpp-30fps-20261008`。main `{upstream}` までを一方向にmergeした。mainの作業フォルダーは編集していない。Mesenで直接起動できる。矢印で移動、X連射、Z単発、Enterポーズ。NTSC、GSU 100%。起動中の約1.5秒の非表示で音源を読み込む。

## 素材の生成と確認

共通パレットは15色＋透明のindex 0。不透明物体から12色を学習し、通常弾の紫・青・赤は録画由来の代表色を各1色確保する。空・地面・山・自機を色選びの学習対象へ混ぜない。山と森のGSU画像も同じパレットで表示するが、学習には使わない。空と地面は別のRGB5 HDMA、自機は専用15色。画面全体が16色という制約ではない。

木は承認済みの葉・幹・暗い輪郭の分離を使う。小型敵は位置を追跡して開閉姿勢を取り直した。隣の胴が重なるボス胴の端だけ、同じ姿勢の旧原画を採取境界に使用する。拡縮は最近傍で縦横を一緒に変え、投影比率の違いは透明余白で調整する。元の二値マスクによる塗り直しはしない。

通常弾は旧四姿勢の主軸と輪郭を半分の原画寸法で保持し、録画の短軸方向の階調を移す。別の撮影姿勢の傾きは移さない。白い中心と単色の両側の陰影、32更新周期（紫16→赤8→青8）、64更新の回転を維持。色周期別の原画と縮小行を事前生成し、パレット番号の加算を廃止した。炎形のボス弾は録画どおり橙色で描く。通常弾の周期は録画から推定したもので原作ROMからの抽出ではない。

[切り抜きと減色の比較](results/cutouts_20261009/materials.png)、[素材一覧](assets/color4/captures.png)、[実PPUの弾アニメ](results/color_review_20261009/bullet_cycle.gif)、[時刻・矩形・動画SHA256](assets/color4/source.json)。{proof['captureAssetsVerified']}採取素材の不透明{proof['sourceOpaquePixelsVerified']:,}画素について元RGBの不変を検査し、全44素材の透明・最近傍による減色・ROM配置が一致した。ディザは使わない。旧35素材の二値一致は今回の採用で置き換わり、過去の証跡は旧ROMの記録として保持する。自機17姿勢、影、STAGE文字など全素材を新規に動画採取したわけではない。

## 転送・容量・速度

内部256×192、4bppの24KiBをVRAMの二面へ交互に転送する。既存の非表示203行以降〜次22行を二回使い、64pxの四本の帯を二本ずつ描画・転送し、完成世代だけを表示する。ゲーム計算と入力は画像ごとに2回。NTSCの目標は約30.0494fps。自機OBJは姿勢変更時に896bytesを加え、OAMと同じ世代で提示する。地面HDMAを維持する。

ROMは2MiB、原画{packing['rawSpriteBytes']:,}bytes、事前縮小行{packing['prescaledBytes']:,}bytes。音源用の `$59:1300..FFFF`（60,672bytes）を配置対象から除外する。透明の詰め物43はSTAGE左端の透明画素を参照し、音源を画像として読まない。音源の待機状態を挟む読み込みがプレイ中に約5ms/fieldを使うことを計測し、4bpp版だけ起動時に全て完了するようにした。

全量転送fixtureの各半分12KiBは最大{dma_ms:.6f}ms。二つの非表示区間へ24KiBを送る帯域は成立するが、人工的な全面拡大では描画を含め{full['renderFPS']:.4f}fps。通常進行18,000fieldは{long['renderFPS']:.4f}fps、2fieldを超えた更新{long['delayedPresents']}回。GSUの半分の描画時間は最大{long['actualGsuMaxMs']:.6f}ms。{limitation}

## 最終ROMの検証

|素材|場面|field数|平均描画fps|遅延回数|画素照合数|
|---|---|---:|---:|---:|---:|
{chr(10).join(rows)}

合計{total:,}標本で全49,152画素と表示中VRAMの24KiBを独立合成へ照合した。自機は実OAM・CHR・CGRAMから408条件を合成し、専用色・透明を元画像と照合。通常弾三発とボス炎弾で64位相を検査。地面CHR・mapの不変、DMAの非表示期間、通常の移動・連射、ポーズ、死亡と復帰、ボス撃破と次周も検査した。実機では未検証。

既定2bppビルドはmainの配布ROMと全2MiBが一致し、SHA256 `{default['sha256']}`。今回の共通ソース変更が2bppの機械語を変えないことを確認した。

- カラーROM SHA256: `{manifests['color']['sha256']}`
- 白黒ROM SHA256: `{manifests['mono']['sha256']}`

[colorの計測・識別](../../releases/4bpp30_color.json)／[mono](../../releases/4bpp30_mono.json)。実行Lua、trace、packet・FB・VRAM・OAM標本と画面を [結果フォルダー](results/four_bpp_20261008/) に保存する。以前のROMの速度を新ROMの保証には使わない。
'''
 (GAME/'RESULTS_4BPP30_20261008.md').write_text(result,encoding='utf-8')
 print(f'Final cutout ROM report: {total} full-frame comparisons; long play {long["renderFPS"]:.4f}fps')

if __name__=='__main__':main()
