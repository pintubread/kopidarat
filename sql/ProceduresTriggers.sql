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
											   u_venue VARCHAR,
											   u_capacity INTEGER) AS $$
DECLARE
	id INTEGER;
BEGIN
	INSERT INTO activity (inviter,category,activity_name,start_date_time,venue,capacity) VALUES (u_email,u_category,u_activity_name,u_start_date_time,u_venue,u_capacity)
	RETURNING activity_id INTO id;
	INSERT INTO joins (activity_id,participant) VALUES (id,u_email);
END
$$ LANGUAGE plpgsql;

----- capacity trigger for joins

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

INSERT INTO joins VALUES (35,'admin00@kopidarat.herokuapp.com')

CREATE TRIGGER check_capacity
BEFORE INSERT OR UPDATE
ON joins
FOR EACH ROW 
EXECUTE FUNCTION check_capacity_func();

INSERT INTO joins VALUES(35,'admin00@kopidarat.herokuapp.com')

----trigger to check validity of review

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
	AND a.start_date_time < NOW();
	
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
--- trigger to check validity of report

CREATE OR REPLACE FUNCTION check_report_func() RETURNS TRIGGER AS $$
DECLARE
	reported_email VARCHAR;
BEGIN
	reported_email = NEW.report_user;
	
	IF reported_email IS NULL THEN
		RAISE EXCEPTION 'Username does not exist';
		RETURN NULL;
	ELSE
		RETURN NEW;
	END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_report
BEFORE INSERT OR UPDATE
ON report
EXECUTE FUNCTION check_report_func();

---Dropping procedures and triggers
DROP TRIGGER IF EXISTS check_review ON review;
DROP TRIGGER IF EXISTS check_report ON report;
DROP TRIGGER IF EXISTS check_capacity ON joins;


DROP PROCEDURE create_new_activity(u_email VARCHAR,
									u_activity_name VARCHAR,
									u_category VARCHAR,
									u_start_date_time TIMESTAMP,
									u_venue VARCHAR,
									u_capacity INTEGER);
DROP PROCEDURE check_report_func();
DROP PROCEDURE check_review_func();
DROP PROCEDURE check_capacity_func();
DROP PROCEDURE add_new_member(full_name VARCHAR,username VARCHAR,
							  email VARCHAR,phone_number VARCHAR,
							  password VARCHAR);
							  
							  
							  
							  
							  