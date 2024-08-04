import fractions
import functools

BASED_ATTACK_VAL = 2709  # 基础攻击力
FIXED_ATTACK_PERCENT = 0.75  # 专武1 3后勤+12
COMMON_DAMAGE_RAISED_PERCENT = 0.18 + 0.24 + 0.085*3  # 专武1+后勤2件套+第3词条
SKILL_DAMAGE_RAISED_PERCENT = 0.75  # 后勤3件套效果
WEAPON_MATCH_RATE = 0.182  # 专武适配率，固定值
DEFAULT_CRITICAL_RATE = 0.5  # 打弱点比例（打弱点必定暴击）
DEFAULT_SAME_TONE = 300.  # 同调

DEFAULT_MISSING_RATE = 0.  # 跳弹率


# 同调加成的闪射最终伤害乘区
# 1天启之后闪射+20%最终伤害
def calc_flash_shooting_final_damage(same_tone):
    return same_tone * (0.1 / 100) + 1.36


# x: 子弹数，y: 实战中闪射值满了之后额外消耗的子弹, z：所需要的闪射值，天启2后只需要40点
# calc_e_cnt_by_bullets = lambda x, y, z=60: x // (z / 4 + y)


def damage_model_based_on_bullets():
    """基于子弹数的伤害模型
    """
    pass


def damage_model_based_on_flash_cnt(
        flash_cnt, needed_flash_val, wasted_bullets_num, e_percent,
        based_attack_val=BASED_ATTACK_VAL,
        fixed_attack_percent=FIXED_ATTACK_PERCENT,
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
    :param based_attack_val: 基础攻击力（不加攻击力百分比）
    :param fixed_attack_percent:
    :param extra_attack_percent: 后勤攻击力百分比
    :param same_tone: 同调
    :param critical_rate: 打弱点比例（手部乘区）
    :param extra_critical_rate: 后勤暴击率
    :param extra_critical_damage: 后勤暴击伤害增幅
    :param missing_rate: 跳弹率
    :return: 总伤害，闪射伤害，非闪射的射击伤害
    """
    attack_val = based_attack_val * (1.0 + fixed_attack_percent + extra_attack_percent)

    flash_shooting_cnt = flash_cnt * 10  # 闪射子弹数

    skill_e_cnt = flash_cnt * e_percent  # e技能打出的闪射数
    shooting_flash_cnt = flash_cnt - skill_e_cnt  # 常规射击打出的闪射数

    """ 常规技
    里芙-无限之视移动速度和战术闪避速度更快，且每次射击命中目标会获得3【闪射值】，若命中带有【瞬析】标记的目标则会额外获得1【闪射值】
    """
    raw_shooting_cnt = shooting_flash_cnt * (needed_flash_val / 4 + wasted_bullets_num)  # 直接射击子弹数

    """ 同调技能 （bilibili wiki与游戏类描述不一致）
    闪射值积累至60后，里芙下次战术闪避消耗全部闪射值并获得效果:战术闪避消耗体力降低50%，
    消耗10发子弹进行闪射，造成10次必定暴击的伤害，最终伤害提升至常规射击伤害的136%(每有100同调指数,则每次闪射的射击最终伤害提升10%)，
    若子弹不足，则闪射的最终伤害降低50%
    """
    """ 常规技
    每有1%暴击率，闪射的射击伤害提升1%;射击速度每提升1%，闪射的射击伤害提升1%
    """
    # 闪射伤害
    # 双枪冲锋枪暴击伤害为30%
    flash_shooting_dmg = \
        attack_val * flash_shooting_cnt * (1.0 + 0.30 * (1.0 + extra_critical_damage))

    flash_shooting_dmg *= WEAPON_MATCH_RATE
    # 暴击转换的闪射伤害在增伤区
    flash_shooting_dmg *= extra_critical_rate \
                          + (1.0 + COMMON_DAMAGE_RAISED_PERCENT + SKILL_DAMAGE_RAISED_PERCENT)
    # TODO: 此处同调技能和1天启为2个独立乘区
    flash_shooting_dmg *= calc_flash_shooting_final_damage(same_tone)
    flash_shooting_dmg *= 1.2  # 1天启+20%最终伤害

    # e技能伤害
    # 快速移动、瞬析射线(1个标记)
    skill_dmg_raised_percent = (1.0 + COMMON_DAMAGE_RAISED_PERCENT + SKILL_DAMAGE_RAISED_PERCENT)
    # 快速（使用e时才有） + 瞬析（闪射子弹击中就有）
    skill_dmg = skill_e_cnt * (0.1 * attack_val * skill_dmg_raised_percent + 11) \
                + flash_shooting_cnt * (0.4 * attack_val * skill_dmg_raised_percent + 21)

    # 常规射击伤害
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
    raw_shooting_dmg *= (1.0 + COMMON_DAMAGE_RAISED_PERCENT)

    return round(flash_shooting_dmg + raw_shooting_dmg + skill_dmg, 2), \
           round(flash_shooting_dmg, 2), \
           round(raw_shooting_dmg, 2)


def calc_equal_attack_percent_same_tone(dmg_same_tone, dmg_base, dmg_attack_percent_max, attack_func):
    if dmg_same_tone <= dmg_base:
        return 0
    if dmg_same_tone >= dmg_attack_percent_max:
        return 10

    low, high = 0, 1000

    while low < high:
        mid = (low + high) // 2
        dmg_mid = attack_func(extra_attack_percent=mid*0.01*0.01)

        if 1.0 - 1e-4 < (dmg_mid[0] / dmg_same_tone) < 1.0 + 1e-4:
            return mid

        if dmg_mid[0] < dmg_same_tone:
            low = mid + 1
        else:
            high = mid
    return low


if __name__ == '__main__':
    fixed_flash_cnt = 45
    csv_data = []
    for critical_rate in [0.1 * _ for _ in range(1, 11)]:
    # for critical_rate in [0.2, 0.4, 0.6, 0.8]:
        print("=" * 50)
        needed_flash_val_ = 40
        wasted_bullets_num_ = 1.75
        e_percent_ = fractions.Fraction(1, 5)
        calc_dmg_func = functools.partial(damage_model_based_on_flash_cnt,
                                          fixed_flash_cnt,
                                          needed_flash_val_,
                                          wasted_bullets_num_,
                                          e_percent_,
                                          critical_rate=critical_rate)

        print("打弱点比例（手部乘区）：", critical_rate)
        print("一次闪射需要积累的闪射值：", needed_flash_val_)
        print("平均每轮闪射浪费子弹数：", wasted_bullets_num_)
        print("e技能冷却打出的闪射比：{} / {}".format(1, round(e_percent_.denominator / e_percent_.numerator,2)))

        # 300同调，额外暴击、爆伤为0
        based_dmg = calc_dmg_func()
        print("基准伤害：", based_dmg,
              ", {} {}".format(round(based_dmg[1] / based_dmg[0], 4), round(based_dmg[2] / based_dmg[0], 4)))
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
        _calc_equivalent_atk_percent = lambda a, b: 8 / (a[0][0] - a[-1][0]) * (b[0] - a[-1][0]) + 1
        equivalent_atk_percents = [
            round(_calc_equivalent_atk_percent(dmg_list, dmg_same_tone_400), 2),
            round(_calc_equivalent_atk_percent(dmg_list, dmg_extra_critical_damage_10), 2),
            round(_calc_equivalent_atk_percent(dmg_list, dmg_extra_critical_rate_5), 2)
        ]
        print("100同调大约为：{}%攻击".format(equivalent_atk_percents[0]))
        print("10爆伤增幅大约为：{}%攻击".format(equivalent_atk_percents[1]))
        print("5暴击大约为：{}%攻击".format(equivalent_atk_percents[2]))

        # print(calc_equal_attack_percent_same_tone(
        #     dmg_same_tone_400[0], based_dmg[0], dmg_attack_percent_10[0], calc_dmg_func))

        csv_data.append(equivalent_atk_percents)

    """
    with open('./results.csv', 'w') as fp:
        for i in range(len(csv_data)):
            fp.write(','.join([str(_) for _ in [(i + 1) * 0.1] + csv_data[i]]) + '\n')
    """
