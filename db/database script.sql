CREATE USER jacob WITH PASSWORD '1passwdwdwxwz';


CREATE DATABASE vr_project
    WITH OWNER = jacob
    ENCODING = 'UTF8';


 GRANT ALL PRIVILEGES ON DATABASE vr_project TO jacob;