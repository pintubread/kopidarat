CREATE OR REPLACE PROCEDURE add_new_member(full_name VARCHAR,
										   username VARCHAR,
										   email VARCHAR,
										   phone_number VARCHAR,
										   password VARCHAR) AS $$
BEGIN
	INSERT INTO users VALUES (full_name,username,email,phone_number,'member');
	INSERT INTO member VALUES (email);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_participation_func() RETURNS TRIGGER AS $$
DECLARE 
	participant VARCHAR;
	activity_id NUMERIC;
BEGIN
	SELECT j.participant INTO participant
	FROM joins j 
	WHERE j.activity_id = NEW.activity_id 
	AND j.participant = NEW.participant;
	
	SELECT a.activity_id INTO activity_id
	FROM activity a 
	WHERE a.activity_id = NEW.activity_id
	AND a.start_date_time < NOW();
	
	IF participant IS NULL THEN
		RAISE NOTICE 'You did not register for this event, 
		hence you are not eligible to give a review.';
		RETURN NULL;
	ELSIF activity_id IS NULL THEN
		RAISE NOTICE 'Event has not happened, hence you cannot give a review';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_participation
BEFORE INSERT OR UPDATE
ON review
FOR EACH ROW 
EXECUTE FUNCTION check_participation_func();

DROP TRIGGER IF EXISTS check_participation ON review;



SELECT * FROM activity WHERE activity_id=35;

INSERT INTO review VALUES(
35,NOW(),'admin00@kopidarat.herokuapp.com',
'amazing');
	
