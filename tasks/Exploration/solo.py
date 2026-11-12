# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep
import cv2
from copy import deepcopy
from cached_property import cached_property

from module.logger import logger
from module.base.timer import Timer

from tasks.Component.GeneralInvite.config_invite import InviteConfig, InviteNumber, FindMode
from tasks.Exploration.base import BaseExploration, UpType, Scene
from tasks.Exploration.config import ChooseRarity, AutoRotate, UserStatus


class SoloExploration(BaseExploration):
    INVITE_FLAG_OFF = (157, 109, 83)
    INVITE_FLAG_ON = (227, 193, 153)
    INVITE_TIMEOUT = 20
    FRIEND_LEAVE_TIMEOUT = 3
    SEARCH_SWIPE_INTERVAL = 1.5
    MAX_SWIPE_COUNT = 2
    TAB_SWITCH_MAX_ATTEMPTS = 3
    CLOSE_PANEL_MAX_ATTEMPTS = 3
    INVITE_PANEL_TIMEOUT = 10
    INVITE_PANEL_GRACE = 2
    explore_init = False
    swipe_cnt: int = 0
    search_fail_timer: Timer = None

    @cached_property
    def _invite_config(self) -> InviteConfig:
        return InviteConfig(
            invite_number=InviteNumber.ONE,
            friend_1=self._config.invite_config.friend_1,
            friend_2='',
            find_mode=self._config.invite_config.find_mode,
            wait_time=self._config.invite_config.wait_time,
            default_invite=False
        )

    def _handle_treasure_box(self) -> bool:
        if self.appear(self.I_TREASURE_BOX_CLICK):
            logger.info('Treasure box appear, get it.')
            self.ui_click_until_disappear(self.I_TREASURE_BOX_CLICK)
            return True
        return False

    def _check_mate_leave(self, friend_leave_timer: Timer) -> bool:

        if self.appear(self.I_TEAM_EMOJI) or self.appear(self.I_TEAM_EMOJI_FIGHT):
            # 再次出现则重新计时，进入对局标志消失
            if friend_leave_timer.started():
                logger.warning('Team emoji appear again, clear friend_leave_timer')
                friend_leave_timer.clear()
            return False

        logger.warning('Team emoji not appear')
        if not friend_leave_timer.started():
            logger.warning('Mate leave, start timer')
            friend_leave_timer.start()
            return False
        if not friend_leave_timer.reached():
            return False

        logger.warning('Mate leave timer reached')
        logger.warning('Exit team')
        self.quit_explore()
        return True

    def _reset_search_state(self, reset_swipe_cnt: bool = False) -> None:
        if reset_swipe_cnt:
            if self.swipe_cnt > 0:
                logger.info(f"Exploration search reset (cleared count: {self.swipe_cnt})")
            self.swipe_cnt = 0
        self.search_fail_timer.clear()

    def _search_next_area(self) -> None:
        if not self.search_fail_timer.started():
            self.search_fail_timer.start()
            return
        if not self.search_fail_timer.reached():
            return

        # 若选择特定 UP（如经验怪），达到最大滑屏次数（默认2次，覆盖前3屏高密度区）超时仍无目标直接早退重开；
        # 若选择“全部”，则不限次数滑动直到最右边界，以保证清完全图小怪并击杀 BOSS。
        is_specific_up = self._config.exploration_config.up_type != UpType.ALL
        if is_specific_up and self.swipe_cnt >= self.MAX_SWIPE_COUNT:
            logger.info(f"Max search swipe count ({self.MAX_SWIPE_COUNT}) reached for specific UP target. Quitting exploration early.")
            self._reset_search_state(reset_swipe_cnt=True)
            self.quit_explore()
            return

        before_image = self.device.image
        self.swipe(self.S_SWIPE_BACKGROUND_RIGHT)
        sleep(0.3)
        self.screenshot()
        unchanged = self.is_swipe_unchanged(before_image, self.device.image)
        if unchanged:
            sleep(0.3)
            self.screenshot()
            unchanged = self.is_swipe_unchanged(before_image, self.device.image)

        if (self.get_current_scene() != Scene.MAIN
                or self.appear(self.I_UI_CONFIRM)
                or self.appear(self.I_UI_CONFIRM_SAMLL)):
            self.search_fail_timer.reset()
            return

        # 若未产生位移，原地做快速二次复核保底
        if unchanged:
            sleep(0.3)
            before_retry = self.device.image
            self.swipe(self.S_SWIPE_BACKGROUND_RIGHT)
            sleep(0.3)
            self.screenshot()
            if self.is_swipe_unchanged(before_retry, self.device.image):
                logger.info("Reached rightmost boundary (confirmed twice). Quitting exploration.")
                self._reset_search_state(reset_swipe_cnt=True)
                self.quit_explore()
                return

        self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
        self.swipe_cnt += 1
        self.search_fail_timer.reset()

    def run_solo(self):
        logger.hr('solo')
        self.search_fail_timer = Timer(self.SEARCH_SWIPE_INTERVAL)

        while 1:
            self.screenshot()
            scene = self.get_current_scene()
            logger.info(f'[run_solo] Current scene: {scene.name}')  # TODO 2026.06.22 之后删掉这个刷屏的
            #
            if scene == Scene.WORLD:
                self.explore_init = False
                self._reset_search_state(reset_swipe_cnt=True)
                self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                # 打开右边箭头
                if not self.wait_world_stable():
                    continue
                if self.check_exit():
                    break
                self.open_expect_level()
                continue
            #
            elif scene == Scene.ENTRANCE:
                self.explore_init = False
                self._reset_search_state(reset_swipe_cnt=True)
                self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                if self.check_exit():
                    break
                self.ui_click(self.I_E_EXPLORATION_CLICK, stop=self.I_E_SETTINGS_BUTTON)
                continue
            #
            elif scene == Scene.MAIN:
                if not self.explore_init:
                    if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                        self.enter_settings_and_do_operations()
                    self.ui_click(self.I_E_AUTO_ROTATE_OFF, stop=self.I_E_AUTO_ROTATE_ON, timeout=5)
                    self.explore_init = True
                    self._reset_search_state(reset_swipe_cnt=True)
                    continue
                if self._handle_treasure_box():
                    self._reset_search_state()
                    continue
                if (self.appear_then_click(self.I_UI_CONFIRM, interval=1)
                        or self.appear_then_click(self.I_UI_CONFIRM_SAMLL, interval=1)):
                    self._reset_search_state()
                    continue
                # 小纸人
                if self.appear(self.I_BATTLE_REWARD):
                    if self.ui_get_reward(self.I_BATTLE_REWARD):
                        self._reset_search_state()
                        continue
                # boss
                if self.appear(self.I_BOSS_BATTLE_BUTTON):
                    self._reset_search_state()
                    self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                    if self.fire(self.I_BOSS_BATTLE_BUTTON):
                        logger.info(f'Boss battle, minions cnt {self.minions_cnt}')
                    continue
                # 小怪
                fight_button = self.search_up_fight()
                if fight_button is not None:
                    self._reset_search_state()
                    self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                    if self.fire(fight_button):
                        logger.info(f'Fight, minions cnt {self.minions_cnt}')
                    continue
                # 向后拉,寻找怪
                self._search_next_area()
                continue
            #
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                self.check_take_over_battle(is_screenshot=False, config=self._config.general_battle_config)
            elif scene == Scene.UNKNOWN:
                continue

    def run_leader(self):
        logger.hr('leader')
        self.search_fail_timer = Timer(self.SEARCH_SWIPE_INTERVAL)
        friend_leave_timer = Timer(self.FRIEND_LEAVE_TIMEOUT)

        while 1:
            self.screenshot()
            scene = self.get_current_scene()
            # 探索大世界
            if scene == Scene.WORLD:
                self.explore_init = False
                self._reset_search_state(reset_swipe_cnt=True)
                self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                # 打开右边箭头
                if not self.wait_world_stable():
                    continue
                if self.check_exit():
                    self.wait_until_stable(self.I_UI_CANCEL, timer=Timer(0.6, 2))
                    if self.appear(self.I_UI_CANCEL):
                        self.ui_click_until_disappear(self.I_UI_CANCEL)
                    break
                if self.appear(self.I_UI_CONFIRM):
                    self.ui_click_until_disappear(self.I_UI_CONFIRM)
                    # 可以加一下，清空第一次 explore_init
                    continue
                self.open_expect_level()
                # explore_init = False
                continue

            # 邀请好友, 非常有可能是后面邀请好友，然后直接跳到组队了
            elif scene == Scene.ENTRANCE:
                self.explore_init = False
                self._reset_search_state(reset_swipe_cnt=True)
                self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                while 1:
                    self.screenshot()
                    if self.is_in_room():
                        break
                    if self.appear_then_click(self.I_ENSURE_PRIVATE_FALSE, interval=0.5):
                        continue
                    if self.appear_then_click(self.I_ENSURE_PRIVATE_FALSE_2, interval=0.5):
                        continue
                    # 创建在组队前，组队蒙层后概率会被误识别
                    if self.appear_then_click(self.I_EXP_CREATE_ENSURE, interval=2):
                        continue
                    if self.appear_then_click(self.I_EXP_CREATE_TEAM, interval=1):
                        continue
            #
            elif scene == Scene.TEAM:
                self.explore_init = False
                self._reset_search_state(reset_swipe_cnt=True)
                # 队友已进房时加号本来就不存在，不能只用加号判断房间是否就绪
                # 等待加号或挑战按钮渲染完成，再决定是邀请还是开战
                timeout = Timer(10)
                timeout.start()
                while 1:
                    self.screenshot()
                    if self.appear(self.I_ADD_2) or self.appear(self.I_FIRE):
                        break
                    if timeout.reached():
                        logger.warning('Wait team room timeout')
                        break
                if self.appear(self.I_FIRE, threshold=0.8) and not self.appear(self.I_ADD_2):
                    self.ui_click_until_disappear(self.I_FIRE, interval=1)
                    continue
                if self.appear(self.I_ADD_2) and self.run_invite(config=self._invite_config, is_first=True):
                    continue
                logger.warning('Invite failed, quit')
                self._quit_team_room()
                break
            ##
            elif scene == Scene.MAIN:
                if not self.explore_init:
                    if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                        self.enter_settings_and_do_operations()
                    self.ui_click(self.I_E_AUTO_ROTATE_OFF, stop=self.I_E_AUTO_ROTATE_ON)
                    self.explore_init = True
                    self._reset_search_state(reset_swipe_cnt=True)
                    continue
                if self._handle_treasure_box():
                    self._reset_search_state()
                    continue
                if (self.appear_then_click(self.I_UI_CONFIRM, interval=1)
                        or self.appear_then_click(self.I_UI_CONFIRM_SAMLL, interval=1)):
                    self._reset_search_state()
                    continue
                # 小纸人
                if self.appear(self.I_BATTLE_REWARD):
                    if self.ui_get_reward(self.I_BATTLE_REWARD):
                        self._reset_search_state()
                        continue
                # 中途有人跑路
                if self._check_mate_leave(friend_leave_timer):
                    self._reset_search_state()
                    continue
                # boss
                if self.appear(self.I_BOSS_BATTLE_BUTTON):
                    self._reset_search_state()
                    self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                    if self.fire(self.I_BOSS_BATTLE_BUTTON):
                        logger.info(f'Boss battle, minions cnt {self.minions_cnt}')
                    continue
                # 小怪
                fight_button = self.search_up_fight()
                if fight_button is not None:
                    self._reset_search_state()
                    self.device.click_record_remove(self.S_SWIPE_BACKGROUND_RIGHT.name)
                    if self.fire(fight_button):
                        logger.info(f'Fight, minions cnt {self.minions_cnt}')
                    continue
                # 向后拉,寻找怪
                self._search_next_area()
                continue
            #
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                self.check_take_over_battle(is_screenshot=False, config=self._config.general_battle_config)
            elif scene == Scene.UNKNOWN:
                continue

    def run_member(self):
        logger.hr('member')
        wait_timer = Timer(50)
        friend_leave_timer = Timer(self.FRIEND_LEAVE_TIMEOUT)

        while 1:
            self.screenshot()
            scene = self.get_current_scene()
            logger.info(f'[run_member] Current scene: {scene.name}')  # TODO 2026.06.12 之后删掉这个刷屏的
            #
            if scene == Scene.WORLD:
                # 打开右边箭头
                if not self.wait_world_stable():
                    continue
                if self.check_exit():
                    break
                if self.check_then_accept():
                    # 接受邀请后清掉计时器
                    wait_timer.clear()
                    continue
                if wait_timer.started() and wait_timer.reached():
                    logger.warning('Wait timer reached')
                    break

                continue
            #
            elif scene == Scene.ENTRANCE:
                self.ui_click(self.I_UI_BACK_YELLOW,stop=self.I_CHECK_EXPLORATION)
            #
            elif scene == Scene.TEAM:
                continue
            #
            elif scene == Scene.MAIN:
                if not self.explore_init:
                    if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                        self.enter_settings_and_do_operations()
                    self.ui_click(self.I_E_AUTO_ROTATE_OFF, stop=self.I_E_AUTO_ROTATE_ON)
                    self.explore_init = True
                    continue
                if self._handle_treasure_box():
                    continue
                # 小纸人
                if self.appear(self.I_BATTLE_REWARD):
                    if self.ui_get_reward(self.I_BATTLE_REWARD):
                        continue
                #
                if self._check_mate_leave(friend_leave_timer):
                    wait_timer.reset()
                    continue
            #
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                logger.info('[run_member] Handling scene: BATTLE')
                self.check_take_over_battle(is_screenshot=False, config=self._config.general_battle_config)
            elif scene == Scene.UNKNOWN:
                continue

    def _invite_panel_open(self) -> bool:
        """
        邀请好友面板是否已经打开
        """
        return self.appear(self.I_INVITE_ENSURE) or self.appear(self.I_LOAD_FRIEND)

    def _open_invite_panel(self) -> str:
        """
        点击加号打开邀请好友面板
        :return: open 面板已打开, joined 队友已经进房, timeout 超时
        """
        logger.info('Click add to invite friend')
        add_clicked = False
        add_click_cnt = 0
        max_add_click = 3
        grace_timer = Timer(self.INVITE_PANEL_GRACE)
        timeout = Timer(self.INVITE_PANEL_TIMEOUT)
        timeout.start()
        while 1:
            self.screenshot()
            if self._invite_panel_open():
                return 'open'
            if add_click_cnt < max_add_click and self.appear_then_click(self.I_ADD_2, interval=1):
                add_clicked = True
                add_click_cnt += 1
                continue
            if add_click_cnt < max_add_click and self.appear_then_click(self.I_ADD_5_4, interval=1):
                add_clicked = True
                add_click_cnt += 1
                continue
            if add_clicked and not self.appear(self.I_ADD_2) and not self.appear(self.I_ADD_5_4):
                # 加号消失：可能是面板正在弹出，也可能队友已经进房，等待一段时间再确认
                if not grace_timer.started():
                    grace_timer.start()
                if grace_timer.reached():
                    self.screenshot()
                    if self._invite_panel_open():
                        return 'open'
                    if not self.appear(self.I_ADD_2) and not self.appear(self.I_ADD_5_4):
                        logger.info('Add button disappeared, teammate maybe joined')
                        self.device.click(x=370, y=480, control_name='exploration_invite_friend_prevent')
                        return 'joined'
            if timeout.reached():
                logger.warning('Invite panel not appear')
                return 'timeout'

    def _close_invite_panel(self) -> None:
        """
        关闭邀请好友面板，避免任务停留在邀请界面
        """
        if not self._invite_panel_open():
            return
        logger.info('Close invite panel')
        for _ in range(self.CLOSE_PANEL_MAX_ATTEMPTS):
            self.screenshot()
            if not self._invite_panel_open():
                return
            x, y = self.I_INVITE_ENSURE.coord()
            self.device.click(x=x, y=y, control_name=self.I_INVITE_ENSURE.name)
            sleep(1)
        self.screenshot()
        if not self._invite_panel_open():
            return
        # 没有选中好友时点“邀请”不会关闭列表，点“取消”退出
        for _ in range(self.CLOSE_PANEL_MAX_ATTEMPTS):
            self.device.click(x=474, y=580, control_name='exploration_invite_cancel')
            sleep(1)
            self.screenshot()
            if not self._invite_panel_open():
                return
        logger.warning('Close invite panel failed')

    def _friend_tab_on_flags(self) -> list:
        """
        第 2 个标签的 ON 资源 roi 被改到了标签栏上方的空白区(#1844)，深拷贝并还原成 #1443 的 roi
        """
        flag_2_on = deepcopy(self.I_FLAG_2_ON)
        flag_2_on.roi_front = [471, 128, 54, 18]
        flag_2_on.roi_back = (471, 128, 54, 18)
        return [self.I_FLAG_1_ON, flag_2_on, self.I_FLAG_3_ON, self.I_FLAG_4_ON]

    def _tab_is_active(self, flag_on) -> bool:
        """
        标签是否处于选中态。match_mean_color 默认使用扩展 2px 的 roi_back，
        会把标签边框算进均值导致选中态判断恒为 False，这里显式使用紧凑的 roi_front
        """
        mean = cv2.mean(flag_on.corp(self.device.image, flag_on.roi_front))[:3]
        return all(abs(mean[i] - self.INVITE_FLAG_ON[i]) <= 10 for i in range(3))

    def _switch_friend_tab(self, index: int) -> bool:
        """
        切换到指定好友标签，点击次数有上限，避免 GameTooManyClickError
        """
        flag_on = self._friend_tab_on_flags()[index]
        flag_off = [self.I_FLAG_1_OFF, self.I_FLAG_2_OFF, self.I_FLAG_3_OFF, self.I_FLAG_4_OFF][index]
        for attempt in range(self.TAB_SWITCH_MAX_ATTEMPTS):
            self.screenshot()
            if self._tab_is_active(flag_on):
                return True
            if attempt:
                sleep(0.8)
            x, y = flag_off.coord()
            self.device.click(x=x, y=y, control_name=flag_off.name)
        self.screenshot()
        if self._tab_is_active(flag_on):
            return True
        logger.warning(f'Switch friend tab failed: {flag_off.name}')
        return False

    def _quit_team_room(self) -> None:
        """
        退出组队房间回到探索界面。会处理“确认退出探索吗？”弹窗，
        并对每个按钮的点击次数设置上限，避免无限连点触发 GameTooManyClickError
        """
        logger.info('Quit team room')
        if self._invite_panel_open():
            self._close_invite_panel()
        timeout = Timer(20)
        timeout.start()
        max_click = 3
        confirm_cnt = back_red_cnt = back_yellow_cnt = 0
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_EXPLORATION):
                break
            if timeout.reached():
                logger.warning('Quit team room timeout')
                break
            if confirm_cnt < max_click and self.appear_then_click(self.I_E_EXIT_CONFIRM, interval=1):
                confirm_cnt += 1
                continue
            if confirm_cnt < max_click and self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                confirm_cnt += 1
                continue
            if back_red_cnt < max_click and self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                back_red_cnt += 1
                continue
            if back_yellow_cnt < max_click and self.appear_then_click(self.I_UI_BACK_YELLOW, interval=1):
                back_yellow_cnt += 1
                continue
            sleep(0.2)

    def invite_friend(self, name: str = None, find_mode: FindMode = FindMode.AUTO_FIND) -> bool:
        open_result = self._open_invite_panel()
        if open_result == 'joined':
            return True
        if open_result != 'open':
            return False

        friend_class = []
        class_ocr = [self.O_F_LIST_1, self.O_F_LIST_2, self.O_F_LIST_3, self.O_F_LIST_4]
        class_index = 0
        list_1 = self.O_F_LIST_1.ocr(self.device.image)
        list_2 = self.O_F_LIST_2.ocr(self.device.image)
        list_3 = self.O_F_LIST_3.ocr(self.device.image)
        list_4 = self.O_F_LIST_4.ocr(self.device.image)
        list_1 = list_1.replace(' ', '').replace('、', '')
        list_2 = list_2.replace(' ', '').replace('、', '')
        list_3 = list_3.replace(' ', '').replace('、', '')
        if list_1 is not None and list_1 != '' and list_1 in self.friend_class:
            friend_class.append(list_1)
        if list_2 is not None and list_2 != '' and list_2 in self.friend_class:
            friend_class.append(list_2)
        if list_3 is not None and list_3 != '' and list_3 in self.friend_class:
            friend_class.append(list_3)
        if list_4 is not None and list_4 != '' and list_4 in self.friend_class:
            friend_class.append(list_4)
        for i in range(len(friend_class)):
            if friend_class[i] == '蔡友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '路区':
                friend_class[i] = '跨区'
            elif friend_class[i] == '察友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '区':
                friend_class[i] = '跨区'
        logger.info(f'Friend class: {friend_class}')

        is_select: bool = False  # 是否选中了好友
        if find_mode == FindMode.RECENT_FRIEND:
            logger.info('Find recent friend')
            if '最近' not in friend_class:
                # 探索好友列表没有“最近”标签，退化为自动查找，不能直接返回并把面板留在界面上
                logger.warning('No recent friend tab, fallback to auto find')
                find_mode = FindMode.AUTO_FIND
            else:
                recent_index = friend_class.index('最近')
                self._switch_friend_tab(recent_index)
                logger.info('Now find friend in ”最近“')
                sleep(1)
                if self.detect_select(name):
                    is_select = True
                sleep(1)
                if not is_select and self.detect_select(name):
                    is_select = True

        for index in range(len(friend_class)):
            # 如果不是自动寻找，就跳过
            if find_mode != FindMode.AUTO_FIND:
                continue
            # 如果已经选中了好友，就不需要再选中了
            if is_select:
                continue
            # 首先切换到不同的好友列表
            if not self._switch_friend_tab(index):
                continue

            # 选中好友， 在这里游戏获取在线的好友并不是很快，根据不同的设备会有不同的时间，而且没有什么元素提供我们来判断
            # 所以这里就直接等待一段时间
            logger.info(f'Now find friend in {friend_class[index]}')
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True

        # 点击邀请
        logger.info('Click invite ensure')
        if not self.appear(self.I_INVITE_ENSURE):
            logger.warning('No appear invite ensure while invite friend')
        for _ in range(self.CLOSE_PANEL_MAX_ATTEMPTS):
            self.screenshot()
            if not self._invite_panel_open():
                break
            x, y = self.I_INVITE_ENSURE.coord()
            self.device.click(x=x, y=y, control_name=self.I_INVITE_ENSURE.name)
            sleep(1)
        if not is_select:
            logger.warning('No find friend')
            self._close_invite_panel()
            logger.info('Task failed')
            return False
        if self._invite_panel_open():
            self._close_invite_panel()
        return True


class ScriptTask(SoloExploration):
    def run(self):
        logger.hr('exploration')
        random_click_cnt = 0
        while 1:
            self.screenshot()
            scene = self.get_current_scene()
            if random_click_cnt >= 2:
                break
            if scene == Scene.UNKNOWN:
                logger.warning('Unknown scene, random click')
                if self.click(self.C_SAFE_RANDOM, interval=1.5):
                    random_click_cnt += 1
                continue
            else:
                break

        if scene == Scene.UNKNOWN:
            self.pre_process()

        match self._config.exploration_config.user_status:
            case UserStatus.ALONE:
                self.run_solo()
            case UserStatus.LEADER:
                self.run_leader()
            case UserStatus.MEMBER:
                self.run_member()
            case _:
                self.run_solo()

        self.post_process()


if __name__ == "__main__":
    from module.config.config import Config
    from module.device.device import Device

    config = Config('oas1')
    device = Device(config)
    t = ScriptTask(config, device)
    t.run()
