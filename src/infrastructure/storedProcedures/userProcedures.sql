CREATE OR REPLACE FUNCTION get_user_statistics(
    p_faculty_id INT DEFAULT NULL,
    p_department_id INT DEFAULT NULL,
    p_year_id INT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_two_hours_ago TIMESTAMP;
    v_this_month_start TIMESTAMP;
    
    v_total_users INT;
    v_users_this_month INT;
    v_percentage_increase INT;
    v_active_now INT;
    v_pending_users_count INT;
    v_last_five_users_active JSON;
    
    v_result JSON;
BEGIN
    -- 1. Setup Timeframes (UTC alignment)
    v_two_hours_ago := NOW() AT TIME ZONE 'UTC' - INTERVAL '2 hours';
    v_this_month_start := DATE_TRUNC('month', NOW() AT TIME ZONE 'UTC');

    -- 2. Get Total Users matching filters
    SELECT COUNT(id) INTO v_total_users
    FROM users
    WHERE (p_faculty_id IS NULL OR faculty_id = p_faculty_id)
      AND (p_department_id IS NULL OR department_id = p_department_id)
      AND (p_year_id IS NULL OR year_id = p_year_id);

    -- 3. Get Users Registered This Month matching filters
    SELECT COUNT(id) INTO v_users_this_month
    FROM users
    WHERE (p_faculty_id IS NULL OR faculty_id = p_faculty_id)
      AND (p_department_id IS NULL OR department_id = p_department_id)
      AND (p_year_id IS NULL OR year_id = p_year_id)
      AND created_at >= v_this_month_start;

    -- 4. Calculate Percentage Increase (Ceil logic applied)
    IF (v_total_users - v_users_this_month) > 0 THEN
        v_percentage_increase := CEIL(((v_users_this_month::NUMERIC / (v_total_users - v_users_this_month)) * 100));
    ELSE
        v_percentage_increase := 0;
    END IF;

    -- 5. Calculate Active Now (Unique users tracking via request_limits within filtered user group)
    SELECT COUNT(DISTINCT rl.user_id) INTO v_active_now
    FROM request_limits rl
    JOIN users u ON rl.user_id = u.id
    WHERE rl.user_id IS NOT NULL
      AND rl.created_at >= v_two_hours_ago
      AND (p_faculty_id IS NULL OR u.faculty_id = p_faculty_id)
      AND (p_department_id IS NULL OR u.department_id = p_department_id)
      AND (p_year_id IS NULL OR u.year_id = p_year_id);

    -- 6. Retrieve Last 5 Active Avatars (Fixed sorting pattern via CTE)
    SELECT COALESCE(JSON_AGG(active_avatars.avatar), '[]'::json) INTO v_last_five_users_active
    FROM (
        SELECT COALESCE(u.details->>'avatar', u.google_avatar) AS avatar
        FROM (
            -- Get the 5 most recently active user IDs uniquely
            SELECT rl.user_id, MAX(rl.created_at) as max_time
            FROM request_limits rl
            JOIN users u ON rl.user_id = u.id
            WHERE rl.user_id IS NOT NULL
              AND rl.created_at >= v_two_hours_ago
              AND (p_faculty_id IS NULL OR u.faculty_id = p_faculty_id)
              AND (p_department_id IS NULL OR u.department_id = p_department_id)
              AND (p_year_id IS NULL OR u.year_id = p_year_id)
            GROUP BY rl.user_id
            ORDER BY max_time DESC
            LIMIT 5
        ) recent_ids
        JOIN users u ON u.id = recent_ids.user_id
    ) active_avatars;

    -- 7. Get Pending Users Count
    SELECT COUNT(pu.id) INTO v_pending_users_count
    FROM pending_users pu
    JOIN users u ON u.id = pu.user_id
    WHERE u.faculty_id IS NOT NULL
      AND u.department_id IS NOT NULL
      AND u.year_id IS NOT NULL
      AND u.type IS NOT NULL
      AND u.type <> ''
      AND u.status = FALSE
      AND (p_faculty_id IS NULL OR u.faculty_id = p_faculty_id)
      AND (p_department_id IS NULL OR u.department_id = p_department_id)
      AND (p_year_id IS NULL OR u.year_id = p_year_id);

    -- 8. Build final structured payload matching your exact schema output
    v_result := JSON_BUILD_OBJECT(
        'users_count', v_total_users,
        'users_this_month', v_users_this_month,
        'percentage_increase', v_percentage_increase,
        'active_now', v_active_now,
        'pending_users_count', v_pending_users_count,
        'last_five_users_active', v_last_five_users_active
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;