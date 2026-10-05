#ifndef MSXSH_MONOSH_ENEMY_H
#define MSXSH_MONOSH_ENEMY_H

#ifdef __ROM__
#define MONOSH_ENEMY_BANKED __banked
#else
#define MONOSH_ENEMY_BANKED
#endif

void monosh_enemy_init(void) MONOSH_ENEMY_BANKED;
unsigned char monosh_enemy_frame(void) MONOSH_ENEMY_BANKED;
void monosh_enemy_render_only(void) MONOSH_ENEMY_BANKED;
unsigned char monosh_enemy_active_count(void) MONOSH_ENEMY_BANKED;
unsigned char monosh_enemy_stage_complete(void) MONOSH_ENEMY_BANKED;
extern unsigned char monosh_enemy_bullet_count;
extern unsigned char monosh_enemy_active_count_value;
extern unsigned char monosh_enemy_stage_complete_flag;
void monosh_enemy_fire_at(unsigned char virtual_x,
                          unsigned char bottom,
                          unsigned char z) MONOSH_ENEMY_BANKED;
unsigned char monosh_enemy_fire_boss_at(unsigned char virtual_x,
                                        unsigned char bottom,
                                        unsigned char z) MONOSH_ENEMY_BANKED;

#endif
