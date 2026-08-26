CREATE OR REPLACE FUNCTION get_user_calendar(
    p_user_id INT,
    p_date_from TIMESTAMP WITH TIME ZONE,
    p_date_to TIMESTAMP WITH TIME ZONE
)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
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
        JOIN registered_subjects rs ON rs.subject_id = a.subject_id
        JOIN subjects s ON s.id = a.subject_id
        WHERE a.date IS NOT NULL
          AND a.date >= p_date_from 
          AND a.date <= p_date_to
    )
    -- 5. Construct final JSON object matching CalendarResponseDto structure
    SELECT json_build_object(
        'tasks', COALESCE((SELECT json_agg(ft ORDER BY ft.deadline ASC, ft.id ASC) FROM filtered_tasks ft), '[]'::json),
        'exams', COALESCE((SELECT json_agg(fe ORDER BY fe.deadline ASC, fe.id ASC) FROM filtered_exams fe), '[]'::json),
        'announcements', COALESCE((SELECT json_agg(fa ORDER BY fa.date DESC, fa.id ASC) FROM filtered_announcements fa), '[]'::json)
    ) INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;