CREATE TABLE country_visa (
    country_id INTEGER,
    name VARCHAR(255),
    visa_type SMALLINT,
    days_without_visa INTEGER,
    comments TEXT,
    date_from DATE,
    date_to DATE
);

CREATE TABLE Country ("id" integer NOT NULL PRIMARY KEY, "name" varchar(100) NOT NULL UNIQUE)
CREATE TABLE Groups ("code" integer NOT NULL PRIMARY KEY, "eu_name" varchar(50) NOT NULL UNIQUE, "name" varchar(100) NOT NULL)
CREATE TABLE country_groups (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    country_id INTEGER NOT NULL
        REFERENCES country(id),
    groups_id INTEGER NOT NULL
        REFERENCES groups(code)
);

CREATE TABLE visa_type (
    id SMALLINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE country_iso (
    name VARCHAR(100),
    alpha_2 CHAR(2),
    alpha_3 CHAR(3),
    country_code INT,
    iso_3166_2 VARCHAR(20),
    region VARCHAR(50),
    sub_region VARCHAR(50),
    intermediate_region VARCHAR(50) NULL,
    region_code INT,
    sub_region_code INT,
    intermediate_region_code INT NULL
);

