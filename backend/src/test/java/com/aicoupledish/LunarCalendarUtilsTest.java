package com.aicoupledish;

import com.aicoupledish.common.utils.LunarCalendarUtils;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 农历工具类测试
 */
@DisplayName("农历工具类测试")
class LunarCalendarUtilsTest {

    @Test
    @DisplayName("阳历转农历-2024年春节")
    void solarToLunar_SpringFestival2024() {
        // 2024年2月10日是春节（农历正月初一）
        LocalDate solarDate = LocalDate.of(2024, 2, 10);
        int[] lunarDate = LunarCalendarUtils.solarToLunar(solarDate);

        assertNotNull(lunarDate);
        assertEquals(4, lunarDate.length);
        assertEquals(2024, lunarDate[0]);  // 年
        assertEquals(1, lunarDate[1]);     // 月
        assertEquals(1, lunarDate[2]);     // 日
    }

    @Test
    @DisplayName("阳历转农历-2024年元旦")
    void solarToLunar_NewYear2024() {
        LocalDate solarDate = LocalDate.of(2024, 1, 1);
        int[] lunarDate = LunarCalendarUtils.solarToLunar(solarDate);

        assertNotNull(lunarDate);
        assertEquals(2023, lunarDate[0]);  // 年
        assertEquals(11, lunarDate[1]);    // 月
        assertEquals(20, lunarDate[2]);    // 日
    }

    @Test
    @DisplayName("农历转阳历-2024年春节")
    void lunarToSolar_SpringFestival2024() {
        LocalDate solarDate = LunarCalendarUtils.lunarToSolar(2024, 1, 1, false);
        assertNotNull(solarDate);
        // 农历2024年正月初一对应阳历日期
        assertEquals(2, solarDate.getMonthValue());
        assertEquals(10, solarDate.getDayOfMonth());
    }

    @Test
    @DisplayName("获取干支年名称")
    void getLunarYearName() {
        String ganZhi = LunarCalendarUtils.getLunarYearName(2024);
        assertNotNull(ganZhi);
        assertEquals(2, ganZhi.length());
    }

    @Test
    @DisplayName("获取生肖")
    void getShengXiao() {
        String zodiac = LunarCalendarUtils.getShengXiao(2024);
        assertNotNull(zodiac);
        assertEquals("龙", zodiac);
    }

    @Test
    @DisplayName("获取生肖-蛇年")
    void getShengXiao_Snake() {
        String zodiac = LunarCalendarUtils.getShengXiao(2025);
        assertEquals("蛇", zodiac);
    }

    @Test
    @DisplayName("获取生肖-马年")
    void getShengXiao_Horse() {
        String zodiac = LunarCalendarUtils.getShengXiao(2026);
        assertEquals("马", zodiac);
    }

    @Test
    @DisplayName("判断是否是农历节日-春节")
    void getLunarHoliday_SpringFestival() {
        String festival = LunarCalendarUtils.getLunarHoliday(1, 1);
        assertEquals("春节", festival);
    }

    @Test
    @DisplayName("判断是否是农历节日-元宵节")
    void getLunarHoliday_LanternFestival() {
        String festival = LunarCalendarUtils.getLunarHoliday(1, 15);
        assertEquals("元宵节", festival);
    }

    @Test
    @DisplayName("判断是否是农历节日-端午节")
    void getLunarHoliday_DragonBoat() {
        String festival = LunarCalendarUtils.getLunarHoliday(5, 5);
        assertEquals("端午节", festival);
    }

    @Test
    @DisplayName("判断是否是农历节日-中秋节")
    void getLunarHoliday_MidAutumn() {
        String festival = LunarCalendarUtils.getLunarHoliday(8, 15);
        assertEquals("中秋节", festival);
    }

    @Test
    @DisplayName("非农历节日")
    void getLunarHoliday_NotFestival() {
        String festival = LunarCalendarUtils.getLunarHoliday(3, 15);
        assertNull(festival);
    }

    @Test
    @DisplayName("获取下一次农历日期")
    void getNextLunarDate() {
        LocalDate nextDate = LunarCalendarUtils.getNextLunarDate(1, 1);
        assertNotNull(nextDate);
        // 应该是未来的日期
        assertTrue(nextDate.isAfter(LocalDate.now()) || nextDate.isEqual(LocalDate.now()));
    }
}
