CREATE TABLE IF NOT EXISTS marketing_plan (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    title                  VARCHAR(200) NOT NULL,
    description            TEXT,
    status                 VARCHAR(20)  NOT NULL DEFAULT '계획',
    segment_name           VARCHAR(100) NOT NULL,
    cluster_goal           VARCHAR(100),
    marketing_id           VARCHAR(50),
    marketing_name         VARCHAR(200),
    goals                  JSON,
    customer_count         INT,
    churn_rate_before      DOUBLE,
    churn_rate_after       DOUBLE,
    expected_churn_before  DOUBLE,
    expected_churn_after   DOUBLE,
    reduced_customers      DOUBLE,
    created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) DEFAULT CHARSET = utf8mb4;