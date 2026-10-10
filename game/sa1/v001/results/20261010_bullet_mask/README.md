# 敵弾の透明マスクと不透明8word転送

`--bullet-mask-arithmetic`で、4画素wordの透明マスクを2回の表引きから
nibbleごとの零検出へ変えた。65536通りの入力を従来マスクと照合した。
道中1800fieldでは1689枚・146画面一致で、従来最良と同じだった。
反転・色・縮小・四辺clipのfixtureも120画面一致した。

`--bullet-opaque8`は完全に不透明な連続8wordだけを展開したコードで写す。
この追加では道中1800fieldで1690枚・146画面一致、fixture120画面一致。
いずれも60fps未達。公開ROMは更新していない。

比較の実行ROM・ラベル・捕捉画像・原データはevidence.zip、結果はcomparison.json。
