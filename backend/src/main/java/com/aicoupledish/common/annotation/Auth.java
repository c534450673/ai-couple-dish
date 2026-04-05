package com.aicoupledish.common.annotation;

import java.lang.annotation.*;

/**
 * Annotation to mark methods or classes that require authentication.
 *
 * When applied to a method, the method will only be accessible to authenticated users.
 * When applied to a class, all public methods in the class will require authentication.
 *
 * Usage:
 * <pre>
 * // Require authentication for a single method
 * {@code @Auth}
 * {@code @PostMapping("/user/profile")}
 * public Result<UserProfileDTO> getUserProfile() { ... }
 *
 * // Require authentication for all methods in a class
 * {@code @Auth}
 * {@code @RestController}
 * public class UserController { ... }
 *
 * // Require specific role
 * {@code @Auth(roles = {"ADMIN", "USER"})}
 * {@code @PostMapping("/admin/settings")}
 * public Result<Void> updateSettings() { ... }
 * </pre>
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Auth {

    /**
     * Specifies whether authentication is required.
     * Default is true. Set to false to explicitly mark a method as public
     * even when the class is annotated with {@code @Auth}.
     */
    boolean required() default true;

    /**
     * Specifies required roles for access.
     * If empty, any authenticated user can access the resource.
     * This setting only applies when authentication is required.
     *
     * @return array of required role names
     */
    String[] roles() default {};
}
