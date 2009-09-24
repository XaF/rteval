-- Create rteval database users
--
CREATE USER xmlrpc NOSUPERUSER ENCRYPTED PASSWORD 'rtevaldb';

-- Create rteval database
--
CREATE DATABASE rteval ENCODING 'utf-8';

\c rteval

-- TABLE: systems
-- Overview table over all systems which have sent reports
-- The dmidata column will keep the complete DMIdata available
-- for further information about the system.
--
    CREATE TABLE systems (
        syskey        SERIAL NOT NULL,
        sysid         VARCHAR(64) NOT NULL,
        dmidata       xml NOT NULL,
        PRIMARY KEY(syskey)
    ) WITH OIDS;

    GRANT SELECT,INSERT ON systems TO xmlrpc;
    GRANT USAGE ON systems_syskey_seq TO xmlrpc;

-- TABLE: systems_hostname
-- This table is used to track the hostnames and IP addresses
-- a registered system have used over time
--
   CREATE TABLE systems_hostname (
        syskey        INTEGER REFERENCES systems(syskey) NOT NULL,
        hostname      VARCHAR(256) NOT NULL,
        ipaddr        cidr      
    ) WITH OIDS;
    CREATE INDEX systems_hostname_syskey ON systems_hostname(syskey);
    CREATE INDEX systems_hostname_hostname ON systems_hostname(hostname);
    CREATE INDEX systems_hostname_ipaddr ON systems_hostname(ipaddr);

    GRANT SELECT, INSERT ON systems_hostname TO xmlrpc;


-- TABLE: rtevalruns
-- Overview over all rteval runs, when they were run and how long they ran.
--
    CREATE TABLE rtevalruns (
        rterid          SERIAL NOT NULL, -- RTEval Run Id
        syskey          INTEGER REFERENCES systems(syskey) NOT NULL,
        kernel_ver      VARCHAR(32) NOT NULL,
        kernel_rt       BOOLEAN NOT NULL,
        arch            VARCHAR(12) NOT NULL,
        run_start       TIMESTAMP WITH TIME ZONE NOT NULL,
        run_duration    INTEGER NOT NULL,
        load_avg        REAL NOT NULL,
        version         VARCHAR(4), -- Version of rteval
        report_filename TEXT,
        PRIMARY KEY(rterid)
    ) WITH OIDS;

    GRANT SELECT,INSERT ON rtevalruns TO xmlrpc;
    GRANT USAGE ON rtevalruns_rterid_seq TO xmlrpc;

-- TABLE rtevalruns_details
-- More specific information on the rteval run.  The data is stored
-- in XML for flexibility
--
-- Tags being saved here includes: /rteval/clocksource, /rteval/hardware,
-- /rteval/loads and /rteval/cyclictest/command_line
--
    CREATE TABLE rtevalruns_details (
        rterid        INTEGER REFERENCES rtevalruns(rterid) NOT NULL,
        xmldata       xml NOT NULL,
        PRIMARY KEY(rterid)
    );
    GRANT INSERT ON rtevalruns_details TO xmlrpc;

-- TABLE: cyclic_statistics
-- This table keeps statistics overview over a particular rteval run
--
    CREATE TABLE cyclic_statistics (
        rterid        INTEGER REFERENCES rtevalruns(rterid) NOT NULL,
        coreid        INTEGER, -- NULL=system
        priority      INTEGER, -- NULL=system
        num_samples   INTEGER NOT NULL,
        lat_min       REAL NOT NULL,
        lat_max       REAL NOT NULL,
        lat_mean      REAL NOT NULL,
        mode          INTEGER NOT NULL,
        range         REAL NOT NULL,
        median        REAL NOT NULL,
        stddev        REAL NOT NULL,
        cstid         SERIAL NOT NULL, -- unique record ID
        PRIMARY KEY(cstid)
    ) WITH OIDS;
    CREATE INDEX cyclic_statistics_rterid ON cyclic_statistics(rterid);

    GRANT INSERT ON cyclic_statistics TO xmlrpc;
    GRANT USAGE ON cyclic_statistics_cstid_seq TO xmlrpc;

-- TABLE: cyclic_rawdata
-- This table keeps the raw data for each rteval run being reported.
-- Due to that it will be an enormous amount of data, we avoid using
-- OID on this table.
--
    CREATE TABLE cyclic_rawdata (
        rterid        INTEGER REFERENCES rtevalruns(rterid) NOT NULL,
        cpu_num       INTEGER NOT NULL,
        sampleseq     INTEGER NOT NULL,
        latency       REAL NOT NULL
    ) WITHOUT OIDS;
    CREATE INDEX cyclic_rawdata_rterid ON cyclic_rawdata(rterid);

    GRANT INSERT ON cyclic_rawdata TO xmlrpc;

-- TABLE: notes
-- This table is purely to make notes, connected to different 
-- records in the database
--
    CREATE TABLE notes (
        ntid          SERIAL NOT NULL,
        reftbl        CHAR NOT NULL,    -- S=systems, R=rtevalruns
        refid         INTEGER NOT NULL, -- reference id, to the corresponding table
        notes         TEXT NOT NULL,
        createdby     VARCHAR(48),
        created       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(ntid)
    ) WITH OIDS;
    CREATE INDEX notes_refid ON notes(reftbl,refid);

