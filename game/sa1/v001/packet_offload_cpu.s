; 自機OBJは本体で準備し、ソフト描画用命令のソート・変換をSA-1へ渡す。
.setcpu "65816"
.smart
.import fx_build_obj, _fx_draw_count, _fx_packet_count, pipe_records
.export _fx_build_packet
.export packet_count_collect: far
.segment "CODE"
.a8
.i8
_fx_build_packet:
  php
  rep #$30
  jsr fx_build_obj
  lda _fx_draw_count
  and #255
  sta _fx_packet_count
  plp
  rts
.segment "GSU"
.a16
.i16
packet_count_collect:
  rep #$30
  lda f:$003106
  sta pipe_records+16,x
  rtl
