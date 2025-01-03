CREATE TYPE instruction_type AS ENUM ('check', 'multiple_choice', 'single_choice', 'multiple_select', 'numeric_input');


CREATE TABLE users(
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL UNIQUE, -- 사용자 닉네임 -- 추후에 company_name으로 수정
    wearable_identification VARCHAR(100)[], -- 1:n
    employee_identification_number BIGINT NOT NULL UNIQUE -- 사원번호, 회원가입할 때 직접 입력
);

CREATE TABLE infras(
    infra_id SERIAL PRIMARY KEY,
    infra_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL, -- 작성자의 이름 또는 아이디(아이디를 만드는 것이 좋을것 같음)
    FOREIGN KEY (company_name) REFERENCES users(company_name) ON DELETE CASCADE
    -- infra_location POINT, -- 위 경도 좌표
);

CREATE TABLE report_forms (
    report_form_id SERIAL PRIMARY KEY,
    infra_id INT NOT NULL,
    company_name VARCHAR(255) NOT NULL, -- 작성자의 이름 또는 아이디(아이디를 만드는 것이 좋을것 같음)
    last_modified_time BIGINT, -- 마지막으로 수정된 시간
    FOREIGN KEY (infra_id) REFERENCES infras(infra_id) ON DELETE CASCADE,
    FOREIGN KEY (company_name) REFERENCES users(company_name) ON DELETE CASCADE
);

CREATE TABLE topic_forms (
    topic_form_id SERIAL PRIMARY KEY,
    report_form_id INT NOT NULL,
    topic_form_name VARCHAR(255) NOT NULL,
    -- image_required BOOLEAN NOT NULL,
    -- postgres 배열 타입: 원소가 instruction_form_id - 추가 나중에 쿼리 날려서 instruction 찾을 때 이거 사용,
    -- 위의 거가 과연 필요한가? 어차피 topic을 찾는다 해도 infra_id로 찾기 시작할거라 필요 없을 듯
    FOREIGN KEY (report_form_id) REFERENCES report_forms(report_form_id) ON DELETE CASCADE
);

CREATE TABLE instruction_forms (
    instruction_form_id SERIAL PRIMARY KEY,
    topic_form_id INT NOT NULL,
    instruction TEXT NOT NULL,
    instruction_type instruction_type NOT NULL,
    img_url VARCHAR(2048), 
    options VARCHAR(100)[], -- 문자열로 옵션 저장 ('multiple_choice', 'single_choice', 'multiple_select' 의 경우)
    answer VARCHAR(100)[], -- 응답 정보 저장 - 바차배열쓰기
    FOREIGN KEY (topic_form_id) REFERENCES topic_forms(topic_form_id) ON DELETE CASCADE
);

CREATE TABLE posted_reports(
    posted_report_id SERIAL PRIMARY KEY,
    posted_report_path VARCHAR(255) NOT NULL, -- 안드로이드 client가 반환한 JSON 형식의 보고서 파일 저장 경로 -- 트리거 생성 필요
    report_form_id INT NOT NULL,
    start_time BIGINT, -- 유닉스 타임스탬프로 작성 시작 시간 
    end_time BIGINT, -- 유닉스 타임스탬프로 작성 완료 시간
    company_name VARCHAR(255) NOT NULL, -- 회사 이름
    user_name VARCHAR(255) NOT NULL, -- 안드로이드 기기에서 작성자의 이름 또는 아이디(아이디를 만드는 것이 좋을것 같음)
    memo VARCHAR(1000),
    FOREIGN KEY (report_form_id) REFERENCES report_forms(report_form_id) ON DELETE CASCADE,
    FOREIGN KEY (company_name) REFERENCES users(company_name) ON DELETE CASCADE
);

CREATE TABLE media_files (
    media_id SERIAL PRIMARY KEY,
    infra_id INT NOT NULL,
    infra_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    file_name VARCHAR,
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('audio', 'image', 'pdf', 'video')),
    -- file_path VARCHAR(255) NOT NULL,
    FOREIGN KEY (infra_id) REFERENCES infras(infra_id) ON DELETE CASCADE
);

CREATE TABLE img_files (
    file_id SERIAL PRIMARY KEY, -- Use SERIAL for auto-incrementing IDs
    file_name VARCHAR(255) NULL, -- Allowing for NULL filenames, adjust length to match others
    file_size BIGINT NULL, -- Use BIGINT to match large file sizes
    file_data BYTEA NULL -- Store binary file data (bytea type)
);

CREATE TABLE user_location (
    android_uuid VARCHAR(100) NOT NULL,  
    company_name VARCHAR(255) NOT NULL,           
    latitude DOUBLE PRECISION NOT NULL,  -- 위도
    longitude DOUBLE PRECISION NOT NULL, -- 경도
    PRIMARY KEY (android_uuid)           -- 안드로이드 UUID를 기본 키로 설정
);