DROP DATABASE IF EXISTS school_substitution;
CREATE DATABASE school_substitution;
USE school_substitution;

SET FOREIGN_KEY_CHECKS = 0;

-- Master Faculty Registry
CREATE TABLE faculty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    wing ENUM('Senior', 'Middle', 'Primary') NOT NULL,
    total_absences INT DEFAULT 0,
    total_substitutions INT DEFAULT 0,
    INDEX idx_wing (wing)
) ENGINE=InnoDB;

-- Daily Attendance Status Layer
CREATE TABLE daily_attendance (
    faculty_id INT PRIMARY KEY,
    status ENUM('Present', 'Absent') DEFAULT 'Present',
    CONSTRAINT fk_attendance_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5-Day / 7-Period Timetable Matrix (Stores Subject Strings or NULL if free)
CREATE TABLE timetable (
    faculty_id INT PRIMARY KEY,
    monday_p1 VARCHAR(50) DEFAULT NULL, monday_p2 VARCHAR(50) DEFAULT NULL, monday_p3 VARCHAR(50) DEFAULT NULL, monday_p4 VARCHAR(50) DEFAULT NULL, monday_p5 VARCHAR(50) DEFAULT NULL, monday_p6 VARCHAR(50) DEFAULT NULL, monday_p7 VARCHAR(50) DEFAULT NULL,
    tuesday_p1 VARCHAR(50) DEFAULT NULL, tuesday_p2 VARCHAR(50) DEFAULT NULL, tuesday_p3 VARCHAR(50) DEFAULT NULL, tuesday_p4 VARCHAR(50) DEFAULT NULL, tuesday_p5 VARCHAR(50) DEFAULT NULL, tuesday_p6 VARCHAR(50) DEFAULT NULL, tuesday_p7 VARCHAR(50) DEFAULT NULL,
    wednesday_p1 VARCHAR(50) DEFAULT NULL, wednesday_p2 VARCHAR(50) DEFAULT NULL, wednesday_p3 VARCHAR(50) DEFAULT NULL, wednesday_p4 VARCHAR(50) DEFAULT NULL, wednesday_p5 VARCHAR(50) DEFAULT NULL, wednesday_p6 VARCHAR(50) DEFAULT NULL, wednesday_p7 VARCHAR(50) DEFAULT NULL,
    thursday_p1 VARCHAR(50) DEFAULT NULL, thursday_p2 VARCHAR(50) DEFAULT NULL, thursday_p3 VARCHAR(50) DEFAULT NULL, thursday_p4 VARCHAR(50) DEFAULT NULL, thursday_p5 VARCHAR(50) DEFAULT NULL, thursday_p6 VARCHAR(50) DEFAULT NULL, thursday_p7 VARCHAR(50) DEFAULT NULL,
    friday_p1 VARCHAR(50) DEFAULT NULL, friday_p2 VARCHAR(50) DEFAULT NULL, friday_p3 VARCHAR(50) DEFAULT NULL, friday_p4 VARCHAR(50) DEFAULT NULL, friday_p5 VARCHAR(50) DEFAULT NULL, friday_p6 VARCHAR(50) DEFAULT NULL, friday_p7 VARCHAR(50) DEFAULT NULL,
    CONSTRAINT fk_timetable_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Active Daily Substitutions Layer
CREATE TABLE live_substitutions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    absent_faculty_id INT NOT NULL,
    period INT NOT NULL,
    substitute_faculty_id INT DEFAULT NULL,
    CONSTRAINT fk_subs_absent FOREIGN KEY (absent_faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    CONSTRAINT fk_subs_substitute FOREIGN KEY (substitute_faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    CONSTRAINT chk_period CHECK (period BETWEEN 1 AND 7),
    UNIQUE KEY uq_absent_period (absent_faculty_id, period)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;