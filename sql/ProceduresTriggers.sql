---- Procedures for inserting members and activities
CREATE OR REPLACE PROCEDURE add_new_member(full_name VARCHAR,
										   username VARCHAR,
										   email VARCHAR,
										   phone_number VARCHAR,
										   password VARCHAR) AS $$
BEGIN
	INSERT INTO users VALUES (full_name,username,email,phone_number,password,'member');
	INSERT INTO member VALUES (email);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE create_new_activity(u_email VARCHAR,
											   u_category VARCHAR,
												 u_activity_name VARCHAR,
											   u_start_date_time TIMESTAMP,
												 u_end_date_time TIMESTAMP,
											   u_venue VARCHAR,
											   u_capacity INTEGER) AS $$
DECLARE
	id INTEGER;
BEGIN
	INSERT INTO activity (inviter,category,activity_name,start_date_time,end_date_time,venue,capacity) VALUES (u_email,u_category,u_activity_name,u_start_date_time,u_end_date_time,u_venue,u_capacity)
	RETURNING activity_id INTO id;
	INSERT INTO joins (activity_id,participant) VALUES (id,u_email);
END
$$ LANGUAGE plpgsql;

---- Joins check trigger, checking amount of people participating
---- timing feasibility trigger

CREATE OR REPLACE FUNCTION check_timing_func() RETURNS TRIGGER AS $$
DECLARE
	overlap_cond INTEGER;
	activity_start TIMESTAMP;
	activity_end TIMESTAMP;
	start_time TIMESTAMP;
	end_time TIMESTAMP;
BEGIN
	overlap_cond := 0;

	SELECT a.start_date_time,a.end_date_time INTO activity_start,activity_end
	FROM joins j, activity a
	WHERE j.activity_id = a.activity_id
	AND j.activity_id = NEW.activity_id;

	FOR start_time,end_time IN
		SELECT a.start_date_time AS start_time, a.end_date_time AS end_time
		FROM joins j, activity a
		WHERE j.activity_id = a.activity_id
		AND j.participant = NEW.participant

	LOOP
		IF (start_time,end_time) OVERLAPS (activity_start,activity_end) THEN
			overlap_cond := overlap_cond + 1;
		END IF;
	END LOOP;
	
	IF overlap_cond > 0 THEN
		RAISE EXCEPTION 'The timing of this activity overlaps with one or more activities that you joined.';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_timing_feasibility
BEFORE INSERT OR UPDATE
ON joins
FOR EACH ROW
EXECUTE FUNCTION check_timing_func();

---- capacity check trigger for joins

CREATE OR REPLACE FUNCTION check_capacity_func() RETURNS TRIGGER AS $$
DECLARE
	curr_participation INTEGER;
	activity_capacity INTEGER;
BEGIN
	SELECT COUNT(*) INTO curr_participation
	FROM joins j
	WHERE j.activity_id = NEW.activity_id;
	
	SELECT capacity INTO activity_capacity
	FROM activity a
	WHERE a.activity_id = NEW.activity_id;
	
	IF activity_capacity - curr_participation<1 THEN
		RAISE EXCEPTION 'Maximum capacity for activity reached.';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_capacity
BEFORE INSERT OR UPDATE
ON joins
FOR EACH ROW 
EXECUTE FUNCTION check_capacity_func();

---- trigger to check validity of review

CREATE OR REPLACE FUNCTION check_review_func() RETURNS TRIGGER AS $$
DECLARE 
	participant VARCHAR;
	activity_happened NUMERIC;
BEGIN
	SELECT j.participant INTO participant
	FROM joins j 
	WHERE j.activity_id = NEW.activity_id 
	AND j.participant = NEW.participant;
	
	SELECT a.activity_id INTO activity_happened
	FROM activity a 
	WHERE a.activity_id = NEW.activity_id
	AND a.end_date_time < NOW();
	
	IF participant IS NULL THEN
		RAISE EXCEPTION 'You did not register for this event, 
		hence you are not eligible to give a review.';
		RETURN NULL;
	ELSIF activity_happened IS NULL THEN
		RAISE EXCEPTION 'Event has not happened, hence you cannot give a review';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_review
BEFORE INSERT OR UPDATE
ON review
FOR EACH ROW 
EXECUTE FUNCTION check_review_func();

---- membership check trigger, users cannot be admins and vice versa
---- check member
CREATE OR REPLACE FUNCTION check_member_func() RETURNS TRIGGER AS $$
DECLARE
	user_email VARCHAR;
BEGIN
	SELECT a.email INTO user_email
	FROM administrator a
	WHERE a.email = NEW.email;

	IF user_email IS NOT NULL THEN
		RAISE EXCEPTION 'This user is an administrator and a member
		cannot be an adiministrator at the same time';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_member
BEFORE INSERT OR UPDATE
ON member
FOR EACH ROW
EXECUTE FUNCTION check_member_func();

---- check administrator
CREATE OR REPLACE FUNCTION check_admin_func() RETURNS TRIGGER AS $$
DECLARE 
	user_email VARCHAR;
BEGIN 
	SELECT m.email INTO user_email
	FROM member m
	WHERE m.email = NEW.email;

	IF user_email IS NOT NULL THEN
		RAISE EXCEPTION 'This user is a member and a member
		cannot be an adiministrator at the same time';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_admin
BEFORE INSERT OR UPDATE
ON administrator
FOR EACH ROW
EXECUTE FUNCTION check_admin_func();
