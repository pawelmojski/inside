--
-- PostgreSQL database dump
--

\restrict HoqwKJgL4mfQaj3cGwvvfdzaYWsSR8amVrkO6UN8piF8gSh8ZJGfpJcHejETLCG

-- Dumped from database version 17.8 (Debian 17.8-0+deb13u1)
-- Dumped by pg_dump version 17.8 (Debian 17.8-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_grants; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.access_grants (
    id integer NOT NULL,
    user_id integer NOT NULL,
    server_id integer NOT NULL,
    protocol character varying(10) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    is_active boolean,
    granted_by character varying(255),
    reason text,
    created_at timestamp without time zone
);


ALTER TABLE public.access_grants OWNER TO jumphost_user;

--
-- Name: access_grants_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.access_grants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.access_grants_id_seq OWNER TO jumphost_user;

--
-- Name: access_grants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.access_grants_id_seq OWNED BY public.access_grants.id;


--
-- Name: access_policies; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.access_policies (
    id integer NOT NULL,
    user_id integer,
    source_ip_id integer,
    scope_type character varying(20) NOT NULL,
    target_group_id integer,
    target_server_id integer,
    protocol character varying(10),
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone,
    is_active boolean,
    granted_by character varying(255),
    reason text,
    created_at timestamp without time zone,
    user_group_id integer,
    port_forwarding_allowed boolean DEFAULT false NOT NULL,
    use_schedules boolean DEFAULT false NOT NULL,
    created_by_user_id integer,
    inactivity_timeout_minutes integer DEFAULT 60,
    mfa_required boolean DEFAULT false NOT NULL,
    CONSTRAINT check_protocol_valid CHECK (((protocol IS NULL) OR ((protocol)::text = ANY ((ARRAY['ssh'::character varying, 'rdp'::character varying])::text[])))),
    CONSTRAINT check_scope_targets CHECK (((((scope_type)::text = 'group'::text) AND (target_group_id IS NOT NULL) AND (target_server_id IS NULL)) OR (((scope_type)::text = ANY ((ARRAY['server'::character varying, 'service'::character varying])::text[])) AND (target_server_id IS NOT NULL) AND (target_group_id IS NULL)))),
    CONSTRAINT check_scope_type_valid CHECK (((scope_type)::text = ANY ((ARRAY['group'::character varying, 'server'::character varying, 'service'::character varying])::text[])))
);


ALTER TABLE public.access_policies OWNER TO jumphost_user;

--
-- Name: COLUMN access_policies.inactivity_timeout_minutes; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.access_policies.inactivity_timeout_minutes IS 'Inactivity timeout in minutes. NULL or 0 = disabled. Session disconnects after this period of no data transmission.';


--
-- Name: access_policies_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.access_policies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.access_policies_id_seq OWNER TO jumphost_user;

--
-- Name: access_policies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.access_policies_id_seq OWNED BY public.access_policies.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO jumphost_user;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id integer,
    action character varying(100) NOT NULL,
    resource_type character varying(50),
    resource_id integer,
    source_ip character varying(45),
    success boolean NOT NULL,
    details text,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO jumphost_user;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO jumphost_user;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: gates; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.gates (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    hostname character varying(255) NOT NULL,
    api_token character varying(255) NOT NULL,
    location character varying(255),
    description text,
    status character varying(20) NOT NULL,
    last_heartbeat timestamp without time zone,
    version character varying(50),
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ip_pool_start character varying(45) DEFAULT '10.0.160.129'::character varying,
    ip_pool_end character varying(45) DEFAULT '10.0.160.254'::character varying,
    ip_pool_network character varying(45) DEFAULT '10.0.160.128/25'::character varying,
    in_maintenance boolean DEFAULT false,
    maintenance_scheduled_at timestamp without time zone,
    maintenance_reason text,
    maintenance_grace_minutes integer DEFAULT 15,
    msg_welcome_banner text,
    msg_no_backend text,
    msg_no_person text,
    msg_no_grant text,
    msg_maintenance text,
    msg_time_window text,
    mfa_enabled boolean DEFAULT false NOT NULL,
    auto_grant_enabled boolean DEFAULT true,
    auto_grant_duration_days integer DEFAULT 7,
    auto_grant_inactivity_timeout_minutes integer DEFAULT 60,
    auto_grant_port_forwarding boolean DEFAULT true
);


ALTER TABLE public.gates OWNER TO jumphost_user;

--
-- Name: COLUMN gates.mfa_enabled; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.mfa_enabled IS 'If true, gate uses MFA for unknown IPs with fingerprint-based sessions';


--
-- Name: COLUMN gates.auto_grant_enabled; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.auto_grant_enabled IS 'Enable auto-grant creation for this gate. TRUE=enabled, FALSE=disabled. Default: TRUE.';


--
-- Name: COLUMN gates.auto_grant_duration_days; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.auto_grant_duration_days IS 'Auto-grant duration in days. Default: 7 days. Min: 1, Max: 365.';


--
-- Name: COLUMN gates.auto_grant_inactivity_timeout_minutes; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.auto_grant_inactivity_timeout_minutes IS 'Session inactivity timeout in minutes. Default: 60. 0 or NULL = disabled.';


--
-- Name: COLUMN gates.auto_grant_port_forwarding; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.auto_grant_port_forwarding IS 'Allow port forwarding in auto-grants. TRUE=allowed, FALSE=denied. Default: TRUE.';


--
-- Name: gates_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.gates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gates_id_seq OWNER TO jumphost_user;

--
-- Name: gates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.gates_id_seq OWNED BY public.gates.id;


--
-- Name: ip_allocations; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.ip_allocations (
    id integer NOT NULL,
    allocated_ip character varying(45) NOT NULL,
    server_id integer NOT NULL,
    user_id integer,
    source_ip character varying(45),
    allocated_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone,
    is_active boolean,
    session_id character varying(255),
    gate_id integer
);


ALTER TABLE public.ip_allocations OWNER TO jumphost_user;

--
-- Name: ip_allocations_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.ip_allocations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ip_allocations_id_seq OWNER TO jumphost_user;

--
-- Name: ip_allocations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.ip_allocations_id_seq OWNED BY public.ip_allocations.id;


--
-- Name: maintenance_access; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.maintenance_access (
    id integer NOT NULL,
    entity_type character varying(10) NOT NULL,
    entity_id integer NOT NULL,
    person_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT maintenance_access_entity_type_check CHECK (((entity_type)::text = ANY ((ARRAY['gate'::character varying, 'server'::character varying])::text[])))
);


ALTER TABLE public.maintenance_access OWNER TO jumphost_user;

--
-- Name: maintenance_access_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.maintenance_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.maintenance_access_id_seq OWNER TO jumphost_user;

--
-- Name: maintenance_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.maintenance_access_id_seq OWNED BY public.maintenance_access.id;


--
-- Name: mfa_challenges; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.mfa_challenges (
    id integer NOT NULL,
    token character varying(64) NOT NULL,
    gate_id integer NOT NULL,
    user_id integer,
    grant_id integer,
    ssh_username character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    verified boolean DEFAULT false NOT NULL,
    verified_at timestamp without time zone,
    saml_email character varying(255),
    destination_ip character varying(45),
    source_ip character varying(45)
);


ALTER TABLE public.mfa_challenges OWNER TO jumphost_user;

--
-- Name: mfa_challenges_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.mfa_challenges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mfa_challenges_id_seq OWNER TO jumphost_user;

--
-- Name: mfa_challenges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.mfa_challenges_id_seq OWNED BY public.mfa_challenges.id;


--
-- Name: mp4_conversion_queue; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.mp4_conversion_queue (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    status character varying(20) NOT NULL,
    progress integer,
    total integer,
    eta_seconds integer,
    priority integer,
    mp4_path text,
    error_msg text,
    created_at timestamp without time zone,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    CONSTRAINT check_conversion_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'converting'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.mp4_conversion_queue OWNER TO jumphost_user;

--
-- Name: mp4_conversion_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.mp4_conversion_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mp4_conversion_queue_id_seq OWNER TO jumphost_user;

--
-- Name: mp4_conversion_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.mp4_conversion_queue_id_seq OWNED BY public.mp4_conversion_queue.id;


--
-- Name: permission_levels; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.permission_levels AS
 SELECT 0 AS level,
    'Super Admin'::text AS name,
    'Full system access'::text AS description
UNION ALL
 SELECT 100 AS level,
    'Admin'::text AS name,
    'Manage users, policies, gates, servers'::text AS description
UNION ALL
 SELECT 500 AS level,
    'Operator'::text AS name,
    'View-only access, manage active sessions'::text AS description
UNION ALL
 SELECT 1000 AS level,
    'User'::text AS name,
    'No GUI access (SSH/RDP only)'::text AS description;


ALTER VIEW public.permission_levels OWNER TO postgres;

--
-- Name: VIEW permission_levels; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.permission_levels IS 'Reference view for permission level constants';


--
-- Name: policy_audit_log; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.policy_audit_log (
    id integer NOT NULL,
    policy_id integer NOT NULL,
    changed_by_user_id integer,
    change_type character varying(50) NOT NULL,
    field_name character varying(100),
    old_value text,
    new_value text,
    full_old_state jsonb,
    full_new_state jsonb,
    changed_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.policy_audit_log OWNER TO jumphost_user;

--
-- Name: policy_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.policy_audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.policy_audit_log_id_seq OWNER TO jumphost_user;

--
-- Name: policy_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.policy_audit_log_id_seq OWNED BY public.policy_audit_log.id;


--
-- Name: policy_schedules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.policy_schedules (
    id integer NOT NULL,
    policy_id integer NOT NULL,
    name character varying(100),
    weekdays integer[],
    time_start time without time zone,
    time_end time without time zone,
    months integer[],
    days_of_month integer[],
    timezone character varying(50) DEFAULT 'Europe/Warsaw'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.policy_schedules OWNER TO postgres;

--
-- Name: policy_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.policy_schedules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.policy_schedules_id_seq OWNER TO postgres;

--
-- Name: policy_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.policy_schedules_id_seq OWNED BY public.policy_schedules.id;


--
-- Name: policy_ssh_logins; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.policy_ssh_logins (
    id integer NOT NULL,
    policy_id integer NOT NULL,
    allowed_login character varying(255) NOT NULL,
    CONSTRAINT check_ssh_login_policy_id CHECK ((policy_id IS NOT NULL))
);


ALTER TABLE public.policy_ssh_logins OWNER TO jumphost_user;

--
-- Name: policy_ssh_logins_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.policy_ssh_logins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.policy_ssh_logins_id_seq OWNER TO jumphost_user;

--
-- Name: policy_ssh_logins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.policy_ssh_logins_id_seq OWNED BY public.policy_ssh_logins.id;


--
-- Name: server_group_members; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.server_group_members (
    id integer NOT NULL,
    server_id integer NOT NULL,
    group_id integer NOT NULL,
    added_at timestamp without time zone,
    CONSTRAINT check_group_member_ids CHECK (((server_id IS NOT NULL) AND (group_id IS NOT NULL)))
);


ALTER TABLE public.server_group_members OWNER TO jumphost_user;

--
-- Name: server_group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.server_group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.server_group_members_id_seq OWNER TO jumphost_user;

--
-- Name: server_group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.server_group_members_id_seq OWNED BY public.server_group_members.id;


--
-- Name: server_groups; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.server_groups (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    parent_group_id integer,
    CONSTRAINT server_groups_no_self_reference CHECK ((id <> parent_group_id))
);


ALTER TABLE public.server_groups OWNER TO jumphost_user;

--
-- Name: server_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.server_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.server_groups_id_seq OWNER TO jumphost_user;

--
-- Name: server_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.server_groups_id_seq OWNED BY public.server_groups.id;


--
-- Name: servers; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.servers (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    ip_address character varying(45) NOT NULL,
    description text,
    os_type character varying(50),
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    ssh_port integer,
    rdp_port integer,
    in_maintenance boolean DEFAULT false,
    maintenance_scheduled_at timestamp without time zone,
    maintenance_reason text,
    maintenance_grace_minutes integer DEFAULT 15
);


ALTER TABLE public.servers OWNER TO jumphost_user;

--
-- Name: servers_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.servers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.servers_id_seq OWNER TO jumphost_user;

--
-- Name: servers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.servers_id_seq OWNED BY public.servers.id;


--
-- Name: session_recordings; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.session_recordings (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    user_id integer NOT NULL,
    server_id integer NOT NULL,
    protocol character varying(10) NOT NULL,
    source_ip character varying(45) NOT NULL,
    allocated_ip character varying(45) NOT NULL,
    recording_path text NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone,
    duration_seconds integer,
    file_size_bytes integer,
    gate_id integer
);


ALTER TABLE public.session_recordings OWNER TO jumphost_user;

--
-- Name: session_recordings_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.session_recordings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.session_recordings_id_seq OWNER TO jumphost_user;

--
-- Name: session_recordings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.session_recordings_id_seq OWNED BY public.session_recordings.id;


--
-- Name: session_transfers; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.session_transfers (
    id integer NOT NULL,
    session_id integer NOT NULL,
    transfer_type character varying(30) NOT NULL,
    file_path text,
    file_size bigint,
    local_addr character varying(45),
    local_port integer,
    remote_addr character varying(255),
    remote_port integer,
    bytes_sent bigint,
    bytes_received bigint,
    started_at timestamp without time zone,
    ended_at timestamp without time zone,
    CONSTRAINT check_transfer_type_valid CHECK (((transfer_type)::text = ANY ((ARRAY['scp_upload'::character varying, 'scp_download'::character varying, 'sftp_upload'::character varying, 'sftp_download'::character varying, 'port_forward_local'::character varying, 'port_forward_remote'::character varying, 'socks_connection'::character varying, 'sftp_session'::character varying])::text[])))
);


ALTER TABLE public.session_transfers OWNER TO jumphost_user;

--
-- Name: session_transfers_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.session_transfers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.session_transfers_id_seq OWNER TO jumphost_user;

--
-- Name: session_transfers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.session_transfers_id_seq OWNED BY public.session_transfers.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.sessions (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    user_id integer,
    server_id integer,
    protocol character varying(10) NOT NULL,
    source_ip character varying(45) NOT NULL,
    proxy_ip character varying(45),
    backend_ip character varying(45) NOT NULL,
    backend_port integer NOT NULL,
    ssh_username character varying(255),
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone,
    duration_seconds integer,
    recording_path character varying(512),
    recording_size bigint,
    is_active boolean,
    termination_reason character varying(255),
    policy_id integer,
    created_at timestamp without time zone,
    subsystem_name character varying(50),
    ssh_agent_used boolean DEFAULT false,
    connection_status character varying(30) DEFAULT 'active'::character varying,
    denial_reason character varying(100),
    denial_details text,
    protocol_version character varying(50),
    stay_id integer,
    gate_id integer,
    CONSTRAINT check_session_protocol_valid CHECK (((protocol)::text = ANY ((ARRAY['ssh'::character varying, 'rdp'::character varying])::text[])))
);


ALTER TABLE public.sessions OWNER TO jumphost_user;

--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sessions_id_seq OWNER TO jumphost_user;

--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.sessions_id_seq OWNED BY public.sessions.id;


--
-- Name: stays; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.stays (
    id integer NOT NULL,
    user_id integer NOT NULL,
    policy_id integer NOT NULL,
    gate_id integer,
    server_id integer NOT NULL,
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone,
    duration_seconds integer,
    is_active boolean NOT NULL,
    termination_reason character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ssh_key_fingerprint character varying(255)
);


ALTER TABLE public.stays OWNER TO jumphost_user;

--
-- Name: COLUMN stays.ssh_key_fingerprint; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.stays.ssh_key_fingerprint IS 'SSH public key fingerprint (SHA256) used for session identification across IPs';


--
-- Name: stays_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.stays_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stays_id_seq OWNER TO jumphost_user;

--
-- Name: stays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.stays_id_seq OWNED BY public.stays.id;


--
-- Name: user_group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_group_members (
    id integer NOT NULL,
    user_group_id integer NOT NULL,
    user_id integer NOT NULL,
    added_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_group_members OWNER TO postgres;

--
-- Name: user_group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_group_members_id_seq OWNER TO postgres;

--
-- Name: user_group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_group_members_id_seq OWNED BY public.user_group_members.id;


--
-- Name: user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_groups (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    parent_group_id integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT user_groups_no_self_reference CHECK ((id <> parent_group_id))
);


ALTER TABLE public.user_groups OWNER TO postgres;

--
-- Name: user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_groups_id_seq OWNER TO postgres;

--
-- Name: user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_groups_id_seq OWNED BY public.user_groups.id;


--
-- Name: user_source_ips; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.user_source_ips (
    id integer NOT NULL,
    user_id integer NOT NULL,
    source_ip character varying(45) NOT NULL,
    label character varying(255),
    is_active boolean,
    created_at timestamp without time zone,
    CONSTRAINT check_user_source_ip_user_id CHECK ((user_id IS NOT NULL))
);


ALTER TABLE public.user_source_ips OWNER TO jumphost_user;

--
-- Name: user_source_ips_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.user_source_ips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_source_ips_id_seq OWNER TO jumphost_user;

--
-- Name: user_source_ips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.user_source_ips_id_seq OWNED BY public.user_source_ips.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: jumphost_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(255) NOT NULL,
    email character varying(255),
    full_name character varying(255),
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    source_ip character varying(45),
    port_forwarding_allowed boolean DEFAULT false NOT NULL,
    permission_level integer DEFAULT 1000 NOT NULL
);


ALTER TABLE public.users OWNER TO jumphost_user;

--
-- Name: COLUMN users.permission_level; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.users.permission_level IS 'Permission level: 0=SuperAdmin, 100=Admin, 500=Operator, 1000=User (no GUI). Lower = more privileges.';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: jumphost_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO jumphost_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jumphost_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: access_grants id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_grants ALTER COLUMN id SET DEFAULT nextval('public.access_grants_id_seq'::regclass);


--
-- Name: access_policies id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies ALTER COLUMN id SET DEFAULT nextval('public.access_policies_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: gates id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.gates ALTER COLUMN id SET DEFAULT nextval('public.gates_id_seq'::regclass);


--
-- Name: ip_allocations id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations ALTER COLUMN id SET DEFAULT nextval('public.ip_allocations_id_seq'::regclass);


--
-- Name: maintenance_access id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.maintenance_access ALTER COLUMN id SET DEFAULT nextval('public.maintenance_access_id_seq'::regclass);


--
-- Name: mfa_challenges id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges ALTER COLUMN id SET DEFAULT nextval('public.mfa_challenges_id_seq'::regclass);


--
-- Name: mp4_conversion_queue id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mp4_conversion_queue ALTER COLUMN id SET DEFAULT nextval('public.mp4_conversion_queue_id_seq'::regclass);


--
-- Name: policy_audit_log id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_audit_log ALTER COLUMN id SET DEFAULT nextval('public.policy_audit_log_id_seq'::regclass);


--
-- Name: policy_schedules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.policy_schedules ALTER COLUMN id SET DEFAULT nextval('public.policy_schedules_id_seq'::regclass);


--
-- Name: policy_ssh_logins id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_ssh_logins ALTER COLUMN id SET DEFAULT nextval('public.policy_ssh_logins_id_seq'::regclass);


--
-- Name: server_group_members id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_group_members ALTER COLUMN id SET DEFAULT nextval('public.server_group_members_id_seq'::regclass);


--
-- Name: server_groups id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_groups ALTER COLUMN id SET DEFAULT nextval('public.server_groups_id_seq'::regclass);


--
-- Name: servers id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.servers ALTER COLUMN id SET DEFAULT nextval('public.servers_id_seq'::regclass);


--
-- Name: session_recordings id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_recordings ALTER COLUMN id SET DEFAULT nextval('public.session_recordings_id_seq'::regclass);


--
-- Name: session_transfers id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_transfers ALTER COLUMN id SET DEFAULT nextval('public.session_transfers_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions ALTER COLUMN id SET DEFAULT nextval('public.sessions_id_seq'::regclass);


--
-- Name: stays id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays ALTER COLUMN id SET DEFAULT nextval('public.stays_id_seq'::regclass);


--
-- Name: user_group_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group_members ALTER COLUMN id SET DEFAULT nextval('public.user_group_members_id_seq'::regclass);


--
-- Name: user_groups id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups ALTER COLUMN id SET DEFAULT nextval('public.user_groups_id_seq'::regclass);


--
-- Name: user_source_ips id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.user_source_ips ALTER COLUMN id SET DEFAULT nextval('public.user_source_ips_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: access_grants; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.access_grants (id, user_id, server_id, protocol, start_time, end_time, is_active, granted_by, reason, created_at) FROM stdin;
\.


--
-- Data for Name: access_policies; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.access_policies (id, user_id, source_ip_id, scope_type, target_group_id, target_server_id, protocol, start_time, end_time, is_active, granted_by, reason, created_at, user_group_id, port_forwarding_allowed, use_schedules, created_by_user_id, inactivity_timeout_minutes, mfa_required) FROM stdin;
38	8	\N	server	\N	9	\N	2026-01-12 15:11:12.194243	2026-01-12 15:15:07.485493	t	\N	\N	2026-01-12 14:11:12.196109	\N	f	f	\N	60	f
48	12	\N	server	\N	10	ssh	2026-02-18 14:02:12.867597	2026-02-18 15:07:38.08771	t	AUTO-GRANT	Automatically created grant (7 days validity)	2026-02-18 14:02:12.905891	\N	t	f	\N	60	f
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.alembic_version (version_num) FROM stdin;
c50921c6cc09
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.audit_logs (id, user_id, action, resource_type, resource_id, source_ip, success, details, "timestamp") FROM stdin;
64	12	auto_user_create	\N	\N	100.64.0.39	t	Auto-created user from SAML: p.mojski@ideosoftware.com	2026-02-18 13:57:52.011815
26	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	No valid grant for 100.64.0.20	2026-01-04 10:56:34.152986
27	\N	rdp_access_denied	rdp_server	\N	100.64.0.39	f	No valid grant for 100.64.0.39	2026-01-04 11:02:47.942108
28	\N	rdp_access_denied	rdp_server	\N	100.64.0.39	f	No valid grant for 100.64.0.39	2026-01-04 11:38:28.235753
31	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 11:59:11.198401
32	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 11:59:22.200139
33	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 12:01:10.405665
29	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 11:55:11.077444
30	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 11:55:15.864489
34	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:01:46.330632
35	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:01:50.930145
36	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:59:06.03278
37	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:59:09.882358
38	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:13:21.449365
39	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:13:24.330431
40	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:16:18.822064
41	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:27:44.617036
42	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:27:48.408396
43	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:55:24.802918
44	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:55:28.922297
45	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:58:36.757779
46	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:58:39.976502
47	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:00:11.994079
48	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:00:19.295367
49	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:02:22.83807
50	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:02:29.72653
51	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:04:50.05205
52	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:04:53.513486
53	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:03.118953
54	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:07.698214
55	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:19.878931
56	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:22.991033
57	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:18:31.795677
58	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:18:36.954757
59	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 16:19:24.330016
60	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 16:20:11.562535
61	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-05 10:24:06.227923
62	\N	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-05 10:24:09.820938
\.


--
-- Data for Name: gates; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.gates (id, name, hostname, api_token, location, description, status, last_heartbeat, version, is_active, created_at, updated_at, ip_pool_start, ip_pool_end, ip_pool_network, in_maintenance, maintenance_scheduled_at, maintenance_reason, maintenance_grace_minutes, msg_welcome_banner, msg_no_backend, msg_no_person, msg_no_grant, msg_maintenance, msg_time_window, mfa_enabled, auto_grant_enabled, auto_grant_duration_days, auto_grant_inactivity_timeout_minutes, auto_grant_port_forwarding) FROM stdin;
4	tailscale-ideo	10.30.0.76	aabbccddideo	\N	Tailscale Ideo Exit Node	online	2026-02-18 14:23:27.552877	1.9.0	t	2026-01-28 14:09:16.474771	2026-02-18 14:23:27.552877	10.0.160.129	10.0.160.254	10.0.160.128/25	f	\N	\N	15	\N	\N	\N	\N	\N	\N	t	t	7	60	t
3	tailscale-etop	10.210.0.76	aabbccddetop	Tailscale Exit Node (etop)	TPROXY-enabled gate for Tailscale exit node deployment	online	2026-02-18 14:23:28.163428	1.9.0	t	2026-01-11 20:51:11.757995	2026-02-18 14:23:28.163428	10.210.200.129	10.210.200.254	10.210.200.128/25	f	\N	\N	15	\N	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nThe IP address is not registered as a backend server in Inside registry.\r\nPlease contact your system administrator for assistance.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nI can't recognize you and I don't know who you are.\r\nPlease contact your system administrator for assistance.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nDear {person}, you don't have access to {backend}.\r\nPlease contact your system administrator to request access.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nThe system is currently in maintenance mode.\r\nPlease try again later or contact your system administrator.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nDear {person}, your access to {backend} is outside the allowed time window.\r\nPlease contact your system administrator for assistance.	t	t	7	60	t
1	gate-localhost	localhost	localhost-default-token-changeme			online	2026-02-18 14:23:36.474556	1.9.0	t	2026-01-07 09:07:27.987596	2026-02-18 14:23:36.474556	10.0.160.129	10.0.160.254	10.0.160.128/25	f	\N	\N	15	\N	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nThe IP address is not registered as a backend server in Inside registry.\nPlease contact your system administrator for assistance.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nI can't recognize you and I don't know who you are.\nPlease contact your system administrator for assistance.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nDear {person}, you don't have access to {backend}.\nPlease contact your system administrator to request access.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nThe system is currently in maintenance mode.\nPlease try again later or contact your system administrator.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nDear {person}, your access to {backend} is outside the allowed time window.\nPlease contact your system administrator for assistance.	f	t	7	60	t
\.


--
-- Data for Name: ip_allocations; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.ip_allocations (id, allocated_ip, server_id, user_id, source_ip, allocated_at, expires_at, is_active, session_id, gate_id) FROM stdin;
5	10.0.160.129	1	\N	\N	2026-01-02 13:54:01.331136	\N	t	\N	1
7	10.0.160.130	2	\N	\N	2026-01-02 13:59:22.835593	\N	t	\N	1
8	10.0.160.131	4	\N	\N	2026-01-04 14:12:25.050222	\N	t	\N	1
9	10.0.160.132	5	\N	\N	2026-01-04 14:17:00.60646	\N	t	\N	1
10	10.0.160.133	6	\N	\N	2026-01-04 14:18:51.522007	\N	t	\N	1
12	10.0.160.134	7	\N	\N	2026-01-11 15:29:03.207916	\N	t	\N	1
13	10.0.160.135	8	\N	\N	2026-01-11 22:05:22.920736	\N	t	\N	1
14	10.0.160.136	9	\N	\N	2026-01-12 09:20:35.743699	\N	t	\N	1
\.


--
-- Data for Name: maintenance_access; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.maintenance_access (id, entity_type, entity_id, person_id, created_at) FROM stdin;
\.


--
-- Data for Name: mfa_challenges; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.mfa_challenges (id, token, gate_id, user_id, grant_id, ssh_username, created_at, expires_at, verified, verified_at, saml_email, destination_ip, source_ip) FROM stdin;
27	ODbFpe2BD28r4WhCuRNNRfGJkOTis2vYtx0TeHY6MyY	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:36:04.92672	2026-01-27 16:41:04.926682	f	\N	\N	\N	\N
28	5FWaGgx-VbI2UIua3dhTT8XKZr3HuppDb4tQbBmLOX4	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:37:14.363133	2026-01-27 16:42:14.363106	f	\N	\N	\N	\N
29	H_1zEau51utYK446DDQRJOs9ic_EbX1XKatPyzb7ioA	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:37:37.005227	2026-01-27 16:42:37.005178	f	\N	\N	\N	\N
40	mdIjE4vM1wSnpDeYiviu3jpZM3HWYrtEetOcDrs1OqY	3	\N	\N	p.mojski	2026-01-27 17:00:04.266291	2026-01-27 17:05:04.26627	f	\N	\N	10.210.1.189	\N
43	_5nzpoKJzv2TLh8dRPK8Sd_2G_jRnC-p3nkihT8pMEM	3	\N	\N	p.mojski	2026-01-27 17:05:15.822755	2026-01-27 17:10:15.822738	f	\N	\N	10.210.1.189	\N
44	aCqxZKaS7g8CGpYY1rxrLbO0UzGjKpnlZ58mT3oOggw	3	\N	\N	p.mojski	2026-01-28 07:25:50.300925	2026-01-28 07:30:50.300897	f	\N	\N	10.210.1.189	\N
45	3yl-B-djBzIgbvsZKrtV4ZOxx2-ornIp0x71gkJH2D0	3	\N	\N	p.mojski	2026-01-28 07:51:12.753323	2026-01-28 07:56:12.753299	f	\N	\N	10.210.1.189	\N
46	kdjVe4c2j5fJg8RPswp5x_YwSq0J3gsOVa9VzSZHznM	3	\N	\N	p.mojski	2026-01-28 07:51:17.559852	2026-01-28 07:56:17.55983	f	\N	\N	10.210.1.189	\N
47	MlBX6KTROOVKGJxr-J_Z2dAQbfvFceyIAmU_aEQiB80	3	\N	\N	p.mojski	2026-01-28 07:53:20.805813	2026-01-28 07:58:20.805793	f	\N	\N	10.210.1.189	\N
48	-Zy08aQYXRzL3ar6c76qIvsvLVrRYQe8exXou6wEdIQ	3	\N	\N	p.mojski	2026-01-28 07:54:53.658248	2026-01-28 07:59:53.658225	f	\N	\N	10.210.1.189	\N
49	BvIO4FOWBCwmjSEUc4gXCC1D3oG_tJTKKbOEKG4aw7Q	3	\N	\N	p.mojski	2026-01-28 07:55:25.292666	2026-01-28 08:00:25.292651	f	\N	\N	10.210.1.189	\N
50	unHsW0NJkMBekx-sV6RG_ggcbTOt4L3RZFg8EK22hms	3	\N	\N	p.mojski	2026-01-28 07:55:29.590353	2026-01-28 08:00:29.59033	f	\N	\N	10.210.1.189	\N
51	TzP-hZjryctg8AM9AJiy0WjzEA8C_Ouf3-p-UmzCms4	3	\N	\N	p.mojski	2026-01-28 08:08:02.948947	2026-01-28 08:13:02.94892	f	\N	\N	10.210.1.189	\N
54	yGSbHsCQI4wMtLWs1ypLcFepsxo7zkqFivqBSsw7B6k	3	\N	\N	p.mojski	2026-01-28 08:16:52.652678	2026-01-28 08:21:52.652657	f	\N	\N	10.210.1.189	\N
150	6FbnJaNkcRMQAgQKhLUWX9WNLOhZwc-FTyFT7WPYm2I	4	12	\N	pmojski	2026-02-18 13:57:43.514739	2026-02-18 14:02:43.514713	t	2026-02-18 13:57:52.018995	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
58	pI8dM_O-34xvMeOxgcRMDDK7yjRot8v3iQCueLukJoc	3	\N	\N	p.mojski	2026-01-28 08:44:18.844461	2026-01-28 08:49:18.844444	f	\N	\N	10.210.1.189	\N
62	MFcORljEwBwF_N_tNsR8BKbAZ2m3vYOoGTpiKDMs_jY	3	\N	\N	p.mojski	2026-01-28 08:53:34.370232	2026-01-28 08:58:34.370185	f	\N	\N	10.210.1.189	\N
63	4W1RQYGq3rnBsREUP4R7UoVekq6G-YPqYM4NsdQ-_OM	3	\N	\N	p.mojski	2026-01-28 08:53:56.894956	2026-01-28 08:58:56.894928	f	\N	\N	10.210.1.189	\N
64	gPeESmQhG3U4sszn_HFSQ95h11CYBC8TZRx1HSq-5hc	3	\N	\N	p.mojski	2026-01-28 08:55:15.184369	2026-01-28 09:00:15.18433	f	\N	\N	10.210.1.189	\N
66	PPvF3Cg2cQEc_VOfsq1No4TjcGrAColMqOnLVtpqI6o	3	\N	\N	p.mojski	2026-01-28 09:11:15.932595	2026-01-28 09:16:15.932573	f	\N	\N	10.210.1.189	\N
67	WJVvo4ojdlLPdYyJhwhfjem202dX7wzwS4kbpMx00CE	3	\N	\N	p.mojski	2026-01-28 09:14:29.708875	2026-01-28 09:19:29.708849	f	\N	\N	10.210.1.189	\N
74	XUxKtSX52h8y5eyLMyI9mkJuZGUYecH_z4Qgh2qeNRo	3	\N	\N	p.mojski	2026-01-28 09:35:33.843878	2026-01-28 09:40:33.843849	f	\N	\N	10.210.1.189	100.64.0.20
79	klLzcEa5dFZJGp0b-r0-WKTAMnCwD6PCQnDXeFIWe8Y	3	\N	\N	p.mojski	2026-01-28 09:41:55.576909	2026-01-28 09:46:55.576885	f	\N	\N	10.210.1.189	100.64.0.20
104	LV0uTa7o6YfbeoLM0TPXhkskVWAT70keiYMxWoNjNKo	3	\N	\N	p.mojski	2026-01-28 11:29:52.25887	2026-01-28 11:34:52.258851	f	\N	\N	10.210.1.190	100.64.0.20
105	kCGs0LZghjk469yHVtMfMNZpzefDIJE8dfmwg6sD9l8	3	\N	\N	p.mojski	2026-01-28 11:34:49.619049	2026-01-28 11:39:49.619023	f	\N	\N	10.210.1.189	100.64.0.20
151	VrfI_uAksDssXOcwj-G_r78ZIpLUPKLDMpmz_JDiaDg	4	12	\N	pmojski	2026-02-18 14:01:58.327524	2026-02-18 14:06:58.327508	t	2026-02-18 14:02:10.930452	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
129	1T3xhWbCONFdDCmtfmWXti9SE1zP6fh9LCUKc36G0FA	4	\N	\N	pmojski	2026-01-28 15:21:33.288429	2026-01-28 15:26:33.288393	f	\N	\N	10.30.14.3	100.64.0.20
142	J1ThSowm_WTl3pezL1MR_RKnIc2oPPo3-zdcXZ5LrCk	4	\N	\N	pmojski	2026-02-18 12:35:32.617525	2026-02-18 12:40:32.617498	f	\N	\N	10.30.14.3	100.64.0.20
\.


--
-- Data for Name: mp4_conversion_queue; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.mp4_conversion_queue (id, session_id, status, progress, total, eta_seconds, priority, mp4_path, error_msg, created_at, started_at, completed_at) FROM stdin;
1	9110480	completed	254	254	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/9110480-rdp_replay_20260104_16-20-11_536_objective_swanson_9110480.mp4	Conversion failed with return code 0	2026-01-05 09:18:09.183805	2026-01-05 09:18:10.235726	2026-01-05 09:18:50.287724
8	thirsty_pare_8468314	completed	228	228	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/thirsty_pare_8468314-rdp_replay_20260104_15-04-53_488_thirsty_pare_8468314.mp4	\N	2026-01-05 09:48:48.460338	2026-01-05 09:48:50.112854	2026-01-05 09:49:04.738434
5	objective_swanson_9110480	completed	254	254	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/objective_swanson_9110480-rdp_replay_20260104_16-20-11_536_objective_swanson_9110480.mp4	\N	2026-01-05 09:34:18.028084	2026-01-05 09:34:18.939367	2026-01-05 09:34:58.175927
9	eloquent_galileo_8262673	completed	793	793	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/eloquent_galileo_8262673-rdp_replay_20260105_10-24-09_804_eloquent_galileo_8262673.mp4	\N	2026-01-05 10:25:45.012205	2026-01-05 10:25:45.33835	2026-01-05 10:26:28.385859
2	1488495	completed	146	146	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/1488495-rdp_replay_20260102_13-25-26_274_mystifying_poincare_1488495.mp4	\N	2026-01-05 09:20:12.949341	2026-01-05 09:20:14.819688	2026-01-05 09:20:23.995866
7	awesome_jang_4293901	completed	178	178	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/awesome_jang_4293901-rdp_replay_20260104_15-18-36_927_awesome_jang_4293901.mp4	\N	2026-01-05 09:44:57.870531	2026-01-05 09:45:00.903234	2026-01-05 09:45:24.901967
6	frosty_bassi_6767861	completed	218	218	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/frosty_bassi_6767861-rdp_replay_20260104_15-06-22_974_frosty_bassi_6767861.mp4	\N	2026-01-05 09:42:51.438319	2026-01-05 09:42:53.692636	2026-01-05 09:43:12.733791
3	6177986	completed	160	160	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/6177986-rdp_replay_20260102_13-04-56_287_quizzical_lamarr_6177986.mp4	\N	2026-01-05 09:21:15.814484	2026-01-05 09:21:19.066966	2026-01-05 09:21:28.136316
4	6003773	completed	151	151	0	0	/var/log/jumphost/rdp_recordings/mp4_cache/6003773-rdp_replay_20260104_12-01-50_917_keen_euclid_6003773.mp4	\N	2026-01-05 09:21:15.814492	2026-01-05 09:21:19.954571	2026-01-05 09:21:29.44287
\.


--
-- Data for Name: policy_audit_log; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.policy_audit_log (id, policy_id, changed_by_user_id, change_type, field_name, old_value, new_value, full_old_state, full_new_state, changed_at) FROM stdin;
\.


--
-- Data for Name: policy_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.policy_schedules (id, policy_id, name, weekdays, time_start, time_end, months, days_of_month, timezone, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: policy_ssh_logins; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.policy_ssh_logins (id, policy_id, allowed_login) FROM stdin;
\.


--
-- Data for Name: server_group_members; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.server_group_members (id, server_id, group_id, added_at) FROM stdin;
4	4	3	2026-01-04 13:51:33.171138
5	5	3	2026-01-04 14:19:17.055145
\.


--
-- Data for Name: server_groups; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.server_groups (id, name, description, created_at, updated_at, parent_group_id) FROM stdin;
3	etop switches	Switche 	2026-01-04 13:36:58.929476	2026-01-04 13:36:58.929486	\N
\.


--
-- Data for Name: servers; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.servers (id, name, ip_address, description, os_type, is_active, created_at, updated_at, ssh_port, rdp_port, in_maintenance, maintenance_scheduled_at, maintenance_reason, maintenance_grace_minutes) FROM stdin;
2	Windows-RDP-Server	10.30.0.140	\N	linux	t	2026-01-02 12:48:20.652893	2026-01-02 12:48:20.6529	\N	\N	f	\N	\N	15
4	etop switch lan	172.20.20.240		\N	t	2026-01-04 13:49:03.772892	2026-01-04 13:49:03.772899	22	3389	f	\N	\N	15
5	etop switch 10g	172.20.20.241		\N	t	2026-01-04 14:15:39.092158	2026-01-04 14:15:39.092166	22	3389	f	\N	\N	15
7	switch SW-L-1G-3	10.30.10.15		\N	t	2026-01-11 15:29:03.193476	2026-01-11 15:29:03.193487	22	3389	f	\N	\N	15
1	Test-SSH-Server	10.0.160.4	Test SSH server for jumphost	linux	t	2026-01-02 11:08:06.473784	2026-01-11 19:13:42.395565	\N	\N	f	\N	\N	5
6	router wan	185.30.125.254		\N	t	2026-01-04 14:18:51.511993	2026-01-12 07:22:29.438227	22	3389	f	\N	\N	15
8	rancher-2	10.210.1.190		\N	t	2026-01-11 22:05:22.912961	2026-01-12 07:24:51.125411	22	3389	f	\N	\N	15
9	rancher1	10.210.1.189		\N	t	2026-01-12 09:20:35.733606	2026-01-12 09:20:35.73361	22	3389	f	\N	\N	15
10	p.mojski - lab	10.30.14.3		\N	t	2026-01-28 13:18:08.55085	2026-01-28 13:18:08.550864	22	3389	f	\N	\N	15
11	ideo 10g	10.30.10.29		\N	t	2026-01-28 13:34:59.997274	2026-01-28 13:34:59.997282	22	3389	f	\N	\N	15
12	ideo sw p105	10.30.10.3		\N	t	2026-01-28 13:48:12.236598	2026-01-28 13:48:12.236606	22	3389	f	\N	\N	15
\.


--
-- Data for Name: session_recordings; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.session_recordings (id, session_id, user_id, server_id, protocol, source_ip, allocated_ip, recording_path, start_time, end_time, duration_seconds, file_size_bytes, gate_id) FROM stdin;
\.


--
-- Data for Name: session_transfers; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.session_transfers (id, session_id, transfer_type, file_path, file_size, local_addr, local_port, remote_addr, remote_port, bytes_sent, bytes_received, started_at, ended_at) FROM stdin;
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.sessions (id, session_id, user_id, server_id, protocol, source_ip, proxy_ip, backend_ip, backend_port, ssh_username, started_at, ended_at, duration_seconds, recording_path, recording_size, is_active, termination_reason, policy_id, created_at, subsystem_name, ssh_agent_used, connection_status, denial_reason, denial_details, protocol_version, stay_id, gate_id) FROM stdin;
323	100.64.0.20_1771423318.118796	12	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 14:02:15.714703	2026-02-18 14:06:58.468596	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_150215_100.64.0.20_1771423318.118796.rec	2216	f	normal	48	2026-02-18 14:02:15.719423	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	149	4
324	100.64.0.20_1771423600.269214	12	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 14:06:40.810062	2026-02-18 14:06:42.90472	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_150640_100.64.0.20_1771423600.269214.rec	2159	f	normal	48	2026-02-18 14:06:40.810789	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	149	4
231	100.64.0.1_1768227178.510036	8	9	ssh	100.64.0.1	10.210.1.189	10.210.1.189	22	k.kawalec	2026-01-12 14:12:59.719424	2026-01-12 16:00:47.757565	6468	/opt/jumphost/logs/recordings/20260112/k.kawalec_rancher1_20260112_151259_100.64.0.1_1768227178.510036.rec	\N	f	gate_restart	38	2026-01-12 14:12:59.722226	\N	t	active	\N	No matching policy (user or group)	SSH-2.0-OpenSSH_10.0	79	3
\.


--
-- Data for Name: stays; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.stays (id, user_id, policy_id, gate_id, server_id, started_at, ended_at, duration_seconds, is_active, termination_reason, created_at, updated_at, ssh_key_fingerprint) FROM stdin;
149	12	48	4	10	2026-02-18 14:02:15.709271	2026-02-18 14:06:58.311574	282	f	grant_revoked	2026-02-18 14:02:15.711143	2026-02-18 14:06:58.351154	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
79	8	38	3	9	2026-01-12 14:12:59.71231	2026-01-12 16:00:47.757565	6468	f	gate_restart	2026-01-12 14:12:59.715475	2026-01-12 16:00:47.770575	\N
\.


--
-- Data for Name: user_group_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_group_members (id, user_group_id, user_id, added_at) FROM stdin;
\.


--
-- Data for Name: user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_groups (id, name, description, parent_group_id, created_at) FROM stdin;
1	root	Root group	\N	2026-01-05 11:40:10.813669
2	admins	Admin group	1	2026-01-05 11:40:10.823444
3	users	Regular users	2	2026-01-05 11:40:10.82729
\.


--
-- Data for Name: user_source_ips; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.user_source_ips (id, user_id, source_ip, label, is_active, created_at) FROM stdin;
8	8	100.64.0.1	\N	t	2026-01-12 14:10:39.497108
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.users (id, username, email, full_name, is_active, created_at, updated_at, source_ip, port_forwarding_allowed, permission_level) FROM stdin;
8	k.kawalec	k.kawalec@ideosoftware.com	Krzysztof Kawalec	t	2026-01-12 14:10:12.266367	2026-01-12 14:10:12.26638	\N	f	1000
7	admin	admin@jumphost.local	\N	t	2026-01-04 13:32:30.049145	2026-01-04 13:32:30.049152	\N	f	0
12	p.mojski	p.mojski@ideosoftware.com	Paweł Mojski	t	2026-02-18 13:57:52.008823	2026-02-18 14:05:08.764662	\N	f	1000
\.


--
-- Name: access_grants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.access_grants_id_seq', 6, true);


--
-- Name: access_policies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.access_policies_id_seq', 48, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 65, true);


--
-- Name: gates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.gates_id_seq', 4, true);


--
-- Name: ip_allocations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.ip_allocations_id_seq', 14, true);


--
-- Name: maintenance_access_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.maintenance_access_id_seq', 2, true);


--
-- Name: mfa_challenges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.mfa_challenges_id_seq', 152, true);


--
-- Name: mp4_conversion_queue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.mp4_conversion_queue_id_seq', 9, true);


--
-- Name: policy_audit_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.policy_audit_log_id_seq', 33, true);


--
-- Name: policy_schedules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.policy_schedules_id_seq', 12, true);


--
-- Name: policy_ssh_logins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.policy_ssh_logins_id_seq', 32, true);


--
-- Name: server_group_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.server_group_members_id_seq', 5, true);


--
-- Name: server_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.server_groups_id_seq', 3, true);


--
-- Name: servers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.servers_id_seq', 12, true);


--
-- Name: session_recordings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.session_recordings_id_seq', 1, false);


--
-- Name: session_transfers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.session_transfers_id_seq', 8, true);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.sessions_id_seq', 324, true);


--
-- Name: stays_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.stays_id_seq', 149, true);


--
-- Name: user_group_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_group_members_id_seq', 1, true);


--
-- Name: user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_groups_id_seq', 3, true);


--
-- Name: user_source_ips_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.user_source_ips_id_seq', 8, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.users_id_seq', 12, true);


--
-- Name: access_grants access_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_grants
    ADD CONSTRAINT access_grants_pkey PRIMARY KEY (id);


--
-- Name: access_policies access_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: gates gates_api_token_key; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.gates
    ADD CONSTRAINT gates_api_token_key UNIQUE (api_token);


--
-- Name: gates gates_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.gates
    ADD CONSTRAINT gates_pkey PRIMARY KEY (id);


--
-- Name: ip_allocations ip_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations
    ADD CONSTRAINT ip_allocations_pkey PRIMARY KEY (id);


--
-- Name: ip_allocations ip_allocations_session_id_key; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations
    ADD CONSTRAINT ip_allocations_session_id_key UNIQUE (session_id);


--
-- Name: maintenance_access maintenance_access_entity_type_entity_id_person_id_key; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.maintenance_access
    ADD CONSTRAINT maintenance_access_entity_type_entity_id_person_id_key UNIQUE (entity_type, entity_id, person_id);


--
-- Name: maintenance_access maintenance_access_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.maintenance_access
    ADD CONSTRAINT maintenance_access_pkey PRIMARY KEY (id);


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);


--
-- Name: mfa_challenges mfa_challenges_token_key; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges
    ADD CONSTRAINT mfa_challenges_token_key UNIQUE (token);


--
-- Name: mp4_conversion_queue mp4_conversion_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mp4_conversion_queue
    ADD CONSTRAINT mp4_conversion_queue_pkey PRIMARY KEY (id);


--
-- Name: policy_audit_log policy_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_audit_log
    ADD CONSTRAINT policy_audit_log_pkey PRIMARY KEY (id);


--
-- Name: policy_schedules policy_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.policy_schedules
    ADD CONSTRAINT policy_schedules_pkey PRIMARY KEY (id);


--
-- Name: policy_ssh_logins policy_ssh_logins_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_ssh_logins
    ADD CONSTRAINT policy_ssh_logins_pkey PRIMARY KEY (id);


--
-- Name: server_group_members server_group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_group_members
    ADD CONSTRAINT server_group_members_pkey PRIMARY KEY (id);


--
-- Name: server_groups server_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_groups
    ADD CONSTRAINT server_groups_pkey PRIMARY KEY (id);


--
-- Name: servers servers_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.servers
    ADD CONSTRAINT servers_pkey PRIMARY KEY (id);


--
-- Name: session_recordings session_recordings_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_recordings
    ADD CONSTRAINT session_recordings_pkey PRIMARY KEY (id);


--
-- Name: session_transfers session_transfers_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_transfers
    ADD CONSTRAINT session_transfers_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: stays stays_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays
    ADD CONSTRAINT stays_pkey PRIMARY KEY (id);


--
-- Name: user_group_members user_group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_pkey PRIMARY KEY (id);


--
-- Name: user_group_members user_group_members_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_unique UNIQUE (user_group_id, user_id);


--
-- Name: user_groups user_groups_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_name_key UNIQUE (name);


--
-- Name: user_groups user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);


--
-- Name: user_source_ips user_source_ips_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.user_source_ips
    ADD CONSTRAINT user_source_ips_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_gates_auto_grant_enabled; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_gates_auto_grant_enabled ON public.gates USING btree (auto_grant_enabled) WHERE (auto_grant_enabled IS NOT NULL);


--
-- Name: idx_maintenance_access_lookup; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_maintenance_access_lookup ON public.maintenance_access USING btree (entity_type, entity_id, person_id);


--
-- Name: idx_mfa_challenges_destination; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_mfa_challenges_destination ON public.mfa_challenges USING btree (destination_ip);


--
-- Name: idx_mfa_challenges_gate_user; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_mfa_challenges_gate_user ON public.mfa_challenges USING btree (gate_id, user_id) WHERE (user_id IS NOT NULL);


--
-- Name: idx_mfa_challenges_token; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_mfa_challenges_token ON public.mfa_challenges USING btree (token);


--
-- Name: idx_mfa_challenges_verified; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_mfa_challenges_verified ON public.mfa_challenges USING btree (verified, expires_at);


--
-- Name: idx_policy_audit_log_change_type; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_policy_audit_log_change_type ON public.policy_audit_log USING btree (change_type);


--
-- Name: idx_policy_audit_log_changed_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_policy_audit_log_changed_at ON public.policy_audit_log USING btree (changed_at);


--
-- Name: idx_policy_audit_log_policy_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_policy_audit_log_policy_id ON public.policy_audit_log USING btree (policy_id);


--
-- Name: idx_policy_schedules_policy_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_policy_schedules_policy_id ON public.policy_schedules USING btree (policy_id);


--
-- Name: idx_sessions_connection_status; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_sessions_connection_status ON public.sessions USING btree (connection_status);


--
-- Name: idx_sessions_denial_reason; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_sessions_denial_reason ON public.sessions USING btree (denial_reason);


--
-- Name: idx_sessions_policy_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_sessions_policy_id ON public.sessions USING btree (policy_id);


--
-- Name: idx_stays_fingerprint; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_stays_fingerprint ON public.stays USING btree (ssh_key_fingerprint, is_active) WHERE (ssh_key_fingerprint IS NOT NULL);


--
-- Name: idx_users_permission_level; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX idx_users_permission_level ON public.users USING btree (permission_level);


--
-- Name: ix_access_grants_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_grants_id ON public.access_grants USING btree (id);


--
-- Name: ix_access_grants_server_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_grants_server_id ON public.access_grants USING btree (server_id);


--
-- Name: ix_access_grants_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_grants_user_id ON public.access_grants USING btree (user_id);


--
-- Name: ix_access_policies_end_time; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_end_time ON public.access_policies USING btree (end_time);


--
-- Name: ix_access_policies_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_id ON public.access_policies USING btree (id);


--
-- Name: ix_access_policies_is_active; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_is_active ON public.access_policies USING btree (is_active);


--
-- Name: ix_access_policies_scope_type; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_scope_type ON public.access_policies USING btree (scope_type);


--
-- Name: ix_access_policies_source_ip_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_source_ip_id ON public.access_policies USING btree (source_ip_id);


--
-- Name: ix_access_policies_start_time; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_start_time ON public.access_policies USING btree (start_time);


--
-- Name: ix_access_policies_target_group_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_target_group_id ON public.access_policies USING btree (target_group_id);


--
-- Name: ix_access_policies_target_server_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_target_server_id ON public.access_policies USING btree (target_server_id);


--
-- Name: ix_access_policies_user_group_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_user_group_id ON public.access_policies USING btree (user_group_id);


--
-- Name: ix_access_policies_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_access_policies_user_id ON public.access_policies USING btree (user_id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_audit_logs_timestamp ON public.audit_logs USING btree ("timestamp");


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_gates_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_gates_id ON public.gates USING btree (id);


--
-- Name: ix_gates_name; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_gates_name ON public.gates USING btree (name);


--
-- Name: ix_ip_allocations_allocated_ip_gate; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_ip_allocations_allocated_ip_gate ON public.ip_allocations USING btree (allocated_ip, gate_id);


--
-- Name: ix_ip_allocations_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_ip_allocations_id ON public.ip_allocations USING btree (id);


--
-- Name: ix_mp4_conversion_queue_created_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_mp4_conversion_queue_created_at ON public.mp4_conversion_queue USING btree (created_at);


--
-- Name: ix_mp4_conversion_queue_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_mp4_conversion_queue_id ON public.mp4_conversion_queue USING btree (id);


--
-- Name: ix_mp4_conversion_queue_priority; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_mp4_conversion_queue_priority ON public.mp4_conversion_queue USING btree (priority);


--
-- Name: ix_mp4_conversion_queue_session_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_mp4_conversion_queue_session_id ON public.mp4_conversion_queue USING btree (session_id);


--
-- Name: ix_mp4_conversion_queue_status; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_mp4_conversion_queue_status ON public.mp4_conversion_queue USING btree (status);


--
-- Name: ix_policy_ssh_logins_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_policy_ssh_logins_id ON public.policy_ssh_logins USING btree (id);


--
-- Name: ix_policy_ssh_logins_policy_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_policy_ssh_logins_policy_id ON public.policy_ssh_logins USING btree (policy_id);


--
-- Name: ix_server_group_members_group_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_server_group_members_group_id ON public.server_group_members USING btree (group_id);


--
-- Name: ix_server_group_members_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_server_group_members_id ON public.server_group_members USING btree (id);


--
-- Name: ix_server_group_members_server_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_server_group_members_server_id ON public.server_group_members USING btree (server_id);


--
-- Name: ix_server_groups_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_server_groups_id ON public.server_groups USING btree (id);


--
-- Name: ix_server_groups_name; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_server_groups_name ON public.server_groups USING btree (name);


--
-- Name: ix_server_groups_parent_group_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_server_groups_parent_group_id ON public.server_groups USING btree (parent_group_id);


--
-- Name: ix_servers_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_servers_id ON public.servers USING btree (id);


--
-- Name: ix_servers_ip_address; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_servers_ip_address ON public.servers USING btree (ip_address);


--
-- Name: ix_session_recordings_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_session_recordings_id ON public.session_recordings USING btree (id);


--
-- Name: ix_session_recordings_session_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_session_recordings_session_id ON public.session_recordings USING btree (session_id);


--
-- Name: ix_session_transfers_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_session_transfers_id ON public.session_transfers USING btree (id);


--
-- Name: ix_session_transfers_session_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_session_transfers_session_id ON public.session_transfers USING btree (session_id);


--
-- Name: ix_session_transfers_started_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_session_transfers_started_at ON public.session_transfers USING btree (started_at);


--
-- Name: ix_session_transfers_transfer_type; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_session_transfers_transfer_type ON public.session_transfers USING btree (transfer_type);


--
-- Name: ix_sessions_ended_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_ended_at ON public.sessions USING btree (ended_at);


--
-- Name: ix_sessions_gate_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_gate_id ON public.sessions USING btree (gate_id);


--
-- Name: ix_sessions_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_id ON public.sessions USING btree (id);


--
-- Name: ix_sessions_is_active; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_is_active ON public.sessions USING btree (is_active);


--
-- Name: ix_sessions_protocol; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_protocol ON public.sessions USING btree (protocol);


--
-- Name: ix_sessions_server_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_server_id ON public.sessions USING btree (server_id);


--
-- Name: ix_sessions_session_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_sessions_session_id ON public.sessions USING btree (session_id);


--
-- Name: ix_sessions_started_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_started_at ON public.sessions USING btree (started_at);


--
-- Name: ix_sessions_stay_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_stay_id ON public.sessions USING btree (stay_id);


--
-- Name: ix_sessions_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: ix_stays_ended_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_ended_at ON public.stays USING btree (ended_at);


--
-- Name: ix_stays_gate_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_gate_id ON public.stays USING btree (gate_id);


--
-- Name: ix_stays_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_id ON public.stays USING btree (id);


--
-- Name: ix_stays_is_active; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_is_active ON public.stays USING btree (is_active);


--
-- Name: ix_stays_policy_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_policy_id ON public.stays USING btree (policy_id);


--
-- Name: ix_stays_server_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_server_id ON public.stays USING btree (server_id);


--
-- Name: ix_stays_started_at; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_started_at ON public.stays USING btree (started_at);


--
-- Name: ix_stays_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_stays_user_id ON public.stays USING btree (user_id);


--
-- Name: ix_user_group_members_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_group_members_group_id ON public.user_group_members USING btree (user_group_id);


--
-- Name: ix_user_group_members_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_group_members_user_id ON public.user_group_members USING btree (user_id);


--
-- Name: ix_user_groups_parent_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_groups_parent_group_id ON public.user_groups USING btree (parent_group_id);


--
-- Name: ix_user_source_ips_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_user_source_ips_id ON public.user_source_ips USING btree (id);


--
-- Name: ix_user_source_ips_source_ip; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_user_source_ips_source_ip ON public.user_source_ips USING btree (source_ip);


--
-- Name: ix_user_source_ips_user_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_user_source_ips_user_id ON public.user_source_ips USING btree (user_id);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_source_ip; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE INDEX ix_users_source_ip ON public.users USING btree (source_ip);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: jumphost_user
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: access_grants access_grants_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_grants
    ADD CONSTRAINT access_grants_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: access_grants access_grants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_grants
    ADD CONSTRAINT access_grants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: access_policies access_policies_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: access_policies access_policies_source_ip_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_source_ip_id_fkey FOREIGN KEY (source_ip_id) REFERENCES public.user_source_ips(id);


--
-- Name: access_policies access_policies_target_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_target_group_id_fkey FOREIGN KEY (target_group_id) REFERENCES public.server_groups(id);


--
-- Name: access_policies access_policies_target_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_target_server_id_fkey FOREIGN KEY (target_server_id) REFERENCES public.servers(id);


--
-- Name: access_policies access_policies_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES public.user_groups(id) ON DELETE CASCADE;


--
-- Name: access_policies access_policies_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.access_policies
    ADD CONSTRAINT access_policies_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: ip_allocations ip_allocations_gate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations
    ADD CONSTRAINT ip_allocations_gate_id_fkey FOREIGN KEY (gate_id) REFERENCES public.gates(id);


--
-- Name: ip_allocations ip_allocations_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations
    ADD CONSTRAINT ip_allocations_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: ip_allocations ip_allocations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.ip_allocations
    ADD CONSTRAINT ip_allocations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: maintenance_access maintenance_access_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.maintenance_access
    ADD CONSTRAINT maintenance_access_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.users(id);


--
-- Name: mfa_challenges mfa_challenges_gate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges
    ADD CONSTRAINT mfa_challenges_gate_id_fkey FOREIGN KEY (gate_id) REFERENCES public.gates(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_grant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges
    ADD CONSTRAINT mfa_challenges_grant_id_fkey FOREIGN KEY (grant_id) REFERENCES public.access_policies(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.mfa_challenges
    ADD CONSTRAINT mfa_challenges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: policy_audit_log policy_audit_log_changed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_audit_log
    ADD CONSTRAINT policy_audit_log_changed_by_user_id_fkey FOREIGN KEY (changed_by_user_id) REFERENCES public.users(id);


--
-- Name: policy_audit_log policy_audit_log_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_audit_log
    ADD CONSTRAINT policy_audit_log_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.access_policies(id) ON DELETE CASCADE;


--
-- Name: policy_schedules policy_schedules_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.policy_schedules
    ADD CONSTRAINT policy_schedules_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.access_policies(id) ON DELETE CASCADE;


--
-- Name: policy_ssh_logins policy_ssh_logins_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.policy_ssh_logins
    ADD CONSTRAINT policy_ssh_logins_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.access_policies(id) ON DELETE CASCADE;


--
-- Name: server_group_members server_group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_group_members
    ADD CONSTRAINT server_group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.server_groups(id);


--
-- Name: server_group_members server_group_members_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_group_members
    ADD CONSTRAINT server_group_members_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: server_groups server_groups_parent_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.server_groups
    ADD CONSTRAINT server_groups_parent_group_id_fkey FOREIGN KEY (parent_group_id) REFERENCES public.server_groups(id) ON DELETE SET NULL;


--
-- Name: session_recordings session_recordings_gate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_recordings
    ADD CONSTRAINT session_recordings_gate_id_fkey FOREIGN KEY (gate_id) REFERENCES public.gates(id);


--
-- Name: session_recordings session_recordings_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_recordings
    ADD CONSTRAINT session_recordings_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: session_recordings session_recordings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_recordings
    ADD CONSTRAINT session_recordings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: session_transfers session_transfers_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.session_transfers
    ADD CONSTRAINT session_transfers_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_gate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_gate_id_fkey FOREIGN KEY (gate_id) REFERENCES public.gates(id);


--
-- Name: sessions sessions_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.access_policies(id);


--
-- Name: sessions sessions_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: sessions sessions_stay_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_stay_id_fkey FOREIGN KEY (stay_id) REFERENCES public.stays(id);


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: stays stays_gate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays
    ADD CONSTRAINT stays_gate_id_fkey FOREIGN KEY (gate_id) REFERENCES public.gates(id);


--
-- Name: stays stays_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays
    ADD CONSTRAINT stays_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.access_policies(id);


--
-- Name: stays stays_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays
    ADD CONSTRAINT stays_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.servers(id);


--
-- Name: stays stays_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.stays
    ADD CONSTRAINT stays_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_group_members user_group_members_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES public.user_groups(id) ON DELETE CASCADE;


--
-- Name: user_group_members user_group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_groups user_groups_parent_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_parent_group_id_fkey FOREIGN KEY (parent_group_id) REFERENCES public.user_groups(id) ON DELETE SET NULL;


--
-- Name: user_source_ips user_source_ips_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jumphost_user
--

ALTER TABLE ONLY public.user_source_ips
    ADD CONSTRAINT user_source_ips_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO jumphost_user;


--
-- Name: TABLE policy_schedules; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.policy_schedules TO jumphost_user;


--
-- Name: SEQUENCE policy_schedules_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.policy_schedules_id_seq TO jumphost_user;


--
-- Name: TABLE user_group_members; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.user_group_members TO jumphost_user;


--
-- Name: SEQUENCE user_group_members_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.user_group_members_id_seq TO jumphost_user;


--
-- Name: TABLE user_groups; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.user_groups TO jumphost_user;


--
-- Name: SEQUENCE user_groups_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.user_groups_id_seq TO jumphost_user;


--
-- PostgreSQL database dump complete
--

\unrestrict HoqwKJgL4mfQaj3cGwvvfdzaYWsSR8amVrkO6UN8piF8gSh8ZJGfpJcHejETLCG

