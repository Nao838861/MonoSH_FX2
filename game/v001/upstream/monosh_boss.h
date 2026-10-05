#ifndef MSXSH_MONOSH_BOSS_H
#define MSXSH_MONOSH_BOSS_H

#ifdef __ROM__
#define MONOSH_BOSS_BANKED __banked
#else
#define MONOSH_BOSS_BANKED
#endif

#define MONOSH_BOSS_STAGE  0u
#define MONOSH_BOSS_ACTIVE 1u
#define MONOSH_BOSS_DYING  2u
#define MONOSH_BOSS_DONE   3u

extern unsigned char monosh_boss_state;
extern unsigned char monosh_boss_hp;
extern unsigned char boss_last_vblank;
unsigned char monosh_boss_should_restart(void) MONOSH_BOSS_BANKED;

void monosh_boss_init(void) MONOSH_BOSS_BANKED;
void monosh_boss_frame(unsigned char stage_ready,
                       signed int player_x,
                       signed int player_bottom) MONOSH_BOSS_BANKED;
void monosh_boss_frame_prepare(unsigned char stage_ready,
                               signed int player_x,
                               signed int player_bottom) MONOSH_BOSS_BANKED;
void monosh_boss_prepare_render(void) MONOSH_BOSS_BANKED;
void monosh_boss_render_only(void);

#endif
