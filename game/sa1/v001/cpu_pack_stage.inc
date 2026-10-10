.export pipe_stage_convert: far, pipe_stage_done: far, stage_busy, stage_too_large: far
.export stage_time_ok: far, stage_converted: far, stage_record
.segment "BSS"
stage_read_slot: .res 2
stage_busy: .res 2
stage_record: .res 2
stage_desc: .res 2
stage_end: .res 2
stage_bank: .res 2
stage_output: .res 2
stage_map_index: .res 2
stage_tile: .res 2
stage_length: .res 2
stage_line: .res 2
stage_cost: .res 2
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
  lda pipe_records+34,x
  cmp #$34e1
  jcs stage_too_large
  ; 変換量に応じて所要時間を予約し、VIRQ前に終わる処理だけ開始する。
  sta stage_cost
  lsr
  lsr
  lsr
  lsr
  clc
  adc stage_cost
  adc #1900
  sta stage_cost
  lda pipe_records+2,x
  asl
  sta stage_line
  asl
  asl
  clc
  adc stage_line
  adc stage_cost
  sta stage_cost
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  sta stage_line
  lda f:$00213d
  and #1
  sta stage_line+1
  rep #$20
  lda stage_line
  cmp #203
  bcs stage_time_ok
  lda #196
  sec
  sbc stage_line
  jmi pipe_stage_done
  sta stage_line
  asl
  asl
  clc
  adc stage_line
  asl
  asl
  clc
  adc stage_line
  asl
  asl
  clc
  adc stage_line
  asl
  cmp stage_cost
  jcc pipe_stage_done
stage_time_ok:
  lda pipe_records+2,x
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
  lda #$cb20
  sta stage_output
  lda #33
  sta stage_tile
  ; mapは毎回空タイルへ初期化。先頭32Bは透明なCHR。
  ldx #0
  lda #0
stage_zero:
  sta a:$cb00,x
  inx
  inx
  cpx #32
  bcc stage_zero
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
  lda stage_bank
  and #$8400
  sta f:$002232
  sep #$20
  lda stage_bank
  sta f:$002234
  rep #$20
  lda #SA1_CC_BUFFER
  sta f:$002235
  lda #$cb20
  sta f:$002181
  lda #$8000
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda stage_bank
  sta f:$004304
  rep #$20
stage_descriptor:
  ldx stage_desc
  cpx stage_end
  jcs stage_converted
  lda pipe_records,x
  sta stage_length
  sta f:$004305
  lda pipe_records+2,x
  sta f:$004302
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  lda stage_output
  clc
  adc stage_length
  sta stage_output
  lda stage_desc
  clc
  adc #6
  sta stage_desc
  jmp stage_descriptor
stage_converted:
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
  lda stage_bank
  and #$8400
  clc
  adc #$6040
  sta f:$004302
  lda #$c500
  sta f:$002181
  lda #1472
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  lda #0
  sta f:$002200
  rep #$20
  lda #0
  sta f:$00311e
  ldx stage_record
  lda #$007e
  sta pipe_records,x
  lda #12
  sta pipe_records+2,x
  lda stage_output
  sec
  sbc #$cb00
  sta pipe_records+208,x
  clc
  adc #1472
  sta pipe_records+34,x
  lda #$cb00
  sta pipe_records+210,x
  lda #512
  sta pipe_records+212,x
  lda #1472
  sta pipe_records+214,x
  lda #$c500
  sta pipe_records+216,x
  lda #$6020
  sta pipe_records+218,x
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
  rtl
stage_too_large:
  ; 越境する絵は必ず検証で止める。RAMを破壊して続行しない。
  stp
.segment "CODE"
