.export fb_sa1_restore: far
  ; 転送元はWRAM port、転送先はBW-RAM。CCは生データの読み戻しまで停止する。
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
  ldx pipe_record_offset
  lda pipe_records,x
  and #$8400
  sta f:$0031bc
  lda #fbCombined
  sta f:$002181
  lda #$8080
  sta f:$004300
  lda #$3400
  sta f:$004302
  lda #96
  sta f:$004305
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
  lda #1
  sta f:$0031a0
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
fb_sa1_wait:
  lda f:$0031a0
  bne fb_sa1_wait
  ldx pipe_record_offset
  lda f:$0031a4
  sta pipe_records+34,x
  lda f:$0031a2
  asl
  sta fbCount
  asl
  clc
  adc fbCount
  sta pipe_records+2,x
  sta f:$004305
  stz pipe_records+4,x
  beq fb_sa1_restore
  txa
  clc
  adc #pipe_records+208
  sta f:$002181
  lda #$3500
  sta f:$004302
  lda #$8000
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda #1
  sta f:$00420b
  rep #$20
fb_sa1_restore:
  ; 以後は元の画像をCC type1でVRAMへ送る。
  lda pipe_records,x
  and #$8400
  sta f:$002232
  sep #$20
  lda pipe_records,x
  sta f:$002234
  sta f:$004304
  lda #$15
  sta f:$002231
  rep #$20
  lda #$02e0
  sta f:$002235
  lda #$1801
  sta f:$004300
  rtl
