package com.aicoupledish.common.utils;

import com.aicoupledish.common.enums.BusinessException;

/**
 * Phone number validation utility.
 * Single source of truth for phone format validation.
 */
public final class PhoneValidationUtils {

    private static final String PHONE_REGEX = "^1[3-9]\\d{9}$";

    private PhoneValidationUtils() {
        // prevent instantiation
    }

    /**
     * Validates phone number format. Throws BusinessException if invalid.
     */
    public static void validatePhoneFormat(String phone) {
        if (phone == null || !phone.matches(PHONE_REGEX)) {
            throw BusinessException.PARAM_INVALID;
        }
    }

    /**
     * Returns true if the phone number matches the expected format.
     */
    public static boolean isValidPhone(String phone) {
        return phone != null && phone.matches(PHONE_REGEX);
    }
}
