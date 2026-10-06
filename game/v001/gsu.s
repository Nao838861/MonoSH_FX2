.include "casfx.inc"
; Super FX2の拡縮・合成処理。CPUが奥→手前に安定ソートした順をそのまま描く。
; 既定構成はconfig.jsonのgsuClip/gsuUv=true、fullFramebufferTransfer=false。
; 流れ: 前回領域clear → packet展開 → clip → UV設定 → 描画 → DMA区間作成。
;
; 出力は256x192、SNESの2bppタイル形式。SCBR等はCPU側で設定済み。
; 画素値0=透明、1=不透明な黒、3=白。白黒と透明を合わせて3状態を使う。
; PLOTに1bppモードはなく、ここでは最小の2bppを使う。
; 原画ROMは各行256bytes、各bankに高さ128以下の原画を2枚配置する。
;   行内  0..127: 1画素/byte。任意倍率をGETCで直接COLORへ読める。
;       128..159: 4画素/byteのpacked 2bpp。左の画素が下位2bit。
;       160..191: 同じ4画素を逆のbit順で格納。左右反転用。
; この配置はtools/build_game.pyのexport_assets/pack_assetsと対応する。
; 原画行の後のpaddingには横方向だけQ8.8で縮小済みのpacked行を置く。
; 対象は草2種・木・ボス胴/顔/弾。縦方向のV/DVは実行時に計算する。
; 原画を置換せず、対応幅の608段階を追加する。メタ表はROM bank5F。
;
; 描画ループ直前のレジスタ契約（packet/clip/UV準備中は役割が変わる）:
;   R0  演算・packed画素展開の作業値
;   R1  出力X。PLOTが自動で+1する         R2  出力Y
;   R3  原画Uの増分DU、符号付きQ8.8      R4  原画Vの増分DV、符号付きQ8.8
;   R5  行頭の出力X                      R6  残り出力行数
;   R7  原画V、Q8.8。bit15は原画ペアの後半を選ぶ
;   R8  genericでは原画U、packedではV整数部のmask
;   R9  出力幅（packedでは1行の繰り返し回数に変更）
;   R10 行頭の原画U（packedでは行内のROM byte位置に変更）
;   R11 packetポインタ/ジャンプ先（doubleでは端数画素数）
;   R12 LOOP回数                         R13 LOOPの戻り先
;   R14 原画ROMアドレス。書き換えるとROM読み出しが始まる
;
; GSUはジャンプ/分岐の直後の命令も実行する（delay slot）。
; LOOP直後のPLOTや行末のINCを移動すると、画素数や座標が変わる。
; CACHEは命令キャッシュを使うための指定であり、画素データの圧縮ではない。
; stableGsuCache: 共通準備+scaled+genericを485byteへ配置。clip補正はcache外。
; generic/packed間や異なるpacked経路へ切替時にCBRを変更。同じ経路なら保持。
; cpuClipCommands: packet末尾bit15=INSIDE。GSUは座標補正だけを省く。
;
; 最適化の評価: 内側のループは短くしてあるが、描画全体の最速は未証明。
; genericは未収録幅・左右反転等の任意倍率を受け持つ。整数比はpackedへ。
; その他の対応幅はscaled_renderで4画素ずつ展開し、clipの先頭端数も描く。
; scaled/genericと共通準備を同じ512byte枠に置き、clipでCBRを変えない。
; 最後のDMA区間生成だけ別cacheへ移る。比較結果はRENDER_ITERATIONS参照。
; probes/v001の最速経路には同色区間もあるが、このゲームの選択器にはない。
.segment "GSU"
.export render_entry, render_stop
.ifdef FX_STABLE_GSU_CACHE
.export hot_cache, hot_cache_end, generic_render, clip_edges
.endif
.export packed_one, packed_half, packed_quarter, packed_double
.export packed_mirror_one, packed_mirror_half, packed_mirror_quarter
.align 16
render_entry:
  cache
  sub r0                     ; R0=0。CMODEの各optionを解除する。
  cmode                      ; 色0は書かずにXだけ進む。奥の画素を残す。
  .ifdef FX_GSU_CLIP
  ; 既定経路。前回のtile列範囲を消し、今回の範囲記録を初期化する。
  .include "gsu_clear.inc"
  .else
  ; 初回は全FB、その後は前回・今回のtile範囲だけを0へ戻す。
  iwt r11,#$0008
  ldw (r11)
  move r9,r0
  iwt r10,#$0600
clear_span:
  ; 非GSU-clip構成: CPUが列挙した[offset words, length bytes]を処理する。
  ibt r0,#0
  from r9
  cmp r0
  beq clear_done
  nop
  dec r9
  to r0
  ldw (r10)
  add r0
  iwt r8,#$2000
  to r1
  add r8
  inc r10
  inc r10
  ldw (r10)
  lsr
  move r12,r0
  inc r10
  inc r10
  iwt r13,#.loword(clear_loop)
  sub r0
clear_loop:
  stw (r1)                   ; PLOTで1画素ずつ消さず、0を16bit単位で書く。
  inc r1
  loop
  inc r1                     ; delay slot。2つのINCで次のwordへ進む。
  bra clear_span
  nop
clear_done:
  .endif
  ; header $00の描画件数を$04へ複製。$06は次のpacket位置で初期値$20。
  ; 各spriteがR11を作業用に使うため、件数・packet位置はRAMに保持する。
  iwt r11,#$0000
  ldw (r11)
  iwt r11,#$0004
  stw (r11)
  iwt r0,#$0020
  iwt r11,#$0006
  stw (r11)
  .ifdef FX_STABLE_GSU_CACHE
  ; 初回はdispatchへ。scaled/genericを含む共通のCBRを維持する。
  iwt r11,#.loword(dispatch)
  .align 16,$01           ; GSUのNOPで埋める。0はSTOPなので使わない。
hot_cache:
  cache
  jmp (r11)
  nop
  .ifdef FX_SCALED_ROWS
scaled_render:
  .include "gsu_scaled_draw.inc"
  .ifdef FX_SCALED_CLIP
  .include "gsu_scaled_head.inc"
  .endif
  .ifdef FX_FAST_UV
generic_render:
  .include "gsu_generic.inc"
  .endif
  .else
generic_render:
  ; 任意倍率の最近傍サンプリング。U/Vの整数部で原画画素を選ぶ。
  ; 6行の画素loop。MERGE r14はWITH+MERGEへ展開され、実命令は7つ。
  ; clip/透明の分岐、乗算、bitの取り出しをここへ入れない。
  iwt r13,#.loword(pixel)
row:
  move r1,r5                 ; 出力Xを行頭へ戻す。
  move r8,r10                ; 原画Uを行頭へ戻す。
  move r12,r9                ; 出力幅だけLOOPする。
pixel:
  merge r14                  ; (R7 & $ff00) | (R8 >> 8)。行pitchの乗算を省く。
  with r8                    ; 以下のADDの入力・出力をR8へ指定するprefix。
  add r3                     ; 次のUへ進める。現在のROM読出し待ちと重ねる。
  getc                       ; 原画byteを直接COLORへ。0/1/3に変換済み。
  loop                       ; R12を減らし、非0ならR13へ戻る。
  plot                       ; delay slot。最終回も描き、透明でも出力Xは+1。
  with r7
  add r4                     ; 次の原画行へ。fractionを残して倍率を滑らかにする。
  dec r6
  bne row
  inc r2                     ; delay slot。次の出力行へ進める。
  rpix                       ; PLOTの画素cacheをRAMへflush。読んだ色は使わない。
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
  .endif
.endif
.export generic
dispatch:
  iwt r11,#$0004
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne dispatch_nonzero
  nop
  iwt r11,#.loword(finished)
  jmp (r11)
  nop
dispatch_nonzero:
  dec r0
  stw (r11)
  iwt r11,#$0006
  ldw (r11)
  move r11,r0
  .ifdef FX_GSU_CLIP
    ; 10byte/体の生寸法から左上とbank/metaを求める。ZはCPUのsortに使用済み。
    .include "gsu_draw.inc"
  .else
  ; 非GSU-clip構成は20byte/体の準備済み情報を読む。
  ; 順序: X,Y,DU,DV,left,height,V0,width,U0,bank。いずれも16bit。
  ; FX_GSU_UVだけ有効なら、DU/DV欄は元寸法、V0/U0欄はbase+整数skipを渡す。
  to r1
  ldw (r11)
  inc r11
  inc r11
  to r2
  ldw (r11)
  inc r11
  inc r11
  to r3
  ldw (r11)
  inc r11
  inc r11
  to r4
  ldw (r11)
  inc r11
  inc r11
  to r5
  ldw (r11)
  inc r11
  inc r11
  to r6
  ldw (r11)
  inc r11
  inc r11
  to r7
  ldw (r11)
  inc r11
  inc r11
  to r9
  ldw (r11)
  inc r11
  inc r11
  to r10
  ldw (r11)
  inc r11
  inc r11
  ldw (r11)
  romb
  inc r11
  inc r11
  .endif
  ; 次packet位置は、shaderやUV準備でR11を壊す前に保存する。
  iwt r8,#$0006
  from r11
  stw (r8)
  .ifdef FX_GSU_CLIP
    ; clipはspriteごとに1回。内側の画素ループには境界判定を入れない。
    ; 全画面外ならdispatchへ戻る。非空矩形だけをUV設定へ渡す。
    .include "gsu_clip.inc"
  .endif
  .ifdef FX_GSU_UV
    ; DU/DVはROM表から取得し、clipで飛ばす原画位置と反転を設定する。
    .ifdef FX_FAST_UV
    .include "gsu_uv_fast.inc"
    .else
    .include "gsu_uv.inc"
    .endif
  .endif
  .ifndef FX_STABLE_GSU_CACHE
.export gsu_selector_cache
gsu_selector_cache:
  cache
  .endif
  .ifdef FX_SCALED_ROWS
  iwt r11,#.loword(selector)
  jmp (r11)
  nop
hot_cache_end:
  .assert hot_cache_end-hot_cache <= 512, error, "GSU common path exceeds cache"
selector:
  .endif
  ; packedでもgenericと同じ原画画素を選ぶため、開始位置とDUを検査する。
  ; U0 & $03ff == 0: 小数部0かつ原画Xが4画素境界。正方向の候補。
  ;             == $03ff: 4画素群の右端+小数部$ff。左右反転の候補。
  ; その他はgenericへ。packedに合わせて座標や倍率を丸めない。
  iwt r8,#$03ff
  from r10
  and r8
  beq positive_steps
  nop
  cmp r8
  bne generic
  nop
  iwt r0,#$ff00
  from r3
  cmp r0
  beq mirror_one_check
  nop
  iwt r0,#$fe00
  from r3
  cmp r0
  beq mirror_half_check
  nop
  iwt r0,#$fc00
  from r3
  cmp r0
  beq mirror_quarter_jump
  nop
  bra generic
  nop
positive_steps:
  ; 水平DU=$0080/$0100/$0200/$0400は、2倍/等倍/半分/1/4。
  ; 垂直はどの経路もQ8.8加算なので、DVまで同じ整数比である必要はない。
  iwt r0,#$0080
  from r3
  cmp r0
  beq packed_double_check
  nop
  iwt r0,#$0100
  from r3
  cmp r0
  beq packed_one_check
  nop
  iwt r0,#$0200
  from r3
  cmp r0
  beq packed_half_check
  nop
  iwt r0,#$0400
  from r3
  cmp r0
  beq packed_quarter_jump
  nop
  .ifdef FX_STABLE_GSU_CACHE
  .ifndef FX_SCALED_ROWS
hot_cache_end:
  .assert hot_cache_end-hot_cache <= 512, error, "GSU common path exceeds cache"
  .endif
generic:
  .ifdef FX_SCALED_ROWS
  iwt r11,#.loword(scaled_select)
  jmp (r11)
  nop
generic_fallback:
  .ifdef FX_FAST_UV
  iwt r11,#.loword(generic_render)
  iwt r8,#.loword(hot_cache)
  jmp (r8)
  nop
  .else
  iwt r11,#.loword(generic_render)
  jmp (r11)
  nop
generic_render:
.export generic_cache
generic_cache:
  cache
  .include "gsu_generic.inc"
  .endif
  .else
  iwt r11,#.loword(generic_render)
  iwt r8,#.loword(hot_cache)
  jmp (r8)
  nop
  .endif
  .else
generic:
  ; 任意倍率の最近傍サンプリング。U/Vの整数部で原画画素を選ぶ。
  ; 6行の画素loop。MERGE r14はWITH+MERGEへ展開され、実命令は7つ。
  ; clip/透明の分岐、乗算、bitの取り出しをここへ入れない。
  iwt r13,#.loword(pixel)
row:
  move r1,r5                 ; 出力Xを行頭へ戻す。
  move r8,r10                ; 原画Uを行頭へ戻す。
  move r12,r9                ; 出力幅だけLOOPする。
pixel:
  merge r14                  ; (R7 & $ff00) | (R8 >> 8)。行pitchの乗算を省く。
  with r8                    ; 以下のADDの入力・出力をR8へ指定するprefix。
  add r3                     ; 次のUへ進める。現在のROM読出し待ちと重ねる。
  getc                       ; 原画byteを直接COLORへ。0/1/3に変換済み。
  loop                       ; R12を減らし、非0ならR13へ戻る。
  plot                       ; delay slot。最終回も描き、透明でも出力Xは+1。
  with r7
  add r4                     ; 次の原画行へ。fractionを残して倍率を滑らかにする。
  dec r6
  bne row
  inc r2                     ; delay slot。次の出力行へ進める。
  rpix                       ; PLOTの画素cacheをRAMへflush。読んだ色は使わない。
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
  .endif
mirror_one_check:
  ; 等倍は4出力画素/群、半分は2出力画素/群。余りが出る幅はgenericへ。
  ; 1/4は1出力画素/群なので、幅の剰余検査が不要。
  ibt r8,#3
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_mirror_one)
  jmp (r11)
  nop
mirror_half_check:
  ibt r8,#1
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_mirror_half)
  jmp (r11)
  nop
mirror_quarter_jump:
  iwt r11,#.loword(packed_mirror_quarter)
  jmp (r11)
  nop
packed_double_check:
  ; 2倍は8出力画素/群。R12=0のLOOPはunderflowするので幅8未満はgenericへ。
  ibt r0,#8
  from r9
  cmp r0
  blt generic
  nop
  iwt r11,#.loword(packed_double)
  jmp (r11)
  nop
packed_one_check:
  ibt r8,#3
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_one)
  jmp (r11)
  nop
packed_half_check:
  ibt r8,#1
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_half)
  jmp (r11)
  nop
packed_quarter_jump:
  iwt r11,#.loword(packed_quarter)
  jmp (r11)
  nop
.macro PACKED_GAME name, shift, mirror
  ; shift=0/1/2 → 原画の4画素群から4/2/1画素を出力する。
  ; mirrorは組立時定数。反転の分岐を画素loopへ持ち込まない。
  .local packed_row, packed_pixels
  .export .ident(.concat(.string(name), "_cache"))
name:
  from r10
  .repeat 10
    lsr
  .endrepeat
  ; U0 >> 10 = 原画X >> 2。Q8.8からpackedのbyte位置を求める。
  ; mirrorでは逆bit順の領域を選び、ROM位置を減らしながら読む。
  iwt r8,#(128+32*mirror)
  to r10
  add r8
  iwt r8,#$ff00
  .if shift < 2
    ; 出力幅を群数へ変更。入口で割り切れる幅であることを確認済み。
    from r9
    .repeat 2-shift
      lsr
    .endrepeat
    move r9,r0
  .endif
.ident(.concat(.string(name), "_cache")):
  cache
  iwt r13,#.loword(packed_pixels)
packed_row:
  ; Vの整数部と固定の行内byte位置を合成。横方向のQ8.8更新は不要。
  from r7
  and r8
  to r14
  or r10
  move r1,r5
  move r12,r9
packed_pixels:
  getb                       ; 4原画画素をR0へ一括取得。
  .if mirror
    dec r14
  .else
    inc r14
  .endif
  ; R14を先に進め、次byteのROM待ちをCOLOR/PLOT/LSRと重ねる。
  ; .repeatは組立時に展開。実行時には画素ごとの倍率判定がない。
  .repeat (4>>shift), I
    color                    ; 下位2bitをPLOTの色へ。透明判定はPLOT側。
    .if I = (4>>shift)-1
      loop
      plot
    .else
      plot
      .repeat (2<<shift)
        ; 等倍は2bit、半分は4bit進む。1/4は次byteへ進むのでLSR不要。
        lsr
      .endrepeat
    .endif
  .endrepeat
  with r7
  add r4
  dec r6
  bne packed_row
  inc r2                     ; delay slot。出力Yだけ+1、VはDVで別に進む。
  rpix                       ; 次spriteやDMAの前に、未書込みの画素を確定する。
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
.endmacro
PACKED_GAME packed_one,0,0
PACKED_GAME packed_half,1,0
PACKED_GAME packed_quarter,2,0
PACKED_GAME packed_mirror_one,0,1
PACKED_GAME packed_mirror_half,1,1
PACKED_GAME packed_mirror_quarter,2,1
; 水平2倍専用。4原画画素を1回で取得し、それぞれ2回PLOTする。
; 全体の幅は8以上。末尾1..7出力画素は、次のbyteから同じ2倍規則で描く。
packed_double:
  ibt r8,#7
  from r9
  and r8
  move r11,r0                ; width % 8。末尾の出力画素数。
  from r9
  lsr
  lsr
  lsr
  move r9,r0                 ; width / 8。主loopの群数。
  from r10
  .repeat 10
    lsr
  .endrepeat
  iwt r8,#128
  to r10
  add r8
  iwt r8,#$ff00
.export packed_double_cache
packed_double_cache:
  cache
  iwt r13,#.loword(double_pixels)
double_row:
  from r7
  and r8
  to r14
  or r10
  move r1,r5
  move r12,r9
double_pixels:
  getb
  inc r14                    ; 次の4画素を先読みしながら、現在の4画素を倍化。
  .repeat 4,I
    color
    plot
    .if I=3
      loop
      plot
    .else
      plot
      lsr
      lsr
    .endif
  .endrepeat
  ibt r0,#0
  from r11
  cmp r0
  beq double_next_row
  nop
  move r12,r11
  getb
  ; 端数はpixel単位で終了判定。最大7回を展開し、8画素群とは分ける。
  .repeat 7,I
    .if (I & 1)=0
      color
    .endif
    plot
    dec r12
    beq double_next_row
    nop
    .if (I & 1)=1
      lsr
      lsr
    .endif
  .endrepeat
double_next_row:
  with r7
  add r4
  dec r6
  bne double_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
  .ifdef FX_STABLE_GSU_CACHE
clip_edges:
  .include "gsu_clip_edges.inc"
  .endif
  .ifdef FX_SCALED_ROWS
  .include "gsu_scaled.inc"
  .endif
  .ifdef FX_FAST_UV
uv_slow:
  .include "gsu_uv.inc"
  iwt r8,#.loword(uv_fast_done)
  jmp (r8)
  nop
  .endif
finished:
  rpix                       ; 件数0でも含め、最後の画素cacheをflushする。
  .if .defined(FX_GSU_CLIP) .and .not .defined(FX_FULL_TRANSFER)
  ; 描画を終えた後にだけcacheを切り替える。区間表生成もROM直読みを避ける。
  .align 16,$01
dma_cache:
  .export dma_cache, dma_cache_end
  cache
  ; 既定の部分転送。今回と前回の範囲を結び、消えたspriteの跡も転送する。
  .include "gsu_dma.inc"
dma_cache_end:
  .assert dma_cache_end-dma_cache <= 512, error, "DMA planner cache overflow"
  .endif
  ; CPUへの完了値として元の描画件数をR0へ戻す。STOPでCPUへ所有権を返す。
  iwt r11,#$0000
  ldw (r11)
render_stop:
  stop
  nop
.repeat 22,I
  ; 通常参照+packed+反転packedを含む原画bank。行pitchは全方式で256bytes。
  .segment .sprintf("ASSET%02X",$44+I)
  .incbin .sprintf("assets/bank%02x.bin",$44+I)
.endrepeat
.segment "SCALE5E"
.incbin "assets/scale5e.bin"
  .ifdef FX_SCALED_ROWS
.segment "SPAN5F"
.incbin "assets/scaled5f.bin"
  .endif
