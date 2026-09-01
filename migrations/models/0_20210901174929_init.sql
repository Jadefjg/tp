-- upgrade --
CREATE TABLE IF NOT EXISTS `schedulerlock` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(5) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(32) NOT NULL UNIQUE,
    `_password` VARCHAR(256) NOT NULL,
    `status` SMALLINT NOT NULL  DEFAULT 1,
    `isAdmin` BOOL NOT NULL  DEFAULT 0,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `project` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(32) NOT NULL UNIQUE,
    `description` VARCHAR(1000) NOT NULL,
    `status` SMALLINT NOT NULL  DEFAULT 1,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `file` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `classify` VARCHAR(4) NOT NULL  COMMENT 'DIR: dir\nFILE: file' DEFAULT 'dir',
    `path` VARCHAR(200),
    `size` INT NOT NULL  DEFAULT 0,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `parent_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_file_project_913082` (`project_id`, `full_name`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `macro` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(32) NOT NULL,
    `comment` LONGTEXT NOT NULL,
    `isCorotine` BOOL NOT NULL  DEFAULT 0,
    `code` LONGTEXT NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'DISABLED: 0\nNORMAL: 1\nDELETED: 2' DEFAULT 0,
    `verifiedAt` DATETIME(6),
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `project_id` INT NOT NULL,
    `verifiedBy_id` INT,
    UNIQUE KEY `uid_macro_project_85096c` (`project_id`, `name`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `testcase` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(32) NOT NULL,
    `priority` SMALLINT NOT NULL  DEFAULT 3,
    `tag` VARCHAR(200),
    `description` VARCHAR(1000) NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'DISABLED: 0\nNORMAL: 1\nDELETED: 2' DEFAULT 1,
    `data` JSON NOT NULL,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_testcase_project_d19633` (`project_id`, `title`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `testcasedetail` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(50) NOT NULL,
    `classify` VARCHAR(5) NOT NULL  COMMENT 'UI: ui\nAPI: api\nRAW: raw\nMACRO: macro' DEFAULT 'ui',
    `comment` VARCHAR(1000),
    `content` LONGTEXT,
    `next_id` INT,
    `testcase_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `testtag` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(30) NOT NULL,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_testtag_project_ea9d4b` (`project_id`, `title`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `element` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(30) NOT NULL,
    `classify` VARCHAR(10) NOT NULL  COMMENT 'PAGE_GROUP: page group\nPAGE: page\nELEMENT: element\nWIDGET: widget',
    `widget_name` VARCHAR(30),
    `selector` VARCHAR(17)   COMMENT 'ID: id\nXPATH: xpath\nLINK_TEXT: link text\nPARTIAL_LINK_TEXT: partial link text\nNAME: name\nTAG_NAME: tag name\nCLASS_NAME: class name\nCSS_SELECTOR: css selector\nUSER_DEFINED: user defined',
    `selector_value` VARCHAR(100),
    `selector_is_relative` BOOL NOT NULL  DEFAULT 0,
    `status` SMALLINT NOT NULL  COMMENT '\n    0: 禁用; 1: 正常; 2: 已删除\n    ' DEFAULT 1,
    `parent_id` INT,
    `project_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `environment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(32) NOT NULL,
    `description` VARCHAR(1000) NOT NULL,
    `status` SMALLINT NOT NULL  DEFAULT 1,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_environment_name_0fa3be` (`name`, `project_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `taskname` VARCHAR(30) NOT NULL,
    `comment` VARCHAR(1000) NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'DISABLED: 0\nNORMAL: 1\nDELETED: 2' DEFAULT 1,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_task_project_5fc763` (`project_id`, `taskname`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskcase` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `casecontent` JSON NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'OLD: 0\nNORMAL: 1' DEFAULT 1,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `task_id` INT NOT NULL,
    `testcase_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskrunlock` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `env_id` INT NOT NULL,
    `task_id` INT NOT NULL,
    UNIQUE KEY `uid_taskrunlock_task_id_12d6fa` (`task_id`, `env_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskscheduler` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `extra_params` JSON NOT NULL,
    `trigger` VARCHAR(8) NOT NULL  COMMENT 'INTERVAL: interval\nCROM: cron\nDATE: date',
    `trigger_params` JSON NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'PAUSED: 0\nNORMAL: 1' DEFAULT 1,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT NOT NULL,
    `env_id` INT NOT NULL,
    `task_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskrun` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `env_content` JSON NOT NULL,
    `extra_params` JSON NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'CREATED: 0\nINITED: 1\nRUNNING: 2\nPAUSED: 3\nERROR: 4\nCOMPLETED: 5\nSTOPPED: 6' DEFAULT 0,
    `total_num` INT NOT NULL  DEFAULT 0,
    `pass_num` INT NOT NULL  DEFAULT 0,
    `failed_num` INT NOT NULL  DEFAULT 0,
    `error_num` INT NOT NULL  DEFAULT 0,
    `skip_num` INT NOT NULL  DEFAULT 0,
    `startAt` DATETIME(6),
    `endAt` DATETIME(6),
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `createBy_id` INT,
    `env_id` INT NOT NULL,
    `scheduler_id` INT,
    `task_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskruncase` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `data` JSON NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'CREATED: 0\nRUNNING: 1\nCOMPLETED: 2\nERROR: 3\nSTOPPED: 4' DEFAULT 0,
    `result` SMALLINT NOT NULL  COMMENT 'NOT_RUN: 0\nPASS: 1\nFAILED: 2\nERROR: 3\nSKIPPED: 4\nSTOPPED: 5' DEFAULT 0,
    `message` LONGTEXT,
    `startAt` DATETIME(6),
    `endAt` DATETIME(6),
    `task_case_id` INT NOT NULL,
    `task_run_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskruncasedetail` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_detail_content` JSON NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'CREATED: 0\nRUNNING: 1\nCOMPLETED: 2\nERROR: 3\nSTOPPED: 4' DEFAULT 0,
    `result` SMALLINT NOT NULL  COMMENT 'NOT_RUN: 0\nPASS: 1\nFAILED: 2\nERROR: 3\nSKIPPED: 4\nSTOPPED: 5' DEFAULT 0,
    `result_detail` JSON NOT NULL,
    `startAt` DATETIME(6),
    `endAt` DATETIME(6),
    `task_run_case_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskrunlog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `levelname` VARCHAR(10) NOT NULL,
    `pathname` VARCHAR(1024) NOT NULL,
    `filename` VARCHAR(64) NOT NULL,
    `lineno` INT NOT NULL,
    `module` VARCHAR(32) NOT NULL,
    `exc_text` LONGTEXT,
    `created` DOUBLE NOT NULL,
    `createAt` DATETIME(6) NOT NULL,
    `message` LONGTEXT NOT NULL,
    `taskrun_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `taskschedulerlog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `message` VARCHAR(1000) NOT NULL,
    `createAt` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `task_scheduler_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `environmentdetail` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `key` VARCHAR(32) NOT NULL,
    `value` VARCHAR(1024) NOT NULL,
    `comment` VARCHAR(300),
    `environment_id` INT NOT NULL,
    UNIQUE KEY `uid_environment_environ_d06cf6` (`environment_id`, `key`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `projectnotify` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `classify` VARCHAR(8) NOT NULL  COMMENT 'DINGDING: dingding' DEFAULT 'dingding',
    `access_token` VARCHAR(128),
    `secret` VARCHAR(128),
    `at_all` BOOL NOT NULL  DEFAULT 0,
    `at_mobile` JSON NOT NULL,
    `report_template` LONGTEXT NOT NULL,
    `project_id` INT NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `remoteproject` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `url` VARCHAR(512) NOT NULL,
    `remote_project_id` INT,
    `remote_project_name` VARCHAR(100),
    `source` VARCHAR(6) NOT NULL  COMMENT 'INLINE: inline\nYAPI: yapi' DEFAULT 'yapi',
    `token` VARCHAR(128) NOT NULL,
    `status` SMALLINT NOT NULL  COMMENT 'DISABLED: 0\nNORMAL: 1\nDELETED: 2' DEFAULT 1,
    `create_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_remoteproje_project_136d86` (`project_id`, `remote_project_id`, `url`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `apicat` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `remote_cat_id` INT,
    `name` VARCHAR(1000) NOT NULL,
    `source` VARCHAR(6)   COMMENT 'INLINE: inline\nYAPI: yapi' DEFAULT 'inline',
    `update_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `create_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    `remote_project_id` INT
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `remote_api_id` INT,
    `title` VARCHAR(100) NOT NULL,
    `method` VARCHAR(8) NOT NULL  COMMENT 'GET: GET\nPOST: POST\nPUT: PUT\nPATCH: PATCH\nDELETE: DELETE\nCOPY: COPY\nHEAD: HEAD\nOPTIONS: OPTIONS\nLINK: LINK\nUNLINK: UNLINK\nPURGE: PURGE\nLOCK: LOCK\nUNLOCK: UNLOCK\nPROPFIND: PROPFIND\nVIEW: VIEW',
    `path` VARCHAR(300) NOT NULL,
    `tag` JSON NOT NULL,
    `req_params` JSON NOT NULL,
    `req_form` JSON NOT NULL,
    `req_body_json_schema` BOOL NOT NULL  DEFAULT 0,
    `req_body_raw` LONGTEXT,
    `req_body_type` VARCHAR(20) NOT NULL,
    `req_headers` JSON NOT NULL,
    `res_body` LONGTEXT NOT NULL,
    `res_body_json_schema` BOOL NOT NULL  DEFAULT 0,
    `res_body_type` VARCHAR(20) NOT NULL,
    `desc` LONGTEXT NOT NULL,
    `markdown` LONGTEXT NOT NULL,
    `source` VARCHAR(6)   COMMENT 'INLINE: inline\nYAPI: yapi' DEFAULT 'inline',
    `status` SMALLINT NOT NULL  COMMENT 'DISABLED: 0\nNORMAL: 1\nDELETED: 2' DEFAULT 1,
    `update_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `create_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `api_cat_id` INT NOT NULL,
    `project_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `loginrecord` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `token` VARCHAR(256) NOT NULL,
    `expire` DOUBLE NOT NULL,
    `status` SMALLINT NOT NULL,
    `user_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `userinfo` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(32),
    `avatar` VARCHAR(128) NOT NULL  DEFAULT 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
    `user_id` INT NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(20) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `project_user` (
    `project_id` INT NOT NULL,
    `user_id` INT NOT NULL
) CHARACTER SET utf8mb4;
