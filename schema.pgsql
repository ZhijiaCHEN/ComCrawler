DROP TABLE IF EXISTS website CASCADE;
CREATE TABLE website(
    wid INT PRIMARY KEY,
    host VARCHAR,
    allow_comment BOOLEAN DEFAULT FALSE
);

DROP TABLE IF EXISTS webpage CASCADE;
CREATE TABLE webpage(
    pid SERIAL PRIMARY KEY,
    wid INT REFERENCES website(wid),
    url VARCHAR UNIQUE,
    language_region VARCHAR,
    btn_hit BOOLEAN,
    cmt_hit BOOLEAN,
    status INT,
    visit_time TIMESTAMP DEFAULT NOW()
);

CREATE TABLE language_region (
    language_region varchar(40) PRIMARY KEY,
    hl varchar(10) NOT NULL,
    gl varchar(10) NOT NULL NOT NULL,
    ceid varchar(40) NOT NULL
);

DROP TABLE IF EXISTS article CASCADE;
CREATE TABLE article(
    aid SERIAL PRIMARY KEY,
    wid INT REFERENCES website(wid),
    title VARCHAR,
    topic VARCHAR,
    url VARCHAR UNIQUE,
    language VARCHAR,
    region VARCHAR,
    btn_hit BOOLEAN,
    cmt_hit BOOLEAN,
    status INT,
    pub_time TIMESTAMP,
    discovered_time TIMESTAMP DEFAULT NOW(),
    last_visit_time TIMESTAMP
);

DROP TABLE IF EXISTS news_monitor CASCADE;
CREATE TABLE news_monitor(
    url VARCHAR PRIMARY KEY,
    title VARCHAR,
    topic VARCHAR,
    language VARCHAR,
    region VARCHAR,
    pub_time TIMESTAMP,
    discovered_time TIMESTAMP DEFAULT NOW()
);

DROP TABLE IF EXISTS comment_crawler CASCADE;
CREATE TABLE comment_crawler(
    aid INT REFERENCES article(aid),
    num_click INT,
    num_btn_candidate INT,
    num_structure INT,
    num_cmt_candidate INT,
    num_no_struct INT,
    stime TIMESTAMP DEFAULT NOW(),
    etime TIMESTAMP
);

DROP TABLE IF EXISTS naive_comment_crawler CASCADE;
CREATE TABLE naive_comment_crawler(
    aid INT REFERENCES article(aid),
    num_click INT,
    num_btn_candidate INT,
    num_structure INT,
    num_cmt_candidate INT,
    num_no_struct INT,
    stime TIMESTAMP DEFAULT NOW(),
    etime TIMESTAMP
);

DROP TABLE IF EXISTS count_results CASCADE;
CREATE TABLE count_results(
    aid INT REFERENCES article(aid),
    has_btn BOOLEAN,
    hit_btn BOOLEAN,
    has_cmt BOOLEAN,
    hit_cmt BOOLEAN,
    failure_code INT,
    cmt_num INT,
    status INT DEFAULT 0
);
