# kopidarat

NUS IT2002 Project
Developing a Web-database three-tier application to allow users to find people with same interests to go for activities together. The Python Django Framework is used for developing the website in conjuction with PostgreSQL as the Database Management System and CSS as the front-end.

This website contain the following features:

1. Register and Login system for users (both members and administrators)
2. Members can create, join, edit, and delete activities
3. Members can create and delete reviews to activities that they have joined
4. Members can create reports to users that is deemed to have inappropriate behaviour
5. Administrators can create, edit, and delete users from the system
6. Administrators can create, edit, and delete activities in the system
7. Administrators can delete reviews in the system
8. Administrators can delete reports in the system

Database Constraints are checked using SQL Database Integrity checks in the schema (during the creation of the tables) and other additional integrity checks are done using PL/pgSQL SQL Procedural Programming Language, mainly stored procedures, functions, and triggers:

1. Procedure to add the users into the users database and member/administator database
2. Procedure to add the activities into the activity table and the associated inviter to the joins table
3. Function and trigger to check there could not be any user trying to join an activity that has an overlapping times with the user's current list of joined activities
4. Function and trigger to check that the user could not join an activity that is already in full capacity
5. Function and trigger to check that the user could not create a review of an event that has not passed yet or even join in the first place
6. Function and trigger to check that a member cannot be an administrator
7. Function and trigger to check that an administrator cannot be a member
