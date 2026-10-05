#ifndef MSXSH_MONOSH_BOSS_DATA_H
#define MSXSH_MONOSH_BOSS_DATA_H

extern const unsigned char monosh_boss_path_z[240];
extern const unsigned char monosh_boss_path_x[240];
extern const unsigned char monosh_boss_path_center_y[240];
extern const unsigned char monosh_boss_path_z_mid[240];
extern const unsigned char monosh_boss_path_x_mid[240];
extern const unsigned char monosh_boss_path_center_y_mid[240];
extern const unsigned char monosh_boss_draw_order_base[2160];
extern const unsigned char monosh_boss_draw_order_mid[2160];
/* Interleaved width,height records indexed by logical Z. */
extern const unsigned char monosh_boss_face_geometry[222];
extern const unsigned char monosh_boss_body_geometry[222];
extern const unsigned char monosh_boss_bom_geometry[222];
extern const unsigned char monosh_boss_bullet_velocity[3328];
extern const unsigned char monosh_boss_bom_depth_by_size[16];
extern const unsigned char monosh_boss_explosion_scale_low[111];
extern const unsigned char monosh_boss_explosion_ground_bottom[111];

#endif
