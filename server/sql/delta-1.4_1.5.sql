-- SQL delta update from rteval-1.4.sql to rteval-1.5.sql

UPDATE rteval_info SET value = '1.5' WHERE key = 'sql_schema_ver';

-- TABLE: hwlatdetect_summary
-- Tracks hwlatdetect results for a particular hardware
--
   CREATE TABLE hwlatdetect_summary (
       rterid         INTEGER REFERENCES rtevalruns(rterid) NOT NULL,
       duration       INTEGER NOT NULL,
       threshold      INTEGER NOT NULL,
       timewindow     INTEGER NOT NULL,
       width          INTEGER NOT NULL,
       samplecount    INTEGER NOT NULL,
       hwlat_min      REAL NOT NULL,
       hwlat_avg      REAL NOT NULL,
       hwlat_max      REAL NOT NULL
   ) WITHOUT OIDS;
   GRANT SELECT, INSERT ON hwlatdetect_summary TO rtevparser;

-- TABLE: hwlatdetect_samples
-- Contains the hwlatdetect sample records from a particular run
--
   CREATE TABLE hwlatdetect_samples (
       rterid         INTEGER REFERENCES rtevalruns(rterid) NOT NULL,
       timestamp      NUMERIC(20,10) NOT NULL,
       latency        REAL NOT NULL
   ) WITHOUT OIDS;
   GRANT SELECT, INSERT ON hwlatdetect_samples TO rtevparser;

