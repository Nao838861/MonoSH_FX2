# MonoSH Super FX2 開発プロジェクト

**このブランチは独立した[4bpp・30fps実験](README_4BPP30.md)です。** 起動は [play_4bpp30.cmd](play_4bpp30.cmd)、カラーROMは [MonoSHFX2_4bpp30_color.sfc](releases/MonoSHFX2_4bpp30_color.sfc)。mainの更新は一方向に取り込み、元の作業フォルダーには変更を加えません。以下の2bppの記述はmainから引き継いだ開発履歴です。

4bpp版の最新は、地上物体の爆発先頭で影38を選び真っ黒になる条件判定の修正。草二種類の透過・爆発四枚・顎の修正も維持する。共通16色・ディザなし、自機の専用色、BGM第2版とSEを維持。[実ROMの結果](game/v001/RESULTS_4BPP30_20261008.md)、[黒い先頭コマの修正前後](game/v001/results/stage_explosion_20261009/comparison.png)、[草・顎の比較](game/v001/results/material_repair_20261009/comparison.png)。

最新ROMは [2bppの敵・障害物のカラー化試作](game/v001/RESULTS_20261008_BG_COLOR.md)。指定録画から原画を取り込み、透明＋3色×8組を8×8単位で割り当てる。CPUが奥から属性を上書きし、SELECT（専用ランチャーはSpace）で敵・障害物だけモノクロへ切り替える。[比較画像](game/v001/results/bg_color_20261008/comparison.png)。

最新は [白黒の二値化と自機の透明穴修正](game/v001/RESULTS_20261009_BINARY_PLAYER.md)。SELECT／Spaceで敵・障害物を純黒と純白へ切替。ズボン・背中の誤った透明176画素を修復し、描画最適化とBGM第2版を引き継ぐ。[修正前後](game/v001/results/binary_player_20261009/player_comparison.png)。

最新ROMは [BGM第2版](game/v001/RESULTS_20261009_NATIVE_AUDIO_V2.md)：原作サントラで音色を測って作り直したメインテーマを、下の配色整理版に載せた。SEは前版のまま。通常・継続ボス各18,000fieldで全表示間隔1field（60.0988fps）。

直前版は [木・小型敵・ボスの配色整理版](game/v001/RESULTS_20261008_PALETTE_REGIONS.md)。木は暗い緑・緑・茶色、敵は赤い目を本来の範囲に残し金属を灰色に、ボスは象牙色の目・角と茶色の腹部へ変更した。同一場面の実PPU比較と1,696単独表示場面で確認。音声・輪郭・操作・描画エンジンは維持し、異なる物体が重なるタイルの色混ざりは制約として残る。

その前は [輪郭修正＋カラー＋BGM・SE版](game/v001/RESULTS_20261008_VISUAL_FIDELITY.md)。カラー化で欠けた草木・敵弾・敵・ボスの輪郭と暗部の細部を修復した。録画を色の参考にし、旧原画のポーズを保持する。6組の固定場面で、実エミュレーターのframebuffer輪郭がカラー化前ROMと完全一致。実PPUの比較画像と原作らしさの評価をリンク先に保存した。処理落ちは今回の反映条件にしていない。

起動時はカラー。SELECT（専用ランチャーはSpace）で敵・障害物だけモノクロへ切り替える。Startで音も停止・再開する。[BGM試聴](game/v001/results/native_audio_v2_20261009/bgm_preview.mp3)、[SE試聴](game/v001/results/native_audio_v2_20261009/se_preview.mp3)。音声・ゲーム進行・奥行き寸法・自機と自弾は維持する。

[音声なしのカラー60Hz検証](game/v001/RESULTS_20261008_COLOR_60HZ.md)と[最初のカラー試作](game/v001/RESULTS_20261008_BG_COLOR.md)は履歴として保持する。

カラー版にも [奥行きに沿った滑らかな拡縮](game/v001/RESULTS_20261008_SMOOTH_DEPTH.md)を引き継いだ。14寸法表を平滑化し、開いた敵EM1も各ポーズ111項目へ変更した。開EM1の最大段差20→1画素、ボス胴の最長同サイズ区間15→4段階。表示256×180・内部FB256×192・2bpp、木の接地、移動速度の設定を保つ。以下は前版の実装と検証の履歴。

前版の [ボス限定の縮小画像と追加最適化](game/v001/RESULTS_20261008_BOSS_SCALING.md)では、縮小画像をボス3素材だけにし、先読み・透明余白省略・511byteの共通GSUキャッシュ・転送量別のDMA締切を採用した。追加データを約203KiB減らし、録画由来の大きい自弾・二層遠景も統合。CPUのOAM生成・地面HDMA表・転送区間loopも追加最適化した。この描画・転送の実装を新版も引き継ぐ。

前版の統合ROMで通常プレイ・長期ボス各約5分、全区分の表示遅延0、60.10fpsを確認した。固定523場面2,454画像の全FB/OBJ、42条件のDMA限界量も検証した。新版の測定は冒頭の拡縮修正の結果に分けて記録する。

録画由来の大きな自弾・紫から緑の空・二層遠景を実装した。[検証結果](game/v001/RESULTS_20261008_RECORDED_EFFECTS.md)、[静止連射GIF](game/v001/results/recorded_effects_20261008/stationary_fire.gif)を保存している。遠景は録画と実PPU画像を比較し、森を9ドット上げ、山裾の透過穴とグラデーションの範囲を修正した。[修正前後の比較](game/v001/results/scenery_fix_20261008/comparison.png)、[修正内容](game/v001/RESULTS_20261008_SCENERY_FIX.md)。以前の測定値は、その測定時のROMに対する記録。

GitHub: [Nao838861/MonoSH_FX2](https://github.com/Nao838861/MonoSH_FX2)。ソース、単独起動ROM、設計書、測定ログ・画像をこのリポジトリにまとめる。

BGM・SEは[標準SFC音源の実装・検証](game/v001/RESULTS_20261008_NATIVE_AUDIO.md)へ進み、[BGM第2版](game/v001/RESULTS_20261009_NATIVE_AUDIO_V2.md)で曲の音色・編曲を作り直した。[実装前の比較](game/v001/AUDIO_APPROACH_20261008.md)は履歴。

自機は録画から切り出した飛行4・走行4ポーズを32×48・16色へ差し替えた。原寸の16色素材と[比較画像](game/v001/assets/player_recording/comparison.png)、[処理・検証](game/v001/RESULTS_20261007_PLAYER_RECORDING.md)も保存し、通常起動するROMへ反映している。

NES版MonoSHのゲームを、MSXSHの60Hz更新仕様を参照してSNESのCPUへ移植した。Super FX2が拡縮スプライトを奥から描き、自機と自弾・反射弾はPPUのOBJ、通常BGとHDMAが地面・遠景を描く。**Stage 1からボス撃破・次周まで動くROM。** 押しっぱなし射撃で誤ポーズになる入力取得も修正済み。通常操作、押しっぱなし、Startでのポーズ・解除を検証した。詳細は [検証結果](game/v001/RESULTS.md)。

地面は同一消失点からの直線式へ直した。指定RGBに近い緑四色を使い、暗い1/2の列と明るい4/3の列が奥へ続く。空は紫から緑のグラデーション。紫の山と緑の森林は別BGで二重スクロールする。自機17poseは赤い服・青い脚・肌色、自弾は録画由来の水色の輪を56×32から縮小するカラーOBJ。静的CHRとパレットは起動時だけ設定し、毎画像の追加転送は使用枠に応じたOAMだけ。三カメラ・反転・画面端・最悪の重なりを最終PPUの画素で照合した。

まず [play.cmd](play.cmd) で遊べる。[ROM単体](releases/MonoSHFX2_v001.sfc) と [操作・ビルド手順](game/v001/README.md)、[実ゲームの測定結果](game/v001/RESULTS.md) を保存した。上下はNESと同じリバース操作。専用ランチャーでは左右矢印、下＝上昇／上＝下降、X連射、Z単発、Enter一時停止。

## cloneして使う

ROMはGSU/Super FX対応のMesenで開く。専用ランチャーにはPython 3.10以上とPillowが必要で、Mesenの場所は環境変数 `MONOSH_FX2_MESEN` で指定できる。詳細は [操作・準備](game/v001/README.md)。

```powershell
git clone https://github.com/Nao838861/MonoSH_FX2.git
cd MonoSH_FX2
python -m pip install -r requirements.txt
```

ビルドにはPATH上のcc65/ca65/ld65を使う。プロジェクトのルートで実行する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/verify_render_release.py
python -X utf8 tools/verify_full_transfer_objects.py
```

通常のゲームROMのビルドには、元のNES/MSXプロジェクトは不要。固定したソース・画像・表を同梱し、casfxだけ固定commitとhashを検査して取得する。

192行・上下16行黒帯の全12KiB転送は最初のプローブで992bytes欠けた。現在はGSUが前後の矩形を32列のtile区間にまとめ、CPUがSTOP後に部分転送する。転送量と区間数が大きい場合は全12KiB一本へ戻す。実ゲームHDMA併用の最大量テストを通すため、表示は180行にして上下を切った。内部FBは256×192・2bppで、座標・当たり判定は縮めていない。192行表示と実機・より広い入力での60Hz検証は残る。

- [設計書](DESIGN.md) — メモリ所有権、CPU と GSU の並行動作、転送量、地面、移植手順、未決事項。
- [実行可能な移植版 v001](game/v001/README.md) — ゲームROM、操作、元の60Hz更新の移植、描画・転送の実装。
- [v001測定結果](probes/v001/RESULTS.md) — 11種類のGSU描画経路、534件の画素検証、30体合成、全転送不足、NESとの速度比較。
- [clip条件とDMA対策](DMA_OPTIONS.md) — 最大の木はclipなし。矩形からの差分転送、固定空白、HBlank forced blank、黒帯追加を比較。
- [v001再実行手順](probes/v001/README.md) — 検証ROMのビルドと自動実行。
- [依頼原文](REQUEST.md) — 2026年10月5日の依頼を保持。
- [帯域計算](tools/frame_budget.py) — 解像度と描画リスト量から時間予算を再計算する。実測値ではない。
- [開発記憶](https://github.com/Nao838861/nao-u-lab/blob/codex/phase1-collect-20260810/GPT/memory/projects/monosh_fx2/README.md) — 元の作業環境での判断・再開場所。

```powershell
python -X utf8 tools/verify_probe.py
python -X utf8 tools/frame_budget.py
python -X utf8 tools/frame_budget.py --commands 40 --reserve-ms 0.5
python -X utf8 tools/frame_budget.py --normal-dma-bytes 7000
```

現在の実装先は [game/v001](game/v001)。参照元はNESの `D:\HomeBrew\MonoSH` とMSXの `D:\MSXDev\MSXSH` で、原本は変更していない。通常ビルドは固定済みの原本・画像を使う。初期の設計・測定記録にある `projects/monosh_fx2/` は元の作業環境での配置を指す。
