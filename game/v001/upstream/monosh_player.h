#ifndef MSXSH_MONOSH_PLAYER_H
#define MSXSH_MONOSH_PLAYER_H

#define MONOSH_PLAYER_ALIVE        0u
#define MONOSH_PLAYER_DEATH_AIR    1u
#define MONOSH_PLAYER_DEATH_GROUND 2u

extern signed int monosh_player_x;
extern signed int monosh_player_bottom;
extern unsigned char monosh_player_state;
extern unsigned char monosh_player_invuln;
extern unsigned char monosh_player_stumble;
extern unsigned char monosh_player_pose;
extern unsigned char monosh_stage_title_timer;

void monosh_player_init(void);
void monosh_player_update(unsigned char input, unsigned char hit);
unsigned char monosh_player_draw_flags(void);
unsigned char monosh_player_world_active(void);
unsigned char monosh_player_can_fire(void);
unsigned char monosh_player_draw_asset(void);

#endif
