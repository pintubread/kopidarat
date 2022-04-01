DROP TRIGGER IF EXISTS check_capacity ON joins;
DROP FUNCTION check_capacity_func();

CREATE OR REPLACE FUNCTION check_capacity_func() RETURNS TRIGGER AS $$
DECLARE
	curr_participation INTEGER;
	activity_capacity INTEGER;
	slots_left INTEGER;
BEGIN
	SELECT COUNT(*) INTO curr_participation
	FROM joins j
	WHERE j.activity_id = NEW.activity_id;
	
	SELECT capacity INTO activity_capacity
	FROM activity a
	WHERE a.activity_id = NEW.activity_id;

	slots_left = activity_capacity - curr_participation;
	
	IF slots_left<0 THEN
		RAISE EXCEPTION 'Maximum capacity for activity reached.';
		DELETE FROM joins WHERE activity_id=NEW.activity_id AND participant=NEW.participant;
	ELSE
		RETURN NULL;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_capacity
AFTER INSERT OR UPDATE
ON joins
FOR EACH ROW 
EXECUTE FUNCTION check_capacity_func();