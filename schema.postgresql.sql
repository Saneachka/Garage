BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> e9dbd7bd23a1

CREATE TABLE roles (
    id BIGSERIAL NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE TABLE services (
    id BIGSERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    price NUMERIC(12, 2) NOT NULL, 
    duration_minutes SMALLINT NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE user_groups (
    id BIGSERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    PRIMARY KEY (id)
);

CREATE TABLE users (
    id BIGSERIAL NOT NULL, 
    role_id BIGINT NOT NULL, 
    full_name VARCHAR(200) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    phone VARCHAR(30), 
    deleted_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(role_id) REFERENCES roles (id), 
    UNIQUE (email)
);

CREATE TABLE schedule_slots (
    id BIGSERIAL NOT NULL, 
    master_user_id BIGINT NOT NULL, 
    starts_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    is_available BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(master_user_id) REFERENCES users (id)
);

CREATE TABLE sessions (
    id VARCHAR(64) NOT NULL, 
    user_id BIGINT NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE user_group_members (
    user_id BIGINT NOT NULL, 
    group_id BIGINT NOT NULL, 
    PRIMARY KEY (user_id, group_id), 
    FOREIGN KEY(group_id) REFERENCES user_groups (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE vehicles (
    id BIGSERIAL NOT NULL, 
    client_user_id BIGINT NOT NULL, 
    vin CHAR(17), 
    plate_number VARCHAR(20), 
    brand VARCHAR(200) NOT NULL, 
    model VARCHAR(200) NOT NULL, 
    production_year SMALLINT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_user_id) REFERENCES users (id), 
    UNIQUE (vin)
);

CREATE TABLE appointments (
    id BIGSERIAL NOT NULL, 
    client_user_id BIGINT NOT NULL, 
    vehicle_id BIGINT NOT NULL, 
    slot_id BIGINT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    comment TEXT, 
    starts_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_user_id) REFERENCES users (id), 
    FOREIGN KEY(slot_id) REFERENCES schedule_slots (id), 
    FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
);

CREATE INDEX ix_appointments_slot_id ON appointments (slot_id);

CREATE TABLE appointment_services (
    appointment_id BIGINT NOT NULL, 
    service_id BIGINT NOT NULL, 
    quoted_price NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (appointment_id, service_id), 
    FOREIGN KEY(appointment_id) REFERENCES appointments (id), 
    FOREIGN KEY(service_id) REFERENCES services (id)
);

CREATE TABLE appointment_slots (
    slot_id BIGINT NOT NULL, 
    appointment_id BIGINT NOT NULL, 
    PRIMARY KEY (slot_id), 
    FOREIGN KEY(appointment_id) REFERENCES appointments (id), 
    FOREIGN KEY(slot_id) REFERENCES schedule_slots (id)
);

CREATE INDEX ix_appointment_slots_appointment_id ON appointment_slots (appointment_id);

CREATE TABLE diagnostics (
    id BIGSERIAL NOT NULL, 
    appointment_id BIGINT NOT NULL, 
    master_user_id BIGINT NOT NULL, 
    findings TEXT NOT NULL, 
    recommended_work TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(appointment_id) REFERENCES appointments (id), 
    FOREIGN KEY(master_user_id) REFERENCES users (id), 
    UNIQUE (appointment_id)
);

CREATE TABLE work_orders (
    id BIGSERIAL NOT NULL, 
    appointment_id BIGINT NOT NULL, 
    master_user_id BIGINT NOT NULL, 
    created_by BIGINT NOT NULL, 
    work_description TEXT NOT NULL, 
    work_cost NUMERIC(12, 2) DEFAULT '0' NOT NULL, 
    total_cost NUMERIC(12, 2) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    completed_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(appointment_id) REFERENCES appointments (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(master_user_id) REFERENCES users (id), 
    UNIQUE (appointment_id)
);

CREATE TABLE work_order_parts (
    id BIGSERIAL NOT NULL, 
    work_order_id BIGINT NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    quantity NUMERIC(10, 2) NOT NULL, 
    unit_price NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(work_order_id) REFERENCES work_orders (id)
);

CREATE INDEX ix_work_order_parts_work_order_id ON work_order_parts (work_order_id);

INSERT INTO alembic_version (version_num) VALUES ('e9dbd7bd23a1') RETURNING alembic_version.version_num;

-- Running upgrade e9dbd7bd23a1 -> c0c4ce0faf05

ALTER TABLE vehicles ADD COLUMN archived_at TIMESTAMP WITHOUT TIME ZONE;

UPDATE alembic_version SET version_num='c0c4ce0faf05' WHERE alembic_version.version_num = 'e9dbd7bd23a1';

-- Running upgrade c0c4ce0faf05 -> 1bcbbc1fe294

CREATE TABLE attachments (
    id BIGSERIAL NOT NULL, 
    work_order_id BIGINT, 
    diagnostic_id BIGINT, 
    filename VARCHAR(255) NOT NULL, 
    content_type VARCHAR(100) NOT NULL, 
    size INTEGER NOT NULL, 
    data BYTEA NOT NULL, 
    uploaded_by BIGINT NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_attachment_one_parent CHECK ((work_order_id IS NULL) <> (diagnostic_id IS NULL)), 
    FOREIGN KEY(diagnostic_id) REFERENCES diagnostics (id), 
    FOREIGN KEY(uploaded_by) REFERENCES users (id), 
    FOREIGN KEY(work_order_id) REFERENCES work_orders (id)
);

CREATE INDEX ix_attachments_diagnostic_id ON attachments (diagnostic_id);

CREATE INDEX ix_attachments_work_order_id ON attachments (work_order_id);

UPDATE alembic_version SET version_num='1bcbbc1fe294' WHERE alembic_version.version_num = 'c0c4ce0faf05';

COMMIT;

