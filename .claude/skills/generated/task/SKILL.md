---
name: task
description: "Skill for the Task area of ai-couple-dish. 37 symbols across 23 files."
---

# Task

37 symbols | 23 files | Cohesion: 64%

## When to Use

- Working with code in `backend/`
- Understanding how SweetBomb, MoodRecord, handleExpiredFeeds work
- Modifying task-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | morningGreetingReminder, nightGreetingReminder, sendGreetingReminder, hasSentGreetingToday, streakBreakReminder (+1) |
| `backend/src/main/java/com/aicoupledish/task/AnniversaryReminderTask.java` | sendReminderToUsers, buildReminderContent, checkAnniversaryReminders, checkAndSendReminder, calculateNextAnniversaryDate |
| `backend/src/main/java/com/aicoupledish/common/utils/LunarCalendarUtils.java` | getLunarYearDays, getLeapMonthDays, getLeapMonth, lunarToSolar, getNextLunarDate |
| `backend/src/test/java/com/aicoupledish/LunarCalendarUtilsTest.java` | lunarToSolar_SpringFestival2024, getNextLunarDate |
| `backend/src/test/java/com/aicoupledish/NotificationServiceTest.java` | sendNotification_Success |
| `backend/src/test/java/com/aicoupledish/NoteServiceTest.java` | commentNote_NoteExists_ShouldSuccess |
| `backend/src/main/java/com/aicoupledish/task/FeedExpireTask.java` | handleExpiredFeeds |
| `backend/src/main/java/com/aicoupledish/service/SweetBombService.java` | generateBomb |
| `backend/src/main/java/com/aicoupledish/service/NotificationService.java` | sendNotification |
| `backend/src/main/java/com/aicoupledish/service/NoteService.java` | commentNote |

## Entry Points

Start here when exploring this area:

- **`SweetBomb`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/SweetBomb.java:11`
- **`MoodRecord`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/MoodRecord.java:12`
- **`handleExpiredFeeds`** (Method) — `backend/src/main/java/com/aicoupledish/task/FeedExpireTask.java:32`
- **`morningGreetingReminder`** (Method) — `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java:41`
- **`nightGreetingReminder`** (Method) — `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java:51`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `SweetBomb` | Class | `backend/src/main/java/com/aicoupledish/dao/model/SweetBomb.java` | 11 |
| `MoodRecord` | Class | `backend/src/main/java/com/aicoupledish/dao/model/MoodRecord.java` | 12 |
| `handleExpiredFeeds` | Method | `backend/src/main/java/com/aicoupledish/task/FeedExpireTask.java` | 32 |
| `morningGreetingReminder` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 41 |
| `nightGreetingReminder` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 51 |
| `sendGreetingReminder` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 61 |
| `hasSentGreetingToday` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 97 |
| `streakBreakReminder` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 110 |
| `checkAndSendStreakReminder` | Method | `backend/src/main/java/com/aicoupledish/task/DailyGreetingTask.java` | 144 |
| `sendReminderToUsers` | Method | `backend/src/main/java/com/aicoupledish/task/AnniversaryReminderTask.java` | 146 |
| `buildReminderContent` | Method | `backend/src/main/java/com/aicoupledish/task/AnniversaryReminderTask.java` | 192 |
| `generateBomb` | Method | `backend/src/main/java/com/aicoupledish/service/SweetBombService.java` | 14 |
| `sendNotification` | Method | `backend/src/main/java/com/aicoupledish/service/NotificationService.java` | 38 |
| `commentNote` | Method | `backend/src/main/java/com/aicoupledish/service/NoteService.java` | 50 |
| `sendMood` | Method | `backend/src/main/java/com/aicoupledish/service/MoodRecordService.java` | 15 |
| `recoverCoupleData` | Method | `backend/src/main/java/com/aicoupledish/service/CoupleService.java` | 68 |
| `generateBomb` | Method | `backend/src/main/java/com/aicoupledish/controller/SweetBombController.java` | 29 |
| `commentNote` | Method | `backend/src/main/java/com/aicoupledish/controller/NoteController.java` | 86 |
| `sendMood` | Method | `backend/src/main/java/com/aicoupledish/controller/MoodRecordController.java` | 31 |
| `recoverCoupleData` | Method | `backend/src/main/java/com/aicoupledish/controller/CoupleController.java` | 120 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `GetTodayEvents → GetLeapMonth` | cross_community | 9 |
| `GetCalendar → GetLeapMonth` | cross_community | 8 |
| `GetEventsByDate → GetLeapMonth` | cross_community | 8 |
| `GetUpcomingEvents → GetLeapMonth` | cross_community | 8 |
| `GetYearOverview → GetLeapMonth` | cross_community | 8 |
| `GetEventsByDateRange → GetLeapMonth` | cross_community | 7 |
| `GetTodayEvents → GetLunarMonthDays` | cross_community | 7 |
| `GetCalendar → GetLunarMonthDays` | cross_community | 6 |
| `GetEventsByDate → GetLunarMonthDays` | cross_community | 6 |
| `GetUpcomingEvents → GetLunarMonthDays` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Controller | 8 calls |
| Impl | 6 calls |
| Aicoupledish | 3 calls |
| Exception | 2 calls |
| Dto | 1 calls |

## How to Explore

1. `gitnexus_context({name: "SweetBomb"})` — see callers and callees
2. `gitnexus_query({query: "task"})` — find related execution flows
3. Read key files listed above for implementation details
