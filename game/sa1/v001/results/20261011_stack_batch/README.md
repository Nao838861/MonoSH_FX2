# スタック描画の複数行まとめ試験

`build_sa1_planar_probe.py --packed-stack --row-calls --stack-batch 8` の後に `test_sa1_probe.py` を実行。既存55fixture全て画素一致。最大描画5.528169ms、全面消去込み10.116275ms。一行ごとにBW mapとstackを設定する前回の9.233msから改善した。8KiBのBW mirror境界と描画順を越えない最大8行で、設定・復帰を共有する。

位置・寸法の検索、ゲーム処理、PPU転送を含まず、ゲームへの統合はまだ行っていない。長いfixture全体で割り込みを止める旧方式と異なり、まとめた行の単位で元のstackと割り込み状態を復帰する。ROM SHA `2ae9c3156932d3bb45c933e33b8f5f40dd285e9a762200c2df9beb6ebb17bd2c`。証拠zipは156,468byte、SHA `70f45333b4746019d78060ade9f885c6f6a417d067dc0889a3364185dfad1453`。

`analyze_sa1_stack_capacity.py` はゲームROMの既存行kernelを読み戻し、PEA主体の逆順書き込みへ変換する追加容量を測る。元の全1,492寸法は維持したまま、速い経路を追加する前提。幅94の爆発39/40/41を全て追加すると、code37,036byte、右端clip表6,832byte、行descriptor7,056byteとなる。40/41のみならcode23,215byte、clip表3,644byte、descriptor4,704byte（合計31,563byte、別途lookup・配置padding）。40のみなら合計14,863byte。

全ての大きい爆発へ一度に追加するのは現ROMの空きに収まらない。幅94の40/41を候補として、未使用ROM領域の実データ非重複、clip境界、guard、IRQ許可復帰を確認してからゲームへ入れる。容量測定だけで描画の高速化や60fps達成とは判定しない。公開ROMは変えていない。
