# 比較で採用しなかった途中ソース

2画素単位のgeneric、木だけの余白表、別cacheを使った余白省略、asset選別の検討途中を保存する。最終版は原画の余白情報とgenericの先読みを511byteの共通cacheへ置く。

これらは調査途中のスナップショットで、各比較ROMとbyte一致する再ビルドを保証しない。当時の測定対象の正本は各比較ディレクトリの圧縮ROM・`game.lbl`・`build_mode.json`・生成Lua・処理時間ログ。公開用ROMは`releases/MonoSHFX2_v001.sfc`。
