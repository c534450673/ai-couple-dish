package com.aicoupledish;

import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Bug Fix Verification Tests
 * 
 * Tests to verify that the model-database mismatches are fixed.
 */
@SpringBootTest
public class BugFixVerificationTest {

    @Autowired
    private CoupleMenuMapper coupleMenuMapper;
    
    @Autowired
    private AnniversaryMapper anniversaryMapper;
    
    @Autowired
    private WishMapper wishMapper;
    
    @Autowired
    private FoodNoteMapper foodNoteMapper;
    
    @Autowired
    private CoupleMapper coupleMapper;
    
    @Autowired
    private DailyGreetingMapper dailyGreetingMapper;
    
    @Autowired
    private MoodRecordMapper moodRecordMapper;
    
    @Autowired
    private CoupleTreeMapper coupleTreeMapper;

    @Test
    void testCoupleMenuMapper_NoExtraFields() {
        // This test verifies that CoupleMenu can be queried without errors
        // The issue was: Unknown column 'photo_urls' in 'field list'
        List<CoupleMenu> menus = coupleMenuMapper.selectList(null);
        assertNotNull(menus);
    }
    
    @Test
    void testAnniversaryMapper_NoExtraFields() {
        // This test verifies that Anniversary can be queried without errors
        // The issue was: Unknown column 'is_lunar_date' in 'field list'
        List<Anniversary> anniversaries = anniversaryMapper.selectList(null);
        assertNotNull(anniversaries);
    }
    
    @Test
    void testWishMapper_NoExtraFields() {
        // This test verifies that Wish can be queried without errors
        // The issue was: Unknown column 'viewer_id' in 'field list'
        List<Wish> wishes = wishMapper.selectList(null);
        assertNotNull(wishes);
    }
    
    @Test
    void testFoodNoteMapper_NoExtraFields() {
        // This test verifies that FoodNote can be queried without errors
        List<FoodNote> notes = foodNoteMapper.selectList(null);
        assertNotNull(notes);
    }
    
    @Test
    void testCoupleMapper_NoExtraFields() {
        // This test verifies that Couple can be queried without errors
        List<Couple> couples = coupleMapper.selectList(null);
        assertNotNull(couples);
    }
    
    @Test
    void testDailyGreetingMapper_NoExtraFields() {
        // This test verifies that DailyGreeting can be queried without errors
        List<DailyGreeting> greetings = dailyGreetingMapper.selectList(null);
        assertNotNull(greetings);
    }
    
    @Test
    void testMoodRecordMapper_NoExtraFields() {
        // This test verifies that MoodRecord can be queried without errors
        List<MoodRecord> moods = moodRecordMapper.selectList(null);
        assertNotNull(moods);
    }
    
    @Test
    void testCoupleTreeMapper_NoExtraFields() {
        // This test verifies that CoupleTree can be queried without errors
        List<CoupleTree> trees = coupleTreeMapper.selectList(null);
        assertNotNull(trees);
    }
}
