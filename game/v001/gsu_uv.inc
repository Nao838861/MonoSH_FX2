; wireの生寸法・整数skipを、既存shaderのQ8.8レジスタへ変換する。
; scratch: $A bank/meta, $10 height, $12 base V, $14 skip Y。
; 入口: R3/R4=clip前のwidth/height、R10=左で捨てた出力画素数、
;       R7上位byte=原画ペアのbase V、下位byte=上で捨てた出力行数。
; DU/DVは原画寸法*256/投影寸法。ROM $5eの表を読むので実行時の除算なし。
; table: DU=$0000+asset*512+width*2、DV=$5800+asset*512+height*2。
; clip後の幅に合わせて倍率を変えると絵が歪むので、元寸法で表を引く。
  .ifdef FX_SCALED_ROWS
  iwt r8,#$001a
  from r3
  stw (r8)                 ; 元幅。横clipのないspan経路だけに使う。
  .endif
  .ifndef FX_STABLE_GSU_CACHE
.export gsu_uv_cache
gsu_uv_cache:
  .ifndef FX_4BPP
  cache
  .endif                   ; 4bppでは連続するボスの描画loopのcacheを維持する。
  iwt r8,#$000a
  stw (r8)                 ; r0はbank/meta。ROMBは下7bitだけを読む。
  .endif                   ; 安定cache構成ではclip入口が既にbank/metaを保存済み。
  iwt r8,#$0010
  from r6
  stw (r8)
  iwt r8,#$0012
  iwt r13,#$ff00
  from r7
  and r13
  stw (r8)
  iwt r8,#$0014
  iwt r13,#$00ff
  from r7
  and r13
  stw (r8)
  iwt r8,#$000a
  ldw (r8)
  swap
  iwt r8,#$00ff
  and r8
  move r11,r0              ; meta
  ibt r8,#63
  and r8
  swap                     ; asset<64なのでbitは重ならない。*256の後に*2。
  add r0
  move r12,r0              ; asset*512
  ibt r0,#$5e
  romb
  from r3
  add r3
  to r14
  add r12
  getb
  inc r14
  getbh
  move r3,r0               ; DU
  from r4
  add r4
  add r12
  iwt r8,#$5800
  to r14
  add r8
  getb
  inc r14
  getbh
  move r4,r0               ; DV
  ; clipのskipはspriteごとにLMULTで投影。画素loop中の乗算を省く。
  ; LMULTはR0*R6の32bit積を出し、低16bitはR4。DVをR13へ一時退避する。
  move r13,r4
  move r6,r3
  from r10
  lmult                    ; U0=skip X*DU、low16はR4
  move r10,r4
  move r4,r13
  ibt r8,#64
  from r11
  and r8
  beq uv_u_done
  nop
  ; 左右反転: DU=-DU、U0=原画width*256-1-skipX*abs(DU)。
  ; -1で原画の右端を選び、小数部$ffを持つ。packed入口判定もこれに対応。
  ibt r0,#0
  to r3
  sub r3
  ibt r8,#63
  from r11
  and r8
  iwt r8,#$b000
  to r14
  add r8
  getb
  swap
  dec r0
  to r10
  sub r10
uv_u_done:
  move r13,r4
  move r6,r4
  iwt r8,#$0014
  ldw (r8)
  lmult                    ; V skipもlow16だけを使う。
  move r7,r4
  move r4,r13
  ibt r8,#$80
  from r11
  and r8
  beq uv_v_done
  nop
  ; 上下反転も同じ規則。原画heightは$b02c+assetの表から読む。
  ibt r0,#0
  to r4
  sub r4
  ibt r8,#63
  from r11
  and r8
  iwt r8,#$b02c
  to r14
  add r8
  getb
  swap
  dec r0
  to r7
  sub r7
uv_v_done:
  ; 後半原画のbase V=$8000を合成し、clip後heightと原画bankを復元する。
  iwt r8,#$0012
  ldw (r8)
  move r8,r0
  with r7
  .ifdef FX_4BPP
  .if FX4_COLOR
  add r8                  ; 任意の行位置へ配置した色周期原画のbase V。
  .else
  or r8
  .endif
  .else
  or r8
  .endif
  iwt r8,#$0010
  to r6
  ldw (r8)
  iwt r8,#$000a
  ldw (r8)
  romb
