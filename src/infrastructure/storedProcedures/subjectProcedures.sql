CREATE OR REPLACE FUNCTION get_user_available_subjects(
    p_user_id INT,
    p_department_id INT,
    p_year_id INT,
    p_query VARCHAR(255) DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_faculty_id INT;
    v_department_id INT;
    v_study_type VARCHAR(255);
    general_department_id INT;
    department_ids INT[];
    year_ids INT[];
    v_user_year INT;
    v_result JSON;
BEGIN
    -- 1. Fetch user's faculty, department, and numerical year value
    SELECT 
        u.faculty_id,
        u.department_id,
        u.study_type,
        y.year
    INTO 
        v_faculty_id,
        v_department_id,
        v_study_type,
        v_user_year
    FROM users u
    JOIN years y ON y.id = u.year_id
    WHERE u.id = p_user_id;

    SELECT id INTO general_department_id FROM departments WHERE name ILIKE '%General%' AND faculty_id = v_faculty_id AND study_type = v_study_type;

    -- If user does not exist or has missing metadata, return empty array
    IF NOT FOUND OR v_user_year IS NULL THEN
        RETURN '[]'::JSON;
    END IF;

    IF general_department_id IS NULL THEN
        department_ids := ARRAY[v_department_id];
    ELSE
        department_ids := ARRAY[v_department_id, general_department_id];
    END IF;

    IF p_department_id NOT IN (SELECT UNNEST(department_ids)) THEN
        RETURN '[]'::JSON;
    END IF;

    SELECT ARRAY_AGG(id) INTO year_ids FROM years WHERE year >= v_user_year AND year <= (v_user_year + 5);

    IF p_year_id NOT IN (SELECT UNNEST(year_ids)) THEN
        RETURN '[]'::JSON;
    END IF;

    -- 2. Retrieve subjects
    SELECT COALESCE(
        JSON_AGG(
            json_build_object(
                'id', sub.id,
                'name', sub.name,
                'code', sub.code,
                'credits', sub.credits,
                'details', sub.details,
                'created_at', sub.created_at,
                'updated_at', sub.updated_at,
                'faculty', json_build_object(
                    'id', f.id,
                    'name', f.name
                ),
                'department', json_build_object(
                    'id', d.id,
                    'name', d.name,
                    'code', d.code
                ),
                'year', json_build_object(
                    'id', y.id,
                    'year', y.year
                )
            )
            ORDER BY y.year ASC, sub.id ASC
        ),
        '[]'::JSON
    )
    INTO v_result
    FROM subjects sub
    JOIN years y ON y.id = sub.year_id
    JOIN faculties f ON f.id = sub.faculty_id
    JOIN departments d ON d.id = sub.department_id
    LEFT JOIN user_subject_links usl ON usl.subject_id = sub.id AND usl.user_id = p_user_id
    WHERE usl.subject_id IS NULL  -- Exclude subjects already registered by the user
      AND sub.faculty_id = v_faculty_id
      AND sub.department_id = p_department_id
      AND sub.year_id = p_year_id
      AND (p_query IS NULL OR (sub.name ILIKE '%' || p_query || '%' OR sub.code ILIKE '%' || p_query || '%'));

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;