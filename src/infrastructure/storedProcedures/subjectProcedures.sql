CREATE OR REPLACE FUNCTION get_user_available_subjects(
    p_user_id INT
)
RETURNS JSON AS $$
DECLARE
    v_faculty_id INT;
    v_department_id INT;
    v_user_year INT;
    v_result JSON;
BEGIN
    -- 1. Fetch user's faculty, department, and numerical year value
    SELECT 
        u.faculty_id,
        u.department_id,
        y.year
    INTO 
        v_faculty_id,
        v_department_id,
        v_user_year
    FROM users u
    JOIN years y ON y.id = u.year_id
    WHERE u.id = p_user_id;

    -- If user does not exist or has missing metadata, return empty array
    IF NOT FOUND OR v_user_year IS NULL THEN
        RETURN '[]'::JSON;
    END IF;

    -- 2. Retrieve subjects in the range [v_user_year, v_user_year + 5]
    SELECT COALESCE(JSON_AGG(sub ORDER BY y.year ASC, sub.id ASC), '[]'::JSON)
    INTO v_result
    FROM subjects sub
    JOIN years y ON y.id = sub.year_id
    WHERE sub.faculty_id = v_faculty_id
      AND sub.department_id = v_department_id
      AND y.year >= v_user_year
      AND y.year <= (v_user_year + 5);

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;