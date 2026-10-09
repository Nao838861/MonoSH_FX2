; 完成bitmapの変更領域をWRAM 7e:a000..ffffへ直接変換して保持する。
; PPU転送は通常WRAM→VRAM DMAになり、SA-1描画用DMAを占有しない。
.export pipe_stage_convert, pipe_stage_done, stage_busy
.segment "BSS"
stage_read_slot: .res 2
stage_busy: .res 2
stage_record: .res 2
stage_desc: .res 2
stage_end: .res 2
stage_bank: .res 2
.segment "CODE"
pipe_stage_convert:
  rep #$30
  lda stage_busy
  jne pipe_stage_done
  lda stage_read_slot
  asl
  tax
  lda pipe_status,x
  cmp #2
  jne pipe_stage_done
  lda stage_read_slot
  .repeat 9
    asl
  .endrepeat
  sta stage_record
  tax
  lda pipe_records+38,x
  jne pipe_stage_done
  lda pipe_records+2,x
  jeq stage_publish
  clc
  adc stage_record
  adc #208
  sta stage_end
  lda stage_record
  clc
  adc #208
  sta stage_desc
  lda pipe_records,x
  sta stage_bank
  lda #0
  sta f:$00311c
  lda #1
  sta f:$00311e
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
stage_grant:
  lda f:$00311c
  cmp #2
  bne stage_grant
  sep #$20
  lda #$15
  sta f:$002231
  rep #$20
  lda #0
  sta f:$002232
  sep #$20
  lda stage_bank
  sta f:$002234
  rep #$20
  lda #SA1_CC_BUFFER
  sta f:$002235
stage_descriptor:
  ldx stage_desc
  lda pipe_records,x
  sta f:$004305
  lda pipe_records+2,x
  sta f:$004302
  clc
  adc #$a000
  sta pipe_records+2,x
  sta f:$002181
  lda #$8000                  ; DMAP=00, BBAD=80: BW→WRAM port
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda stage_bank
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
  lda stage_desc
  clc
  adc #6
  sta stage_desc
  cmp stage_end
  jne stage_descriptor
  sep #$20
  lda #$95
  sta f:$002231
  lda #0
  sta f:$002200
  rep #$20
  lda #0
  sta f:$00311e
stage_publish:
  ldx stage_record
  lda #1
  sta pipe_records+38,x
  sta stage_busy
  lda stage_read_slot
  inc
  cmp #SA1_PIPELINE_DEPTH
  bcc :+
  lda #0
:
  sta stage_read_slot
pipe_stage_done:
  rep #$30
  rts
