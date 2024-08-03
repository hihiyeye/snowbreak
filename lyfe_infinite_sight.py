import functools

DEFAULT_ATTACK_VAL = 4617  # 攻击力，专武1，3后勤+12且无百分比攻击词条
WEAPON_MATCH_RATE = 0.182  # 专武适配率，固定值
DEFAULT_CRITICAL_RATE = 0.5  # 打弱点比例（打弱点必定暴击）
DEFAULT_SAME_TONE = 300.  # 同调

DEFAULT_MISSING_RATE = 0.  # 跳弹率


# 同调加成的闪射最终伤害乘区
def calc_skill_shooting_final_damage(same_tone):
    return same_tone * (0.1 / 100) + 1.0


# x: 子弹数，y: 实战中闪射值满了之后额外消耗的子弹, z：所需要的闪射值，天启2后只需要40点
# calc_e_cnt_by_bullets = lambda x, y, z=60: x // (z / 4 + y)


def damage_model_based_on_bullets():
    """基于子弹数的伤害模型
    """
    pass


def damage_model_based_on_flash_cnt(
        flash_cnt, needed_flash_val, wasted_bullets_num,
        raw_attack_val=DEFAULT_ATTACK_VAL,
        extra_attack_percent=0.,
        same_tone=DEFAULT_SAME_TONE,
        critical_rate=DEFAULT_CRITICAL_RATE,
        extra_critical_rate=0.,
        extra_critical_damage=0.,
        missing_rate=DEFAULT_MISSING_RATE):
    """基于闪射次数的伤害模型
    假设子弹全部打中敌人。且省去一些相同/相等乘区。
    伤害组成为：闪射射击伤害 + e技能伤害（1个标记） + 直射伤害
    伤害计算公式参考：https://www.bilibili.com/video/BV1Jb4y157Lo

    :param flash_cnt: 闪射次数
    :param needed_flash_val: 闪射值，2天启之前为60，2天启之后为40
    :param wasted_bullets_num: 到达满闪射值之后继续射击溢出的子弹数(手部乘区)
    :param raw_attack_val: 不加后勤百分比攻击的攻击力
    :param extra_attack_percent: 后勤攻击力百分比
    :param same_tone: 同调
    :param critical_rate: 打弱点比例（手部乘区）
    :param extra_critical_rate: 后勤暴击率
    :param extra_critical_damage: 后勤暴击伤害增幅
    :param missing_rate: 跳弹率
    :return: 总伤害，闪射伤害，非闪射的射击伤害
    """
    attack_val = raw_attack_val * (1.0 + extra_attack_percent)

    flash_shooting_cnt = flash_cnt * 10  # 闪射子弹数
    """ 常规技
    里芙-无限之视移动速度和战术闪避速度更快，且每次射击命中目标会获得3【闪射值】，若命中带有【瞬析】标记的目标则会额外获得1【闪射值】
    """
    raw_shooting_cnt = flash_cnt * (needed_flash_val / 4 + wasted_bullets_num)  # 直接射击子弹数

    """ 同调技能
    闪射值积累至60后，里芙下次战术闪避消耗全部闪射值并获得效果:战术闪避消耗体力降低50%，
    消耗10发子弹进行闪射，造成10次必定暴击的136%的射击伤害(每有100同调指数,则每次闪射的射击最终伤害提升10%)，
    若子弹不足，则闪射的最终伤害降低50%
    """
    """ 常规技
    每有1%暴击率，闪射的射击伤害提升1%;射击速度每提升1%，闪射的射击伤害提升1%
    """
    # 闪射伤害
    # 双枪冲锋枪暴击伤害为30%
    flash_shooting_dmg = \
        attack_val * flash_shooting_cnt * (1.36 + extra_critical_rate) * (1.0 + 0.30 * (1.0 + extra_critical_damage)) * \
        calc_skill_shooting_final_damage(same_tone)

    flash_shooting_dmg *= WEAPON_MATCH_RATE

    # 快速移动、瞬析射线(1个标记)
    skill_dmg = flash_cnt * (0.1 * attack_val + 11) + (0.4 * attack_val + 21)

    # 直射伤害
    # 非跳弹次数
    valid_raw_shooting_cnt = raw_shooting_cnt * (1.0 - missing_rate)
    # 打弱点次数
    critical_shooting_cnt = valid_raw_shooting_cnt * critical_rate
    # 打非弱点暴击次数
    extra_critical_shooting_cnt = (valid_raw_shooting_cnt - critical_shooting_cnt) * extra_critical_rate

    raw_shooting_dmg = attack_val * \
        ((critical_shooting_cnt + extra_critical_shooting_cnt) * (1.0 + 0.30 * (1.0 + extra_critical_damage))
         + (valid_raw_shooting_cnt - critical_shooting_cnt - extra_critical_shooting_cnt) * 1.0)

    raw_shooting_dmg *= WEAPON_MATCH_RATE

    return round(flash_shooting_dmg + raw_shooting_dmg + skill_dmg, 2), round(flash_shooting_dmg, 2), round(raw_shooting_dmg, 2)


if __name__ == '__main__':
    fixed_flash_cnt = 20
    # for critical_rate in [0.1 * _ for _ in range(1, 11)]:
    for critical_rate in [0.2, 0.4, 0.6, 0.8]:
        print("=" * 50)
        wasted_bullets_num = 3
        calc_dmg_func = functools.partial(damage_model_based_on_flash_cnt, fixed_flash_cnt, 40, wasted_bullets_num,
                                          critical_rate=critical_rate)

        print("打弱点比例（手部乘区）：", critical_rate)
        print("平均每轮闪射浪费子弹数：", wasted_bullets_num)

        # 300同调，额外暴击、爆伤为0
        based_dmg = calc_dmg_func()
        print("基准伤害：", based_dmg)
        print("计算模型省略很多相同的伤害乘区，只能比较不同词条之间的相对提升比例")
        print("后面2个小数为闪射伤害、直射伤害占比")

        dmg_same_tone_400 = calc_dmg_func(same_tone=400)
        dmg_attack_percent_10 = calc_dmg_func(extra_attack_percent=0.1)
        dmg_extra_critical_damage_10 = calc_dmg_func(extra_critical_damage=0.1)
        dmg_extra_critical_rate_5 = calc_dmg_func(extra_critical_rate=0.05)

        dmg_percents = [(round(x[1] / x[0], 4), round(x[2] / x[0], 4)) for x in (
            dmg_same_tone_400, dmg_attack_percent_10, dmg_extra_critical_damage_10, dmg_extra_critical_rate_5
        )]

        print("额外100同调：{}, {} {}\n额外10%攻击：{}, {} {}\n额外10%爆伤增幅：{}, {} {}\n额外5%暴击：{}, {} {}".format(
            dmg_same_tone_400, dmg_percents[0][0], dmg_percents[0][1],
            dmg_attack_percent_10, dmg_percents[1][0], dmg_percents[1][1],
            dmg_extra_critical_damage_10,dmg_percents[2][0], dmg_percents[2][1],
            dmg_extra_critical_rate_5, dmg_percents[3][0], dmg_percents[3][1],))

        print('-' * 5)
        dmg_list = []
        for i in range(9, 0, -1):
            dmg_tmp = calc_dmg_func(extra_attack_percent=0.01 * i)
            dmg_list.append(dmg_tmp)
            # print("额外攻击百分比{}%：".format(i), dmg_tmp,
            #       "占比：{} {}".format(round(dmg_tmp[1] / dmg_tmp[0], 4), round(dmg_tmp[2] / dmg_tmp[0], 4)))

        # 线性相关，计算等效攻击百分比
        _calc_percent = lambda a, b: 8 / (a[0][0] - a[-1][0]) * (b[0] - a[-1][0]) + 1
        print("100同调大约为：{}%攻击".format(round(_calc_percent(dmg_list, dmg_same_tone_400), 2)))
        print("10爆伤增幅大约为：{}%攻击".format(round(_calc_percent(dmg_list, dmg_extra_critical_damage_10), 2)))
        print("5暴击大约为：{}%攻击".format(round(_calc_percent(dmg_list, dmg_extra_critical_rate_5), 2)))

