#ifndef MSXSH_MONOSH_STAGE_H
#define MSXSH_MONOSH_STAGE_H

#ifdef __ROM__
#define MONOSH_STAGE_BANKED __banked
#else
#define MONOSH_STAGE_BANKED
#endif

void monosh_stage_init(void) MONOSH_STAGE_BANKED;
unsigned char monosh_stage_frame(void) MONOSH_STAGE_BANKED;
void monosh_stage_render_only(void) MONOSH_STAGE_BANKED;
unsigned char monosh_stage_is_clear(void) MONOSH_STAGE_BANKED;

#endif
