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
      AND u.study_type IS NOT NULL
      AND u.study_type <> ''
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

CREATE OR REPLACE FUNCTION get_user_with_details(
    p_user_id INT
)
RETURNS JSON AS $$
DECLARE
    v_user_json JSON;
    v_user_registered_subject_ids INT[];
    
    v_tasks_published JSON;
    v_tasks JSON;
    v_exams_published JSON;
    v_exams JSON;
    v_announcements_published JSON;
    v_announcements JSON;
    v_materials JSON;
    v_subjects JSON;
    v_events JSON;
    v_logs JSON;
    
    v_result JSON;
BEGIN
    -- 1. Fetch user with nested faculty, department, year, and role
    SELECT JSON_BUILD_OBJECT(
        'id', u.id,
        'name', u.name,
        'email', u.email,
        'phone', u.phone,
        'status', u.status,
        'gender', u.gender,
        'section', u.section,
        'is_early_access', u.is_early_access,
        'details', u.details,
        'google_id', u.google_id,
        'google_name', u.google_name,
        'google_email', u.google_email,
        'google_avatar', u.google_avatar,
        'study_type', u.study_type,
        'created_at', u.created_at,
        'updated_at', u.updated_at,
        'faculty', CASE WHEN f.id IS NOT NULL THEN JSON_BUILD_OBJECT('id', f.id, 'name', f.name) ELSE NULL END,
        'department', CASE WHEN d.id IS NOT NULL THEN JSON_BUILD_OBJECT('id', d.id, 'name', d.name) ELSE NULL END,
        'year', CASE WHEN y.id IS NOT NULL THEN JSON_BUILD_OBJECT('id', y.id, 'year', y.year) ELSE NULL END,
        'role', CASE WHEN r.id IS NOT NULL THEN JSON_BUILD_OBJECT('id', r.id, 'name', r.name) ELSE NULL END,
        'avatar', CASE WHEN u.avatar_id IS NOT NULL THEN JSON_BUILD_OBJECT('id', a.id, 'url', a.url, 'details', a.details) ELSE NULL END
    ) INTO v_user_json
    FROM users u
    LEFT JOIN faculties f ON f.id = u.faculty_id
    LEFT JOIN departments d ON d.id = u.department_id
    LEFT JOIN years y ON y.id = u.year_id
    LEFT JOIN roles r ON r.id = u.role_id
    LEFT JOIN attachments a ON a.id = u.avatar_id
    WHERE u.id = p_user_id;

    IF v_user_json IS NULL THEN
        RETURN NULL;
    END IF;

    -- 2. Fetch user's registered subject IDs into an array
    SELECT ARRAY_AGG(subject_id) INTO v_user_registered_subject_ids
    FROM user_subject_links
    WHERE user_id = p_user_id;

    -- 3. Tasks Published (author_id = p_user_id AND task_type = 'task')
    SELECT COALESCE(JSON_AGG(t_pub), '[]'::json) INTO v_tasks_published
    FROM (
        SELECT 
            t.id, t.name, t.task_type, t.deadline, t.details, t.created_at, t.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM tasks t
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.author_id = p_user_id 
          AND t.task_type = 'task'
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT 5
    ) t_pub;

    -- 4. Tasks (In registered subjects AND task_type = 'task')
    SELECT COALESCE(JSON_AGG(t_reg), '[]'::json) INTO v_tasks
    FROM (
        SELECT 
            t.id, t.name, t.task_type, t.deadline, t.details, t.created_at, t.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM tasks t
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.subject_id = ANY(v_user_registered_subject_ids)
          AND t.task_type = 'task'
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT 5
    ) t_reg;

    -- 5. Exams Published (author_id = p_user_id AND task_type = 'exam')
    SELECT COALESCE(JSON_AGG(e_pub), '[]'::json) INTO v_exams_published
    FROM (
        SELECT 
            t.id, t.name, t.task_type, t.deadline, t.details, t.created_at, t.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM tasks t
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.author_id = p_user_id 
          AND t.task_type = 'exam'
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT 5
    ) e_pub;

    -- 6. Exams (In registered subjects AND task_type = 'exam')
    SELECT COALESCE(JSON_AGG(e_reg), '[]'::json) INTO v_exams
    FROM (
        SELECT 
            t.id, t.name, t.task_type, t.deadline, t.details, t.created_at, t.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM tasks t
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.subject_id = ANY(v_user_registered_subject_ids)
          AND t.task_type = 'exam'
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT 5
    ) e_reg;

    -- 7. Announcements Published (author_id = p_user_id)
    SELECT COALESCE(JSON_AGG(a_pub), '[]'::json) INTO v_announcements_published
    FROM (
        SELECT 
            a.id, a.title, a.content, a.date, a.details, a.created_at, a.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM announcements a
        JOIN subjects s ON s.id = a.subject_id
        WHERE a.author_id = p_user_id
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT 5
    ) a_pub;

    -- 8. Announcements (In registered subjects)
    SELECT COALESCE(JSON_AGG(a_reg), '[]'::json) INTO v_announcements
    FROM (
        SELECT 
            a.id, a.title, a.content, a.date, a.details, a.created_at, a.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM announcements a
        JOIN subjects s ON s.id = a.subject_id
        WHERE a.subject_id = ANY(v_user_registered_subject_ids)
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT 5
    ) a_reg;

    -- 9. Materials (In registered subjects)
    SELECT COALESCE(JSON_AGG(m_reg), '[]'::json) INTO v_materials
    FROM (
        SELECT 
            m.id, m.name, m.details, m.created_at, m.updated_at,
            JSON_BUILD_OBJECT('id', s.id, 'name', s.name, 'code', s.code) AS subject
        FROM materials m
        JOIN subjects s ON s.id = m.subject_id
        WHERE m.subject_id = ANY(v_user_registered_subject_ids)
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 5
    ) m_reg;

    -- 10. Subjects (User's registered subjects)
    SELECT COALESCE(JSON_AGG(s_reg), '[]'::json) INTO v_subjects
    FROM (
        SELECT s.id, s.name, s.code, s.faculty_id, s.department_id, s.year_id
        FROM subjects s
        JOIN user_subject_links usl ON usl.subject_id = s.id
        WHERE usl.user_id = p_user_id
        ORDER BY s.name ASC
        LIMIT 5
    ) s_reg;

    -- 11. Events Published (author_id = p_user_id)
    SELECT COALESCE(JSON_AGG(e_pub), '[]'::json) INTO v_events
    FROM (
        SELECT e.id, e.title, e.start_date, e.end_date, e.price, e.location_type, e.location, e.details, e.created_at, e.updated_at, 
        JSON_BUILD_OBJECT(
            'id', eo.id, 
            'name', eo.name, 
            'details', eo.details, 
            'logo', JSON_BUILD_OBJECT('id', eo_logo.id, 'url', eo_logo.url, 'details', eo_logo.details)
        ) AS event_organizer,
        JSON_BUILD_OBJECT(
            'id', e_logo.id, 
            'url', e_logo.url,
            'details', e_logo.details
        ) AS logo,
        JSON_BUILD_OBJECT(
            'id', ue.id,
            'user', JSON_BUILD_OBJECT('id', u.id, 'name', u.name, 'email', u.email)
        ) AS user_events
        FROM events e
        LEFT JOIN event_organizers eo ON eo.id = e.event_organizer_id
        LEFT JOIN attachments eo_logo ON eo_logo.id = eo.logo_id
        LEFT JOIN attachments e_logo ON e_logo.id = e.logo_id
        LEFT JOIN user_events ue ON ue.event_id = e.id
        LEFT JOIN users u ON u.id = ue.user_id
        WHERE e.author_id = p_user_id
        ORDER BY e.created_at DESC, e.id DESC
        LIMIT 5
    ) e_pub;

    -- 11. User Logs
    SELECT COALESCE(JSON_AGG(l_user), '[]'::json) INTO v_logs
    FROM (
        SELECT l.*
        FROM logs l
        WHERE l.user_id = p_user_id
        ORDER BY l.created_at DESC, l.id DESC
        LIMIT 5
    ) l_user;

    -- 12. Combine user base details with nested relationship top 5s
    v_result := v_user_json::jsonb || JSON_BUILD_OBJECT(
        'tasks_published', v_tasks_published,
        'tasks', v_tasks,
        'exams_published', v_exams_published,
        'exams', v_exams,
        'announcements_published', v_announcements_published,
        'announcements', v_announcements,
        'materials', v_materials,
        'subjects', v_subjects,
        'events', v_events,
        'logs', v_logs
    )::jsonb;

    RETURN v_result::json;
END;
$$ LANGUAGE plpgsql;