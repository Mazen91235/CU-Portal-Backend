CREATE OR REPLACE FUNCTION get_user_calendar(
    p_user_id INT,
    p_date_from TIMESTAMP WITH TIME ZONE,
    p_date_to TIMESTAMP WITH TIME ZONE
)
RETURNS JSON AS $$
DECLARE
    v_faculty_id INT;
    v_department_id INT;
    v_year_id INT;
    v_result JSON;
BEGIN
    SELECT 
        u.faculty_id,
        u.department_id,
        u.year_id
    INTO 
        v_faculty_id,
        v_department_id,
        v_year_id
    FROM users u
    WHERE u.id = p_user_id;

    WITH registered_subjects AS (
        -- 1. Fetch all subject IDs registered by the user
        SELECT subject_id 
        FROM user_subject_links 
        WHERE user_id = p_user_id
    ),
    filtered_tasks AS (
        -- 2. Fetch Tasks (task_type = 'task') within range
        SELECT t.*, json_build_object('id', s.id, 'name', s.name) AS subject
        FROM tasks t
        JOIN registered_subjects rs ON rs.subject_id = t.subject_id
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.task_type = 'task'
          AND t.deadline >= p_date_from 
          AND t.deadline <= p_date_to
    ),
    filtered_exams AS (
        -- 3. Fetch Exams (task_type = 'exam') within range
        SELECT t.*, json_build_object('id', s.id, 'name', s.name) AS subject
        FROM tasks t
        JOIN registered_subjects rs ON rs.subject_id = t.subject_id
        JOIN subjects s ON s.id = t.subject_id
        WHERE t.task_type = 'exam'
          AND t.deadline >= p_date_from 
          AND t.deadline <= p_date_to
    ),
    filtered_announcements AS (
        -- 4. Fetch Announcements with non-null date within range
        SELECT a.*, json_build_object('id', s.id, 'name', s.name) AS subject
        FROM announcements a
        LEFT JOIN registered_subjects rs ON rs.subject_id = a.subject_id
        LEFT JOIN subjects s ON s.id = a.subject_id
        WHERE a.date IS NOT NULL
        AND (a.subject_id IS NOT NULL OR (a.faculty_id IS NULL OR a.faculty_id = v_faculty_id) AND (a.department_id IS NULL OR a.department_id = v_department_id) AND (a.year_id IS NULL OR a.year_id = v_year_id))
          AND a.date >= p_date_from 
          AND a.date <= p_date_to
    ),
    filtered_events AS (
    -- 5. Fetch Events with non-null date within range
    SELECT e.*,
           json_build_object('id', f.id, 'name', f.name) AS faculty,
           json_build_object('id', d.id, 'name', d.name, 'code', d.code) AS department,
           json_build_object('id', y.id, 'year', y.year) AS year,
           json_build_object('id', a.id, 'url', a.url, 'details', a.details) AS logo,
           COALESCE(
               json_agg(json_build_object('id', ue.id)) FILTER (WHERE ue.id IS NOT NULL),
               '[]'::json
           ) AS attendees
    FROM events e
    LEFT JOIN faculties f ON f.id = e.faculty_id
    LEFT JOIN departments d ON d.id = e.department_id
    LEFT JOIN years y ON y.id = e.year_id
    LEFT JOIN attachments a ON a.id = e.logo_id
    LEFT JOIN user_events ue ON ue.event_id = e.id
    WHERE (e.faculty_id IS NULL OR e.faculty_id = v_faculty_id)
      AND (e.department_id IS NULL OR e.department_id = v_department_id)
      AND (e.year_id IS NULL OR e.year_id = v_year_id)
      AND e.start_date IS NOT NULL
      AND e.start_date >= p_date_from 
      AND e.start_date <= p_date_to
    GROUP BY e.id, f.id, d.id, y.id, a.id
    ),
    filtered_notes AS (
        -- 6. Fetch Notes with non-null date within range
        SELECT n.*
        FROM notes n
        WHERE n.author_id = p_user_id
          AND n.date IS NOT NULL
          AND n.date >= p_date_from 
          AND n.date <= p_date_to
    )
    -- 7. Construct final JSON object matching CalendarResponseDto structure
    SELECT json_build_object(
        'tasks', COALESCE((SELECT json_agg(ft ORDER BY ft.deadline ASC, ft.id ASC) FROM filtered_tasks ft), '[]'::json),
        'exams', COALESCE((SELECT json_agg(fe ORDER BY fe.deadline ASC, fe.id ASC) FROM filtered_exams fe), '[]'::json),
        'announcements', COALESCE((SELECT json_agg(fa ORDER BY fa.date DESC, fa.id ASC) FROM filtered_announcements fa), '[]'::json),
        'events', COALESCE((SELECT json_agg(fe ORDER BY fe.start_date DESC, fe.id ASC) FROM filtered_events fe), '[]'::json),
        'notes', COALESCE((SELECT json_agg(fn ORDER BY fn.date DESC, fn.id ASC) FROM filtered_notes fn), '[]'::json)
    ) INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;