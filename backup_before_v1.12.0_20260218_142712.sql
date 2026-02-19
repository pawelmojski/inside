--
-- PostgreSQL database dump
--

\restrict B3KL1Rzel6NcvHExPH8HX2Km38MzIE4chf9W8qOGg2obemTgV6mBgerekkjWZl6

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
    mfa_enabled boolean DEFAULT false NOT NULL
);


ALTER TABLE public.gates OWNER TO jumphost_user;

--
-- Name: COLUMN gates.mfa_enabled; Type: COMMENT; Schema: public; Owner: jumphost_user
--

COMMENT ON COLUMN public.gates.mfa_enabled IS 'If true, gate uses MFA for unknown IPs with fingerprint-based sessions';


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
    port_forwarding_allowed boolean DEFAULT false NOT NULL
);


ALTER TABLE public.users OWNER TO jumphost_user;

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
10	6	\N	group	3	\N	\N	2026-01-04 15:06:45.915958	2026-01-04 16:06:45.910929	t	\N	\N	2026-01-04 14:06:45.915967	\N	f	f	7	60	f
15	6	\N	server	\N	1	\N	2026-01-05 13:45:24.551533	2026-01-06 17:18:58.451274	t	\N	\N	2026-01-05 12:45:24.551539	\N	t	f	7	60	f
30	6	\N	service	\N	1	ssh	2026-01-06 17:28:00	2026-02-05 18:46:00	t	\N	\N	2026-01-06 16:28:44.633155	\N	t	t	7	60	f
33	6	\N	server	\N	7	\N	2026-01-11 16:30:06.376204	\N	t	\N	\N	2026-01-11 15:30:06.378955	\N	f	f	\N	60	f
34	6	\N	server	\N	8	\N	2026-01-11 23:06:00	2026-01-12 11:17:18.360555	t	\N	\N	2026-01-11 22:06:09.398423	\N	t	f	\N	60	f
36	6	\N	server	\N	8	\N	2026-01-12 11:35:00	2026-01-12 11:36:00	t	\N	\N	2026-01-12 10:35:43.271596	\N	t	t	\N	60	f
38	8	\N	server	\N	9	\N	2026-01-12 15:11:12.194243	2026-01-12 15:15:07.485493	t	\N	\N	2026-01-12 14:11:12.196109	\N	f	f	\N	60	f
35	6	\N	server	\N	9	\N	2026-01-12 10:21:41.398677	2026-01-12 15:30:51.599798	t	\N	\N	2026-01-12 09:21:41.403845	\N	t	f	\N	60	f
40	6	\N	server	\N	8	\N	2026-01-12 17:06:29.616314	2026-01-12 17:25:24.677506	t	\N	\N	2026-01-12 16:06:29.621094	\N	f	f	\N	60	f
41	6	\N	server	\N	8	\N	2026-01-12 17:26:14.625416	2026-01-12 17:26:32.864483	t	\N	\N	2026-01-12 16:26:14.626952	\N	f	f	\N	60	f
42	6	\N	server	\N	8	\N	2026-01-12 17:32:00	2026-01-12 17:43:00	t	\N	\N	2026-01-12 16:32:53.621585	\N	f	f	\N	60	f
11	6	\N	server	\N	6	\N	2026-01-04 15:26:16.535979	2026-01-04 16:26:16.533292	t	\N	\N	2026-01-04 14:26:16.535988	\N	f	f	7	60	f
25	6	\N	server	\N	1	ssh	2026-01-06 16:54:59.212103	2026-01-06 17:14:04.765031	t	\N	\N	2026-01-06 15:54:59.215549	\N	f	t	7	60	f
43	6	\N	server	\N	8	\N	2026-01-12 18:00:00	2026-01-12 18:32:00	t	\N	\N	2026-01-12 17:00:57.550832	\N	f	f	\N	60	f
37	6	\N	server	\N	8	\N	2026-01-12 11:46:00	2026-01-12 17:06:15.807961	t	\N	\N	2026-01-12 10:46:20.409897	\N	t	f	\N	60	f
44	6	\N	server	\N	8	\N	2026-01-22 15:21:00	2026-01-28 13:56:46.185262	t	\N	\N	2026-01-22 14:21:33.783271	\N	t	f	\N	6	f
47	6	\N	server	\N	12	\N	2026-01-28 13:48:36.646997	2026-01-28 14:48:36.646997	t	\N	\N	2026-01-28 13:48:36.648553	\N	f	f	\N	60	f
45	6	\N	server	\N	10	\N	2026-01-28 13:19:00	2027-01-28 15:50:00	t	\N	\N	2026-01-28 13:19:07.315386	\N	t	f	\N	60	f
46	6	\N	server	\N	11	\N	2026-01-28 13:35:00	2026-01-29 08:01:00	t	\N	\N	2026-01-28 13:35:33.288726	\N	f	f	\N	6	f
39	6	\N	server	\N	9	\N	2026-01-12 15:31:13.334825	2026-01-30 10:09:29.668036	t	\N	\N	2026-01-12 14:31:13.335468	\N	f	f	\N	60	f
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
26	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	No valid grant for 100.64.0.20	2026-01-04 10:56:34.152986
27	\N	rdp_access_denied	rdp_server	\N	100.64.0.39	f	No valid grant for 100.64.0.39	2026-01-04 11:02:47.942108
28	\N	rdp_access_denied	rdp_server	\N	100.64.0.39	f	No valid grant for 100.64.0.39	2026-01-04 11:38:28.235753
29	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 11:55:11.077444
30	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 11:55:15.864489
31	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 11:59:11.198401
32	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 11:59:22.200139
33	\N	rdp_access_denied	rdp_server	\N	100.64.0.20	f	Access denied: No matching access policy	2026-01-04 12:01:10.405665
34	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:01:46.330632
35	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:01:50.930145
36	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:59:06.03278
37	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 12:59:09.882358
38	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:13:21.449365
39	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:13:24.330431
40	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 13:16:18.822064
41	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:27:44.617036
42	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:27:48.408396
43	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:55:24.802918
44	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:55:28.922297
45	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:58:36.757779
46	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 14:58:39.976502
47	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:00:11.994079
48	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:00:19.295367
49	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:02:22.83807
50	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:02:29.72653
51	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:04:50.05205
52	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:04:53.513486
53	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:03.118953
54	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:07.698214
55	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:19.878931
56	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:06:22.991033
57	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:18:31.795677
58	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 15:18:36.954757
59	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 16:19:24.330016
60	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-04 16:20:11.562535
61	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-05 10:24:06.227923
62	6	rdp_access_granted	rdp_server	2	100.64.0.39	t	User p.mojski connected to 10.30.0.140 via 10.0.160.130	2026-01-05 10:24:09.820938
\.


--
-- Data for Name: gates; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.gates (id, name, hostname, api_token, location, description, status, last_heartbeat, version, is_active, created_at, updated_at, ip_pool_start, ip_pool_end, ip_pool_network, in_maintenance, maintenance_scheduled_at, maintenance_reason, maintenance_grace_minutes, msg_welcome_banner, msg_no_backend, msg_no_person, msg_no_grant, msg_maintenance, msg_time_window, mfa_enabled) FROM stdin;
4	tailscale-ideo	10.30.0.76	aabbccddideo	\N	Tailscale Ideo Exit Node	online	2026-02-18 13:19:11.693434	1.9.0	t	2026-01-28 14:09:16.474771	2026-02-18 13:19:11.693434	10.0.160.129	10.0.160.254	10.0.160.128/25	f	\N	\N	15	\N	\N	\N	\N	\N	\N	t
1	gate-localhost	localhost	localhost-default-token-changeme			online	2026-02-18 13:19:31.885532	1.9.0	t	2026-01-07 09:07:27.987596	2026-02-18 13:19:31.885532	10.0.160.129	10.0.160.254	10.0.160.128/25	f	\N	\N	15	\N	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nThe IP address is not registered as a backend server in Inside registry.\nPlease contact your system administrator for assistance.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nI can't recognize you and I don't know who you are.\nPlease contact your system administrator for assistance.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nDear {person}, you don't have access to {backend}.\nPlease contact your system administrator to request access.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nThe system is currently in maintenance mode.\nPlease try again later or contact your system administrator.	Hello, I'm Gate (gate-localhost), an entry point of Inside.\nDear {person}, your access to {backend} is outside the allowed time window.\nPlease contact your system administrator for assistance.	f
3	tailscale-etop	10.210.0.76	aabbccddetop	Tailscale Exit Node (etop)	TPROXY-enabled gate for Tailscale exit node deployment	online	2026-02-18 13:19:20.593274	1.9.0	t	2026-01-11 20:51:11.757995	2026-02-18 13:19:20.593274	10.210.200.129	10.210.200.254	10.210.200.128/25	f	\N	\N	15	\N	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nThe IP address is not registered as a backend server in Inside registry.\r\nPlease contact your system administrator for assistance.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nI can't recognize you and I don't know who you are.\r\nPlease contact your system administrator for assistance.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nDear {person}, you don't have access to {backend}.\r\nPlease contact your system administrator to request access.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nThe system is currently in maintenance mode.\r\nPlease try again later or contact your system administrator.	Hello, I'm Gate (tailscale-etop), an entry point of Inside.\r\nDear {person}, your access to {backend} is outside the allowed time window.\r\nPlease contact your system administrator for assistance.	t
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
1	Ut3xYCznDk4QV3oGq0kdbvwYzvZ7zKz9eqgAlxOSJnE	3	6	44	p.mojski	2026-01-27 13:48:34.294412	2026-01-27 13:53:34.29439	f	\N	\N	\N	\N
2	8MhjSQQoIDUqyJZhgrCHHzHbIuxl1wvVfWo-cBBExDc	3	6	44	p.mojski	2026-01-27 13:53:39.809728	2026-01-27 13:58:39.809693	f	\N	\N	\N	\N
3	338JZIhAQVFLR0CVeIDtLjFmas9UwYUgxI2MPNioLwI	3	6	44	p.mojski	2026-01-27 13:56:04.102071	2026-01-27 14:01:04.10205	f	\N	\N	\N	\N
4	mcRrgsLCm2-gj_XcZaNMgkPb7iWmhjQpcgErGlmWsfA	3	6	44	p.mojski	2026-01-27 13:59:49.368305	2026-01-27 14:04:49.368287	f	\N	\N	\N	\N
5	OiO-x5qGAe5ajRHNGsiQBxbSFTjiOFBMHc_7QmXK1N8	3	6	44	p.mojski	2026-01-27 14:02:12.852027	2026-01-27 14:07:12.851997	f	\N	\N	\N	\N
6	2TuGL53RkMFptbscSt4nCwqrGY2Raj71i5-3QNmpaQk	3	6	44	p.mojski	2026-01-27 14:02:39.834263	2026-01-27 14:07:39.834238	f	\N	\N	\N	\N
7	ib7pU3p5AD1XSw-lL8kC_pjzhcM95USw8J5pNni1_yo	3	6	44	p.mojski	2026-01-27 14:09:14.078455	2026-01-27 14:14:14.07842	f	\N	\N	\N	\N
8	ejeOt-C4x3bGpvSGov6Co9zZCH7QMt_UBaKtRR1pJLg	3	6	44	p.mojski	2026-01-27 14:09:18.504308	2026-01-27 14:14:18.504271	f	\N	\N	\N	\N
9	W-qP3J-oYDcchIuVL5N8GOZTx31PaMZ0lPjXE6Ek7C0	3	6	44	p.mojski	2026-01-27 14:11:05.856092	2026-01-27 14:16:05.856069	f	\N	\N	\N	\N
10	vYrUAipEbhvKfTGmfVVAyMlNS7t-GG3TquEPLyxupIg	3	6	44	p.mojski	2026-01-27 14:12:43.99275	2026-01-27 14:17:43.992722	f	\N	\N	\N	\N
11	FGXHPnGWG3h2jGnuH9b90KF9NICd-MT_9DByp7UMlQk	3	6	44	p.mojski	2026-01-27 14:14:13.404117	2026-01-27 14:19:13.404078	f	\N	\N	\N	\N
12	L9-cE79TvORsFG9eoODUlQx6SJGL-rlfKmsW-UjSfwc	3	6	44	p.mojski	2026-01-27 14:15:50.895561	2026-01-27 14:20:50.895524	f	\N	\N	\N	\N
13	oZLyjQUBiyrX2QA2xYgEJidKLKDsJgBKb_-4S2N9XVU	3	6	44	p.mojski	2026-01-27 14:18:44.949093	2026-01-27 14:23:44.949069	f	\N	\N	\N	\N
14	XPNHFCx8i2c-N25brZ0qpYfi6pQtFkbtrcYtNn_nVpk	3	6	44	p.mojski	2026-01-27 14:27:15.105416	2026-01-27 14:32:15.105393	f	\N	\N	\N	\N
15	5WsHCc67wuNrYMIT27wz6Ohicl20DOJyhzEribZvMRM	3	6	44	p.mojski	2026-01-27 14:28:38.304822	2026-01-27 14:33:38.30479	f	\N	\N	\N	\N
16	qZvPzQpZ4g33rotGbHDQ_p4efUTUY82z63Prp3YMZLU	3	6	44	p.mojski	2026-01-27 14:29:15.517412	2026-01-27 14:34:15.517384	f	\N	\N	\N	\N
17	qgoSovq5c3XknPuaHL6VYRhTuRJ1SVD_la-_pXk-YdY	3	6	44	p.mojski	2026-01-27 15:07:00.520957	2026-01-27 15:12:00.520932	f	\N	\N	\N	\N
18	dkixVJC2C2i7dYC0tsIU1c2lyAksrzcTZp67xP_TQTM	3	6	44	p.mojski	2026-01-27 15:13:47.942918	2026-01-27 15:18:47.942893	t	2026-01-27 15:17:32.923082	p.mojski@ideosoftware.com	\N	\N
19	1wT-416GTtnnywuCH6TBfmSAydG5Nw1zmcLfoDB6q5I	3	6	44	p.mojski	2026-01-27 15:21:59.916745	2026-01-27 15:26:59.916682	t	2026-01-27 15:22:07.728242	p.mojski@ideosoftware.com	\N	\N
20	qk5WGlkz01beFMtk4CGR0bNBVNDSaLuQKfY39sv2wLA	3	6	44	p.mojski	2026-01-27 15:22:21.03641	2026-01-27 15:27:21.036385	t	2026-01-27 15:22:27.647094	p.mojski@ideosoftware.com	\N	\N
21	FAIpISw4hQ9nk5If389F7AxxhbteuY-Dao-slSUAKW4	3	6	44	p.mojski	2026-01-27 15:24:15.704493	2026-01-27 15:29:15.704456	t	2026-01-27 15:24:24.424008	p.mojski@ideosoftware.com	\N	\N
22	EyXdkvglDQuE-fqhOD-XI8tS8EvAwUks6sdFpXXo-Bo	3	6	44	p.mojski	2026-01-27 15:24:34.675065	2026-01-27 15:29:34.675024	f	\N	\N	\N	\N
23	xtrXPl7uqbjxZZ94SDX_9tO2ZuqU5D3sG3hdbCzKQmk	3	6	44	p.mojski	2026-01-27 15:27:25.971108	2026-01-27 15:32:25.971087	t	2026-01-27 15:27:33.085574	p.mojski@ideosoftware.com	\N	\N
24	Bt0FbXZkS_G3q0ZoYRucuixWJDWarZcpYPSahCPHVVM	3	6	44	p.mojski	2026-01-27 15:29:26.680075	2026-01-27 15:34:26.680057	f	\N	\N	\N	\N
25	a9sT2JR0qNsa3zCaF2Jg_wVh2CNWv8UYHxp4WCTk6vU	3	6	44	p.mojski	2026-01-27 15:29:50.940935	2026-01-27 15:34:50.940919	f	\N	\N	\N	\N
27	ODbFpe2BD28r4WhCuRNNRfGJkOTis2vYtx0TeHY6MyY	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:36:04.92672	2026-01-27 16:41:04.926682	f	\N	\N	\N	\N
28	5FWaGgx-VbI2UIua3dhTT8XKZr3HuppDb4tQbBmLOX4	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:37:14.363133	2026-01-27 16:42:14.363106	f	\N	\N	\N	\N
29	H_1zEau51utYK446DDQRJOs9ic_EbX1XKatPyzb7ioA	3	\N	\N	p.mojski@10.210.1.190	2026-01-27 16:37:37.005227	2026-01-27 16:42:37.005178	f	\N	\N	\N	\N
30	M-vgBIAFjS_CZgpzV3D6gnQ3NcoceNrPb58AQILMvBM	3	6	\N	p.mojski	2026-01-27 16:40:57.734573	2026-01-27 16:45:57.734554	t	2026-01-27 16:41:03.340906	p.mojski@ideosoftware.com	10.210.1.190	\N
31	waq8RVWpxqrVK39yQu2Nf4rFfllwfstgjQomnBNIK5o	3	6	\N	p.mojski	2026-01-27 16:42:35.329333	2026-01-27 16:47:35.329302	t	2026-01-27 16:42:42.481268	p.mojski@ideosoftware.com	10.210.1.190	\N
32	v9TDAQL__kfeSFvxDAvNQHCNIIiN9xKg98rvKvrcYsg	3	6	\N	p.mojski	2026-01-27 16:45:01.759313	2026-01-27 16:50:01.759282	t	2026-01-27 16:45:06.713482	p.mojski@ideosoftware.com	10.210.1.190	\N
33	ewXltrOoKJakZjyhxZQDuGmjKgpY0YdP4vj8_VD1XZs	3	6	\N	p.mojski	2026-01-27 16:46:43.622661	2026-01-27 16:51:43.622631	t	2026-01-27 16:46:49.46372	p.mojski@ideosoftware.com	10.210.1.190	\N
34	g41qTbz_eQCRVBcUS23goJsR5YHnT15yIaL3pfKKDS8	3	6	\N	p.mojski	2026-01-27 16:52:02.622297	2026-01-27 16:57:02.622279	t	2026-01-27 16:52:07.895181	p.mojski@ideosoftware.com	10.210.1.190	\N
35	--ZQls9ag5GAOXMDz8MuNuIJY69s5In7ziFIaLTlfNQ	3	6	\N	p.mojski	2026-01-27 16:53:18.269288	2026-01-27 16:58:18.269265	t	2026-01-27 16:53:23.584637	p.mojski@ideosoftware.com	10.210.1.190	\N
36	CTshosMLUYsGk9Ul5v9lmbg6sMvDH4s4STNJRR_bObc	3	6	\N	p.mojski	2026-01-27 16:54:51.476	2026-01-27 16:59:51.47598	t	2026-01-27 16:54:56.719668	p.mojski@ideosoftware.com	10.210.1.190	\N
37	edthvcrQcJI7X_-P0Ul_dvJ6B2HFII5dx5V4sXcIOAo	3	6	\N	p.mojski	2026-01-27 16:55:39.772683	2026-01-27 17:00:39.772654	t	2026-01-27 16:55:45.09884	p.mojski@ideosoftware.com	10.210.1.190	\N
38	3ZnXrc_AlzVXhhjBSBDum-OetUIVQQODjBEgNQrA3iU	3	6	\N	p.mojski	2026-01-27 16:57:27.036361	2026-01-27 17:02:27.036343	t	2026-01-27 16:57:34.448895	p.mojski@ideosoftware.com	10.210.1.190	\N
39	6L5OOSOUAJ17fZ2IBidqB8Lj0CXh7HdR5cPYe5UOIsQ	3	6	\N	p.mojski	2026-01-27 16:58:39.413667	2026-01-27 17:03:39.413646	t	2026-01-27 16:58:44.901915	p.mojski@ideosoftware.com	10.210.1.190	\N
40	mdIjE4vM1wSnpDeYiviu3jpZM3HWYrtEetOcDrs1OqY	3	\N	\N	p.mojski	2026-01-27 17:00:04.266291	2026-01-27 17:05:04.26627	f	\N	\N	10.210.1.189	\N
41	e6Zea-3DtGpelXbrMQmeXQ-wKREoK2_3VomRHxN3DHE	3	6	\N	p.mojski	2026-01-27 17:00:23.961462	2026-01-27 17:05:23.961416	t	2026-01-27 17:00:29.844521	p.mojski@ideosoftware.com	10.210.1.190	\N
42	QPfKYjSgFxWeY5Zo7QVHteCqNTedg90bTgUqfs5udpU	3	6	\N	p.mojski	2026-01-27 17:02:57.693035	2026-01-27 17:07:57.693011	t	2026-01-27 17:03:16.051753	p.mojski@ideosoftware.com	10.210.1.189	\N
43	_5nzpoKJzv2TLh8dRPK8Sd_2G_jRnC-p3nkihT8pMEM	3	\N	\N	p.mojski	2026-01-27 17:05:15.822755	2026-01-27 17:10:15.822738	f	\N	\N	10.210.1.189	\N
44	aCqxZKaS7g8CGpYY1rxrLbO0UzGjKpnlZ58mT3oOggw	3	\N	\N	p.mojski	2026-01-28 07:25:50.300925	2026-01-28 07:30:50.300897	f	\N	\N	10.210.1.189	\N
45	3yl-B-djBzIgbvsZKrtV4ZOxx2-ornIp0x71gkJH2D0	3	\N	\N	p.mojski	2026-01-28 07:51:12.753323	2026-01-28 07:56:12.753299	f	\N	\N	10.210.1.189	\N
46	kdjVe4c2j5fJg8RPswp5x_YwSq0J3gsOVa9VzSZHznM	3	\N	\N	p.mojski	2026-01-28 07:51:17.559852	2026-01-28 07:56:17.55983	f	\N	\N	10.210.1.189	\N
47	MlBX6KTROOVKGJxr-J_Z2dAQbfvFceyIAmU_aEQiB80	3	\N	\N	p.mojski	2026-01-28 07:53:20.805813	2026-01-28 07:58:20.805793	f	\N	\N	10.210.1.189	\N
48	-Zy08aQYXRzL3ar6c76qIvsvLVrRYQe8exXou6wEdIQ	3	\N	\N	p.mojski	2026-01-28 07:54:53.658248	2026-01-28 07:59:53.658225	f	\N	\N	10.210.1.189	\N
49	BvIO4FOWBCwmjSEUc4gXCC1D3oG_tJTKKbOEKG4aw7Q	3	\N	\N	p.mojski	2026-01-28 07:55:25.292666	2026-01-28 08:00:25.292651	f	\N	\N	10.210.1.189	\N
50	unHsW0NJkMBekx-sV6RG_ggcbTOt4L3RZFg8EK22hms	3	\N	\N	p.mojski	2026-01-28 07:55:29.590353	2026-01-28 08:00:29.59033	f	\N	\N	10.210.1.189	\N
51	TzP-hZjryctg8AM9AJiy0WjzEA8C_Ouf3-p-UmzCms4	3	\N	\N	p.mojski	2026-01-28 08:08:02.948947	2026-01-28 08:13:02.94892	f	\N	\N	10.210.1.189	\N
52	4gF61LN1zF9SGtIZpPf-xkFFhrNczQPYDSZvFzxXoMw	3	6	\N	p.mojski	2026-01-28 08:10:37.634786	2026-01-28 08:15:37.634772	t	2026-01-28 08:10:47.890737	p.mojski@ideosoftware.com	10.210.1.189	\N
53	vJ66rGRjJ_nRbKz3yxlPiE0ly5dP3TxJvOuM7WZGjuo	3	6	\N	p.mojski	2026-01-28 08:12:00.021136	2026-01-28 08:17:00.021118	t	2026-01-28 08:12:14.05833	p.mojski@ideosoftware.com	10.210.1.189	\N
54	yGSbHsCQI4wMtLWs1ypLcFepsxo7zkqFivqBSsw7B6k	3	\N	\N	p.mojski	2026-01-28 08:16:52.652678	2026-01-28 08:21:52.652657	f	\N	\N	10.210.1.189	\N
55	nPnlfPN3G4xx_cr2on0z4FKxa-ex6rFp_Sor26a2Ieg	3	6	\N	p.mojski	2026-01-28 08:16:59.20621	2026-01-28 08:21:59.206195	t	2026-01-28 08:17:07.802698	p.mojski@ideosoftware.com	10.210.1.189	\N
56	RE23wXa_U_GACFEh4DntW948WDZ9Hr0i_wxgkmxZNl4	3	6	\N	p.mojski	2026-01-28 08:18:55.997295	2026-01-28 08:23:55.99727	t	2026-01-28 08:19:01.788082	p.mojski@ideosoftware.com	10.210.1.189	\N
57	dLa3sTmThaAkHGHJyL9dl9CzUenlNZVGlH2cO-x1CkY	3	6	\N	p.mojski	2026-01-28 08:33:18.823173	2026-01-28 08:38:18.823136	t	2026-01-28 08:33:26.895495	p.mojski@ideosoftware.com	10.210.1.189	\N
58	pI8dM_O-34xvMeOxgcRMDDK7yjRot8v3iQCueLukJoc	3	\N	\N	p.mojski	2026-01-28 08:44:18.844461	2026-01-28 08:49:18.844444	f	\N	\N	10.210.1.189	\N
59	x1Y3NZm4nY3o6PoKaTCmV_HIH459TztEnJIJ3HCywIo	3	6	\N	p.mojski	2026-01-28 08:44:23.875481	2026-01-28 08:49:23.875461	t	2026-01-28 08:44:32.63501	p.mojski@ideosoftware.com	10.210.1.189	\N
60	pj2_2SoC7Xu9k1pM-A1pVfcogfaoD0VGG6dBR1toxTM	3	6	\N	p.mojski	2026-01-28 08:44:36.347941	2026-01-28 08:49:36.347914	t	2026-01-28 08:44:42.647551	p.mojski@ideosoftware.com	10.210.1.189	\N
61	zAuJjVFN1kSqLLxwxx_XUiFodXyoPgl-YyQFa3QaCgc	3	6	\N	ideo	2026-01-28 08:44:53.084274	2026-01-28 08:49:53.084251	t	2026-01-28 08:47:43.092336	p.mojski@ideosoftware.com	10.210.1.190	\N
62	MFcORljEwBwF_N_tNsR8BKbAZ2m3vYOoGTpiKDMs_jY	3	\N	\N	p.mojski	2026-01-28 08:53:34.370232	2026-01-28 08:58:34.370185	f	\N	\N	10.210.1.189	\N
63	4W1RQYGq3rnBsREUP4R7UoVekq6G-YPqYM4NsdQ-_OM	3	\N	\N	p.mojski	2026-01-28 08:53:56.894956	2026-01-28 08:58:56.894928	f	\N	\N	10.210.1.189	\N
64	gPeESmQhG3U4sszn_HFSQ95h11CYBC8TZRx1HSq-5hc	3	\N	\N	p.mojski	2026-01-28 08:55:15.184369	2026-01-28 09:00:15.18433	f	\N	\N	10.210.1.189	\N
66	PPvF3Cg2cQEc_VOfsq1No4TjcGrAColMqOnLVtpqI6o	3	\N	\N	p.mojski	2026-01-28 09:11:15.932595	2026-01-28 09:16:15.932573	f	\N	\N	10.210.1.189	\N
67	WJVvo4ojdlLPdYyJhwhfjem202dX7wzwS4kbpMx00CE	3	\N	\N	p.mojski	2026-01-28 09:14:29.708875	2026-01-28 09:19:29.708849	f	\N	\N	10.210.1.189	\N
68	62CzcK7t1-Xj5Qyp8u8C3-puB8AQf-PccoGp1Ocu-0M	3	6	\N	p.mojski	2026-01-28 09:20:02.014564	2026-01-28 09:25:02.014544	t	2026-01-28 09:20:11.105972	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
70	j4Fh_S2_8PrMSjEuAB54v9WinidaI8ro489sATVDnR4	3	6	\N	p.mojski	2026-01-28 09:20:48.735908	2026-01-28 09:25:48.735865	t	2026-01-28 09:21:00.469381	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
72	pRs10k9vjgDDJ7VBqGsiazrZuTpFdNdJ9TFUEab_ffs	3	6	\N	p.mojski	2026-01-28 09:23:56.466231	2026-01-28 09:28:56.466213	t	2026-01-28 09:24:09.575509	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
73	J9JsxW7Xtvaqq-jaAa4yprWyEYS1JxpS4yygs0cNy1A	3	6	\N	p.mojski	2026-01-28 09:24:31.880304	2026-01-28 09:29:31.880283	t	2026-01-28 09:24:40.974397	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
74	XUxKtSX52h8y5eyLMyI9mkJuZGUYecH_z4Qgh2qeNRo	3	\N	\N	p.mojski	2026-01-28 09:35:33.843878	2026-01-28 09:40:33.843849	f	\N	\N	10.210.1.189	100.64.0.20
75	VLOQmXDiVwkb7TNxady7Erj9WZrmlam8ptxNvSlQ8VM	3	6	\N	p.mojski	2026-01-28 09:35:40.068554	2026-01-28 09:40:40.06853	t	2026-01-28 09:35:44.50314	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
76	acNrQvB51v6R99DcuQDcdEQLjnaEtsaCng88fP57jho	3	6	\N	p.mojski	2026-01-28 09:38:09.226424	2026-01-28 09:43:09.226383	t	2026-01-28 09:38:14.993323	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
77	0j08_fKY_OuSfOY6YVjaK7-JJmUUyXsBp60wwK3UBQw	3	6	\N	p.mojski	2026-01-28 09:38:54.519106	2026-01-28 09:43:54.519087	t	2026-01-28 09:38:59.343037	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
78	2EY-GyfTT-XO3yHPmANKpUScldvk8toh2mVg_i8XrKg	3	6	\N	p.mojski	2026-01-28 09:41:41.607724	2026-01-28 09:46:41.607695	t	2026-01-28 09:41:47.621306	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
79	klLzcEa5dFZJGp0b-r0-WKTAMnCwD6PCQnDXeFIWe8Y	3	\N	\N	p.mojski	2026-01-28 09:41:55.576909	2026-01-28 09:46:55.576885	f	\N	\N	10.210.1.189	100.64.0.20
80	lZeZ8zHxswvLXHF6V84sZoV2gG0PNRN0qoOruKWbOy0	3	6	\N	p.mojski	2026-01-28 09:44:03.03057	2026-01-28 09:49:03.030552	t	2026-01-28 09:44:17.110812	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
81	-LX-9McgLKEVJkg0tHBJPDHBrx7KjkCoaCnHqfIwpA4	3	6	\N	p.mojski	2026-01-28 09:46:26.816528	2026-01-28 09:51:26.816492	t	2026-01-28 09:46:33.921849	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
82	_6Z2w_LeQCI04fuzEFZwofEg6ZecKkJQK-CYVPA-4mo	3	6	\N	p.mojski	2026-01-28 09:59:01.032014	2026-01-28 10:04:01.031985	t	2026-01-28 09:59:08.364804	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
83	xhWWQ7XeGs1uAHWZE8C_hmRfOnWbI2R08wjBYIMNWqE	3	6	\N	p.mojski	2026-01-28 10:03:03.171413	2026-01-28 10:08:03.171384	t	2026-01-28 10:03:08.573958	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
84	Wab27VGddJJ29v93HoHMK1uPy1yXSG2lauSaf6yl9sA	3	6	\N	p.mojski	2026-01-28 10:09:35.520887	2026-01-28 10:14:35.520861	t	2026-01-28 10:09:39.581946	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
85	382ZMEDMab5RFbg3f6yiG9nqXP7vOsTaVFGnTjW06_4	3	6	\N	p.mojski	2026-01-28 10:11:17.116294	2026-01-28 10:16:17.116271	t	2026-01-28 10:11:21.531735	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
86	gGLf4IEBWQcCRXHfoYP1pvyY9oMZ04BwT_UEdQ7zLlM	3	6	\N	p.mojski	2026-01-28 10:15:59.957668	2026-01-28 10:20:59.95764	t	2026-01-28 10:16:04.261005	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
87	tovDU5IkbdOCdf3FxhX-3WOu6sGcRQfFf-FiOiUHLsE	3	6	\N	p.mojski	2026-01-28 10:25:00.537652	2026-01-28 10:30:00.537632	t	2026-01-28 10:25:07.458805	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
88	sRR2_LSzjBaB1JIMLL0UuJr235v2AMN8AZ902cGfjzk	3	6	\N	p.mojski	2026-01-28 10:25:36.312642	2026-01-28 10:30:36.312623	t	2026-01-28 10:25:48.401083	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
89	BkOSUDDdTn5vmt_7CKfLRRvUnIA-0JjrD-hl82j5OSc	3	6	\N	p.mojski	2026-01-28 10:26:02.366986	2026-01-28 10:31:02.366948	t	2026-01-28 10:26:08.283574	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
90	KB1cJtBvgFUjr5ixisiQjdaM5z9AGKPc0hqLyDGVHe8	3	6	\N	p.mojski	2026-01-28 10:40:17.540708	2026-01-28 10:45:17.540681	t	2026-01-28 10:40:31.341335	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
91	_VDyJLAkyRYIr_Mki5WcCCuKfJaaXl-AnBgniZPftS0	3	6	\N	p.mojski	2026-01-28 10:46:14.814807	2026-01-28 10:51:14.814776	t	2026-01-28 10:46:20.895691	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
92	Sp253yBkjYO6Wy-ldaUdtwphkwv8_dIDemG0sMpN6G0	3	6	\N	p.mojski	2026-01-28 10:48:38.877771	2026-01-28 10:53:38.877717	t	2026-01-28 10:48:42.807004	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
93	G5v-za_EM01RCF81Ygy2j1A14hngbmRT9fwzJ8MqpBg	3	6	\N	p.mojski	2026-01-28 10:50:48.677798	2026-01-28 10:55:48.677769	t	2026-01-28 10:50:52.58994	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
94	viHFjkRJliTNq6aIzeoogSNz-pdfjUv0jzi1Nly88M0	3	6	\N	p.mojski	2026-01-28 10:52:10.601174	2026-01-28 10:57:10.601151	t	2026-01-28 10:52:16.08584	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
95	ES5Im6asbcDo-pRRxJ57w9sSicIs1Mus_hHwhsQ4Q-I	3	6	\N	p.mojski	2026-01-28 10:55:16.633108	2026-01-28 11:00:16.633077	t	2026-01-28 10:55:21.791566	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
96	LEjjYtmLwluM7LsdY306QbIwHUt4hJj2w4hwna7cYys	3	6	\N	p.mojski	2026-01-28 10:57:37.552958	2026-01-28 11:02:37.552931	t	2026-01-28 10:57:41.845997	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
98	r4jJ9t5ycMkasN-PRLuNHnJCl-z1VnplQGaZyIggfiw	3	6	\N	p.mojski	2026-01-28 11:07:45.053803	2026-01-28 11:12:45.053765	t	2026-01-28 11:07:51.949536	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
102	Q0PSMPUxFh-WhjuWaj6rZE3cRPM3W3AWVq1bLf95Ujk	3	6	\N	p.mojski	2026-01-28 11:24:59.883428	2026-01-28 11:29:59.883402	t	2026-01-28 11:25:05.19566	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
103	EDgSQWIZc3I8kRTmaVnvdJcd-YgVyOSD9Shf_pJP_4s	3	6	\N	p.mojski	2026-01-28 11:25:36.991606	2026-01-28 11:30:36.991582	t	2026-01-28 11:25:41.497806	p.mojski@ideosoftware.com	10.210.1.190	100.64.0.20
104	LV0uTa7o6YfbeoLM0TPXhkskVWAT70keiYMxWoNjNKo	3	\N	\N	p.mojski	2026-01-28 11:29:52.25887	2026-01-28 11:34:52.258851	f	\N	\N	10.210.1.190	100.64.0.20
105	kCGs0LZghjk469yHVtMfMNZpzefDIJE8dfmwg6sD9l8	3	\N	\N	p.mojski	2026-01-28 11:34:49.619049	2026-01-28 11:39:49.619023	f	\N	\N	10.210.1.189	100.64.0.20
114	73vYl9Gu5H_eSRRyQ9r1qKobFs3Oq0TOF68iLH20Z-I	4	6	\N	root	2026-01-28 13:16:52.624389	2026-01-28 13:21:52.62436	t	2026-01-28 13:17:34.431094	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
106	o8sTbmlip1PKYuTp5B57PQQXQphadiVDgmo9m4pGnx0	3	6	\N	p.mojski	2026-01-28 11:34:54.518011	2026-01-28 11:39:54.517986	t	2026-01-28 11:35:04.310519	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
107	UZ1HA6i2aCbfjT3nZse1sW4hktVsjd-MPRZj-DgWPrI	3	6	\N	p.mojski	2026-01-28 11:36:44.147576	2026-01-28 11:41:44.147554	t	2026-01-28 11:36:49.376251	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
116	cG0dcp9X3ZlNcJs1Pmimi-9YLBT8h9Bsu_93O0S-q1M	4	6	\N	p.mojski	2026-01-28 13:19:21.794335	2026-01-28 13:24:21.794319	t	2026-01-28 13:19:28.023797	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
109	jbQgOwD5lY67r9ShUS4hKhDptGtchPwVaue9qJYO5Dw	3	6	\N	p.mojski	2026-01-28 12:51:32.036545	2026-01-28 12:56:32.036524	t	2026-01-28 12:51:50.858668	p.mojski@ideosoftware.com	10.210.1.190	100.64.0.20
110	gxjbYpeMZmnI9hI5VV_AboDO41DE3rIgmDuwN_oSWvs	3	6	\N	p.mojski	2026-01-28 12:56:23.522998	2026-01-28 13:01:23.522975	t	2026-01-28 12:56:32.975616	p.mojski@ideosoftware.com	10.210.1.190	100.64.0.20
117	8zUGtS-xosiv0qTbHvI2WvOZv-nMQ3ghxfgoLVFxW4Y	4	6	\N	p.mojski	2026-01-28 13:19:43.957782	2026-01-28 13:24:43.957749	t	2026-01-28 13:19:53.233613	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
111	e-5VshdQwL8TnmwSsDEH4EzplPfjXHDgU6j3dVPh9eg	3	6	\N	p.mojski	2026-01-28 12:56:57.301029	2026-01-28 13:01:57.300958	t	2026-01-28 12:57:02.858568	p.mojski@ideosoftware.com	10.210.1.190	100.64.0.20
112	Q02gAv1p3zA2CKk5y1q4u2495Sr95MmwIetxUH47Tzk	3	6	\N	p.mojski	2026-01-28 12:57:26.548792	2026-01-28 13:02:26.54877	t	2026-01-28 12:57:31.636715	p.mojski@ideosoftware.com	10.210.1.190	100.64.0.20
118	eV5wyTdLwAzhvvwALrEbjIjlK7e0fgNAYh76cZLQPX0	4	6	\N	p.mojski	2026-01-28 13:27:47.026864	2026-01-28 13:32:47.02684	t	2026-01-28 13:27:58.731388	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
119	5tIxUt6v6MwAILNlQEKXV4p6XJl5Iy9bDj9fn9qd9fo	4	6	\N	p.mojski	2026-01-28 13:29:46.609183	2026-01-28 13:34:46.609154	t	2026-01-28 13:29:53.088158	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
120	2ZhOg9xW5ZPj-haIMQhptJbkBOZSMABnmvu4ycL2QYI	4	6	\N	p.mojski	2026-01-28 13:30:18.524699	2026-01-28 13:35:18.524678	t	2026-01-28 13:30:24.716533	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
121	4Jb2j8z9dGoWTvOBecQoqqBh6vM1FgLCBMzzAoNz9pU	4	6	\N	pmojski	2026-01-28 13:31:42.526236	2026-01-28 13:36:42.526211	t	2026-01-28 13:31:45.425816	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
122	ZJNDxjePB81w8R2jNWRESurjBDDdkgnYIalCllkt5J4	4	6	\N	pmojski	2026-01-28 13:32:37.124801	2026-01-28 13:37:37.124778	t	2026-01-28 13:32:41.765946	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
123	et4HuME0whNp3fYHCOhHPL9c1jEx7JNmKrEYAEy1wqQ	4	6	\N	pmojski	2026-01-28 13:52:30.990036	2026-01-28 13:57:30.990009	t	2026-01-28 13:52:40.379661	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
124	2yEdFG4bqfTr1YB5Eaf9g6-WMJHkeq60vNRBcw5x3qY	4	6	45	pmojski	2026-01-28 13:55:04.261715	2026-01-28 14:00:04.261685	t	2026-01-28 13:55:31.244174	p.mojski@ideosoftware.com	\N	\N
125	VHnJJuxZDJnZIEE1p7WA_AXWSDRABGd1p8ocA915CZ0	4	6	\N	pmojski	2026-01-28 14:11:00.580485	2026-01-28 14:16:00.580459	t	2026-01-28 14:11:09.436734	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
126	X_jJctGGc9IT52OA_WeP1Lq9jxrhMzXbkRdXyeuBoBw	4	6	\N	pmojski	2026-01-28 14:49:31.584681	2026-01-28 14:54:31.584649	t	2026-01-28 14:49:50.107499	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
127	UdD4gTFsGXi3t6pbetgZaQK7-8duh2uHWhBGT9eD2xA	4	6	\N	pmojski	2026-01-28 14:50:47.102878	2026-01-28 14:55:47.102858	t	2026-01-28 14:50:55.267624	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
128	FnJb-tRksVRIU0SktDpMsHv4yCPUnuSXrb2U7zzY87o	4	6	\N	pmojski	2026-01-28 14:51:18.388083	2026-01-28 14:56:18.388052	t	2026-01-28 14:51:24.797675	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
129	1T3xhWbCONFdDCmtfmWXti9SE1zP6fh9LCUKc36G0FA	4	\N	\N	pmojski	2026-01-28 15:21:33.288429	2026-01-28 15:26:33.288393	f	\N	\N	10.30.14.3	100.64.0.20
130	SbcFKsfRcdmFv6S6dLU66_f-5M48aASqDiKEIZW7SdI	4	6	\N	pmojski	2026-01-28 15:21:48.453224	2026-01-28 15:26:48.453196	t	2026-01-28 15:22:09.650303	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
131	vLOMDmY-8ORaLLuwBf3UcEetHZp8FgNVzzj42X0PFPU	4	6	\N	pmojski	2026-01-28 15:24:18.260027	2026-01-28 15:29:18.259993	t	2026-01-28 15:24:21.985812	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
132	htwZ1KpWXwF6NV59VKhjzCoCNLnHg3XiuriVuRqfau0	4	6	\N	cisco	2026-01-29 07:00:41.765235	2026-01-29 07:05:41.765213	t	2026-01-29 07:01:03.94389	p.mojski@ideosoftware.com	10.30.10.29	100.64.0.20
133	UhE27-7MWdAYayvh4z3gSwGSxxYIXZDzGv8EXMqgfes	4	6	\N	cisco	2026-01-29 07:01:29.350408	2026-01-29 07:06:29.350392	t	2026-01-29 07:01:36.771136	p.mojski@ideosoftware.com	10.30.10.29	100.64.0.20
134	frHUQd96fFFrRJg8Pdyu0f7qmVOgz0709Urn2CiZqgs	4	6	\N	cisco	2026-01-29 07:01:53.794758	2026-01-29 07:06:53.794741	t	2026-01-29 07:02:00.773314	p.mojski@ideosoftware.com	10.30.10.29	100.64.0.20
135	dfTrufRQ6LHtlbWhQmZYHayQ6yRqJkLRtl_AUtjjrr8	4	6	\N	cisco	2026-01-29 07:03:17.202507	2026-01-29 07:08:17.202479	t	2026-01-29 07:03:22.964678	p.mojski@ideosoftware.com	10.30.10.29	100.64.0.20
136	pryJBvcVl4wFQ-CREiLqZlu5ijZmaX_tbCVfIgz6TAc	3	6	\N	p.mojski	2026-01-30 08:34:38.437135	2026-01-30 08:39:38.437098	t	2026-01-30 08:34:42.574803	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.39
137	Xiipcg-FgZdzzWMv9KBuT7P1-vNpAzYkA-rr3qBR67Q	3	6	\N	p.mojski	2026-01-30 09:09:10.804649	2026-01-30 09:14:10.804597	t	2026-01-30 09:09:35.570362	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
139	0-H6OBX1rMSN_6Y-9B1GoOm9APovxSCjuZzP3PKTMEI	3	6	\N	p.mojski	2026-01-30 09:09:55.700029	2026-01-30 09:14:55.700008	t	2026-01-30 09:09:59.524204	p.mojski@ideosoftware.com	10.210.1.189	100.64.0.20
140	rxHC6bp-6dm0SH3uxD5SpNnMU-4_l8yMzCDbYs40osQ	4	6	\N	pmojski	2026-02-18 12:33:58.359869	2026-02-18 12:38:58.359825	t	2026-02-18 12:34:09.754261	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
141	aggq2WpvhE7xr0Yrp64lCdRrStd4YQJOFCqHRJ-moLE	4	6	\N	pmojski	2026-02-18 12:34:42.354545	2026-02-18 12:39:42.35452	t	2026-02-18 12:34:49.763069	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
142	J1ThSowm_WTl3pezL1MR_RKnIc2oPPo3-zdcXZ5LrCk	4	\N	\N	pmojski	2026-02-18 12:35:32.617525	2026-02-18 12:40:32.617498	f	\N	\N	10.30.14.3	100.64.0.20
143	hES8YFHqdaN2vH4ywpLJXx5ZyrbbEP9K3yjiGpp6RGw	4	6	\N	pmojski	2026-02-18 12:37:09.210399	2026-02-18 12:42:09.210362	t	2026-02-18 12:37:20.099039	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
144	x-YrMvg2ZraL_FrOzTtv697wRI24ik6fiDczGtbDU-g	4	6	\N	pmojski	2026-02-18 12:40:15.500795	2026-02-18 12:45:15.500776	t	2026-02-18 12:40:24.742969	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
145	2QKAP5iXWv0PC484n7HiZ3b9LQkLMk5D-hXWMgI4q8c	4	6	\N	pmojski	2026-02-18 12:42:02.244845	2026-02-18 12:47:02.244818	t	2026-02-18 12:42:08.998447	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
146	JjcR9zM9QNs5cDVrwJvMq1OK19cPB4i2Sd_xilXQ81U	4	6	\N	pmojski	2026-02-18 12:44:08.719376	2026-02-18 12:49:08.719348	t	2026-02-18 12:44:12.934124	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
147	9sLpbFuqcEnqR0ISYXjEiaGe2EPL2G7tG-OjdmTEZzE	4	6	\N	pmojski	2026-02-18 12:46:46.991524	2026-02-18 12:51:46.991496	t	2026-02-18 12:46:52.078654	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
148	sIVCZb5WI76nBS_xdJ6eJ6FaFpzGYftVv8NEPm8iIkk	4	6	\N	pmojski	2026-02-18 12:49:57.934501	2026-02-18 12:54:57.934464	t	2026-02-18 12:50:02.19344	p.mojski@ideosoftware.com	10.30.14.3	100.64.0.20
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
1	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-06T17:28:44.625652", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": null, "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:44.625652", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-01-06T17:28:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-06 17:19:30.232265
2	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:26.474086", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-07 10:02:56.599385
3	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-07 10:03:20.013489
4	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": [], "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1], "is_active": true, "time_start": "00:00", "days_of_month": []}, {"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": null, "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "00:00", "days_of_month": null}, {"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-07 10:03:36.303964
10	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:33:13.199693
5	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 8, "name": "test 1", "months": null, "time_end": "17:59", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "00:00", "days_of_month": null}, {"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:10:46.111732
6	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [1, 2], "is_active": true, "time_start": "18:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": null, "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:11:01.603557
7	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": null, "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:13:54.702864
8	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:14:33.278444
9	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": [], "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": [6]}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 10:32:23.992411
19	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T18:05:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T18:06:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:05:10.539488
11	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "19:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "21:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 18:36:44.516654
12	30	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "21:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-05T17:46:00", "protocol": "ssh", "is_active": true, "schedules": [{"id": 11, "name": "test 2", "months": null, "time_end": "22:00", "timezone": "Europe/Warsaw", "weekdays": [0, 1, 2, 3, 4, 5, 6], "is_active": true, "time_start": "10:30", "days_of_month": null}], "scope_type": "service", "ssh_logins": ["p.mojski"], "start_time": "2026-01-06T16:28:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 1, "port_forwarding_allowed": true}	2026-01-11 19:55:22.7921
13	34	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-10T23:07:23.007881", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": ["p.mojski"], "start_time": "2026-01-11T22:06:09.396708", "source_ip_id": 5, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-10T23:07:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": ["p.mojski"], "start_time": "2026-01-11T22:06:00", "source_ip_id": 5, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	2026-01-12 07:15:46.965068
14	36	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T10:36:43.267365", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T10:35:43.267365", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-01-12T10:36:00", "protocol": null, "is_active": true, "schedules": [{"id": 12, "name": "13-14", "months": null, "time_end": "13:59", "timezone": "Europe/Warsaw", "weekdays": null, "is_active": true, "time_start": "13:00", "days_of_month": null}], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T10:35:00", "source_ip_id": 5, "use_schedules": true, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	2026-01-12 10:36:00.751743
15	37	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-02-11T16:02:28.266503", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": ["p.mojski"], "start_time": "2026-01-12T10:46:20.407825", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-02-11T16:02:28.266503", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": ["p.mojski"], "start_time": "2026-01-12T10:46:00", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	2026-01-12 16:02:53.49008
16	42	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T17:32:53.616260", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T16:32:53.616260", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T16:35:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T16:32:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 16:33:29.061706
17	42	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T17:35:58.784480", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T16:32:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T16:43:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T16:32:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 16:36:43.114045
18	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T18:00:57.546910", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:57.546910", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T18:05:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:01:30.613033
20	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T18:06:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T18:04:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:10:30.116876
21	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T18:04:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T17:17:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:11:38.470437
22	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T17:17:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T17:19:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:14:03.490895
23	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T19:22:43.342673", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T17:30:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:23:30.081488
24	43	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-12T17:30:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	{"user_id": 6, "end_time": "2026-01-12T17:32:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-12T17:00:00", "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": false}	2026-01-12 17:25:12.563805
25	44	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-27T13:59:44.537144", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:33.778463", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-01-27T13:59:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	2026-01-27 13:00:04.770451
26	44	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-27T13:59:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	{"user_id": 6, "end_time": "2026-01-27T13:59:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true}	2026-01-27 13:00:18.860572
27	44	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-27T13:59:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "mfa_required": false, "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 6}	{"user_id": 6, "end_time": "2026-01-27T13:59:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "mfa_required": true, "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 6}	2026-01-27 13:03:26.882008
28	44	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-27T16:06:57.668685", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "mfa_required": true, "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 6}	{"user_id": 6, "end_time": "2026-01-27T18:06:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-22T14:21:00", "mfa_required": false, "source_ip_id": 7, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 8, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 6}	2026-01-27 16:12:51.354524
29	45	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-28T14:19:07.311003", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:07.311003", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	{"user_id": 6, "end_time": "2026-01-28T14:19:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": true, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	2026-01-28 13:54:58.293282
30	45	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-28T14:19:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": true, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	{"user_id": 6, "end_time": "2026-01-28T14:19:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	2026-01-28 13:56:13.845608
31	45	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-28T15:50:08.659125", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	{"user_id": 6, "end_time": "2026-01-28T15:50:08.659125", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	2026-01-28 14:50:24.431636
32	45	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-28T15:50:08.659125", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	{"user_id": 6, "end_time": "2027-01-28T15:50:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:19:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 10, "port_forwarding_allowed": true, "inactivity_timeout_minutes": 60}	2026-01-28 14:50:43.921235
33	46	7	policy_updated	\N	\N	\N	{"user_id": 6, "end_time": "2026-01-29T08:01:23.001646", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:35:33.286038", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 11, "port_forwarding_allowed": false, "inactivity_timeout_minutes": 60}	{"user_id": 6, "end_time": "2026-01-29T08:01:00", "protocol": null, "is_active": true, "schedules": [], "scope_type": "server", "ssh_logins": [], "start_time": "2026-01-28T13:35:00", "mfa_required": false, "source_ip_id": null, "use_schedules": false, "user_group_id": null, "target_group_id": null, "target_server_id": 11, "port_forwarding_allowed": false, "inactivity_timeout_minutes": 6}	2026-01-29 07:03:13.732129
\.


--
-- Data for Name: policy_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.policy_schedules (id, policy_id, name, weekdays, time_start, time_end, months, days_of_month, timezone, is_active, created_at) FROM stdin;
4	25	Business Hours	{0,1,2,3,4}	08:00:00	16:00:00	\N	\N	Europe/Warsaw	t	2026-01-06 15:54:59.221347
11	30	test 2	{0,1,2,3,4,5,6}	10:30:00	22:00:00	\N	\N	Europe/Warsaw	t	2026-01-06 17:19:30.225843
12	36	13-14	\N	13:00:00	13:59:00	\N	\N	Europe/Warsaw	t	2026-01-12 10:36:00.742439
\.


--
-- Data for Name: policy_ssh_logins; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.policy_ssh_logins (id, policy_id, allowed_login) FROM stdin;
8	10	cisco
11	15	p.mojski
25	33	admin
27	30	p.mojski
29	34	p.mojski
30	35	p.mojski
32	37	p.mojski
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
1	97	scp_upload	/home/user/document.pdf	2458624	\N	\N	\N	\N	0	0	2026-01-06 13:15:45.308054	2026-01-06 13:15:53.308054
2	97	sftp_download	/var/log/syslog	15728640	\N	\N	\N	\N	0	0	2026-01-06 13:17:45.308054	2026-01-06 13:18:30.308054
3	97	port_forward_local	\N	\N	127.0.0.1	8080	internal-server.local	80	524288	2097152	2026-01-06 13:16:45.308054	2026-01-06 13:24:45.308054
4	97	socks_connection	\N	\N	\N	\N	google.com	443	12345	67890	2026-01-06 13:19:45.308054	2026-01-06 13:20:00.308054
6	105	sftp_session	\N	\N	\N	\N	\N	\N	305	1299003	2026-01-06 14:18:39.949874	2026-01-06 14:18:48.047456
7	106	sftp_session	\N	\N	\N	\N	\N	\N	305	1299003	2026-01-06 14:19:18.752745	2026-01-06 14:19:26.818198
8	108	port_forward_local	\N	\N	100.64.0.20	45538	las.init1.pl	25	12	126	2026-01-06 14:27:47.004092	2026-01-06 14:27:50.446851
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.sessions (id, session_id, user_id, server_id, protocol, source_ip, proxy_ip, backend_ip, backend_port, ssh_username, started_at, ended_at, duration_seconds, recording_path, recording_size, is_active, termination_reason, policy_id, created_at, subsystem_name, ssh_agent_used, connection_status, denial_reason, denial_details, protocol_version, stay_id, gate_id) FROM stdin;
103	100.64.0.20_1767708693.864036	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:11:34.218354	2026-01-06 14:11:44.214036	9	\N	\N	f	normal	\N	2026-01-06 14:11:34.222411	sftp	t	active	\N	\N	\N	\N	\N
104	100.64.0.20_1767708952.630941	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:15:52.962127	2026-01-06 14:16:01.671544	8	\N	\N	f	normal	\N	2026-01-06 14:15:52.96849	sftp	t	active	\N	\N	\N	\N	\N
6	100.64.0.20_1767538334.310123	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 14:52:14.606757	2026-01-04 14:58:22.813259	368	\N	\N	f	normal	\N	2026-01-04 14:52:14.607973	\N	t	active	\N	\N	\N	\N	\N
9	unruffled_wiles_8878585	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 14:58:36.745954	2026-01-04 15:01:20.487749	\N	\N	\N	f	\N	\N	2026-01-04 14:58:36.748145	\N	f	active	\N	\N	\N	\N	\N
10	blissful_jackson_2474083	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:02:22.821475	2026-01-04 15:04:33.524742	\N	\N	\N	f	manual_cleanup	\N	2026-01-04 15:02:22.823699	\N	f	active	\N	\N	\N	\N	\N
11	determined_sinoussi_4168695	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:04:50.028112	2026-01-04 15:04:51.199822	1	rdp_replay_20260104_15-04-49_900_determined_sinoussi_4168695.pyrdp	\N	f	normal	\N	2026-01-04 15:04:50.031561	\N	f	active	\N	\N	\N	\N	\N
12	thirsty_pare_8468314	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:04:53.500173	2026-01-04 15:05:06.140991	12	rdp_replay_20260104_15-04-53_488_thirsty_pare_8468314.pyrdp	\N	f	normal	\N	2026-01-04 15:04:53.500789	\N	f	active	\N	\N	\N	\N	\N
13	jovial_yalow_8252105	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:06:03.112955	2026-01-04 15:06:04.242346	1	rdp_replay_20260104_15-06-03_103_jovial_yalow_8252105.pyrdp	\N	f	normal	\N	2026-01-04 15:06:03.113319	\N	f	active	\N	\N	\N	\N	\N
15	relaxed_hopper_7222850	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:06:19.868379	2026-01-04 15:06:21.008873	1	rdp_replay_20260104_15-06-19_851_relaxed_hopper_7222850.pyrdp	\N	f	normal	\N	2026-01-04 15:06:19.869065	\N	f	active	\N	\N	\N	\N	\N
14	compassionate_mcnulty_3753012	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:06:07.688632	2026-01-04 15:06:38.665852	30	rdp_replay_20260104_15-06-07_670_compassionate_mcnulty_3753012.pyrdp	\N	f	normal	\N	2026-01-04 15:06:07.689694	\N	f	active	\N	\N	\N	\N	\N
16	frosty_bassi_6767861	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:06:22.984364	2026-01-04 15:06:43.680843	20	rdp_replay_20260104_15-06-22_974_frosty_bassi_6767861.pyrdp	\N	f	normal	\N	2026-01-04 15:06:22.984763	\N	f	active	\N	\N	\N	\N	\N
17	100.64.0.20_1767539503.495504	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:11:43.879799	2026-01-04 15:12:04.073638	20	\N	\N	f	normal	\N	2026-01-04 15:11:43.880704	\N	t	active	\N	\N	\N	\N	\N
18	100.64.0.20_1767539620.602707	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:13:41.021835	2026-01-04 15:14:41.527384	60	\N	\N	f	normal	\N	2026-01-04 15:13:41.030806	\N	t	active	\N	\N	\N	\N	\N
19	100.64.0.20_1767539682.380049	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:14:42.682944	2026-01-04 15:14:43.882483	1	\N	\N	f	normal	\N	2026-01-04 15:14:42.68391	\N	t	active	\N	\N	\N	\N	\N
21	upbeat_brattain_9793178	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:18:31.765677	2026-01-04 15:18:32.924101	1	rdp_replay_20260104_15-18-31_626_upbeat_brattain_9793178.pyrdp	\N	f	normal	\N	2026-01-04 15:18:31.7695	\N	f	active	\N	\N	\N	\N	\N
22	awesome_jang_4293901	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 15:18:36.942524	2026-01-04 15:19:06.423567	29	rdp_replay_20260104_15-18-36_927_awesome_jang_4293901.pyrdp	\N	f	normal	\N	2026-01-04 15:18:36.943903	\N	f	active	\N	\N	\N	\N	\N
20	100.64.0.20_1767539685.713076	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:14:46.020594	2026-01-04 15:32:30.563832	1064	\N	\N	f	normal	\N	2026-01-04 15:14:46.022209	\N	t	active	\N	\N	\N	\N	\N
23	100.64.0.20_1767541661.295768	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:47:41.695961	2026-01-04 15:47:52.909256	11	\N	\N	f	normal	\N	2026-01-04 15:47:41.69713	\N	t	active	\N	\N	\N	\N	\N
24	100.64.0.20_1767541909.322988	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:51:49.643683	2026-01-04 15:52:31.378847	41	\N	\N	f	normal	\N	2026-01-04 15:51:49.64463	\N	t	active	\N	\N	\N	\N	\N
25	100.64.0.20_1767542043.092928	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 15:54:03.395407	2026-01-04 15:55:35.605292	92	\N	\N	f	normal	\N	2026-01-04 15:54:03.396322	\N	t	active	\N	\N	\N	\N	\N
26	100.64.0.20_1767542405.888029	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 16:00:06.309282	2026-01-04 16:11:26.331332	680	/var/log/jumphost/ssh_recordings/20260104_160006_p.mojski_10_0_160_4_100.64.0.20_1767542405.888029.log	39541	f	normal	\N	2026-01-04 16:00:06.316091	\N	t	active	\N	\N	\N	\N	\N
28	cocky_gates_7478743	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 16:19:24.307899	2026-01-04 16:19:25.467439	1	rdp_replay_20260104_16-19-24_205_cocky_gates_7478743.pyrdp	\N	f	normal	\N	2026-01-04 16:19:24.310112	\N	f	active	\N	\N	\N	\N	\N
29	objective_swanson_9110480	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 16:20:11.550992	2026-01-04 16:21:03.616964	52	rdp_replay_20260104_16-20-11_536_objective_swanson_9110480.pyrdp	\N	f	normal	\N	2026-01-04 16:20:11.551563	\N	f	active	\N	\N	\N	\N	\N
27	100.64.0.20_1767543259.272914	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 16:14:19.676447	2026-01-04 16:22:56.168721	516	/var/log/jumphost/ssh_recordings/20260104_161419_p.mojski_10_0_160_4_100.64.0.20_1767543259.272914.log	2852	f	normal	\N	2026-01-04 16:14:19.682317	\N	t	active	\N	\N	\N	\N	\N
30	100.64.0.20_1767543866.391603	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 16:24:26.700311	2026-01-04 16:26:03.733024	97	/var/log/jumphost/ssh_recordings/20260104_162426_p.mojski_10_0_160_4_100.64.0.20_1767543866.391603.log	2129	f	normal	\N	2026-01-04 16:24:26.702376	\N	t	active	\N	\N	\N	\N	\N
31	100.64.0.20_1767544026.915879	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-04 16:27:07.212839	2026-01-05 07:01:55.557769	52488	/var/log/jumphost/ssh_recordings/20260104_162707_p.mojski_10_0_160_4_100.64.0.20_1767544026.915879.log	3176	f	normal	\N	2026-01-04 16:27:07.213743	\N	t	active	\N	\N	\N	\N	\N
32	100.64.0.20_1767596517.308847	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 07:01:57.617699	2026-01-05 07:01:58.348142	0	/var/log/jumphost/ssh_recordings/20260105_070157_p.mojski_10_0_160_4_100.64.0.20_1767596517.308847.log	1575	f	normal	\N	2026-01-05 07:01:57.619033	\N	t	active	\N	\N	\N	\N	\N
33	100.64.0.20_1767596523.175847	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 07:02:03.473561	2026-01-05 07:02:15.399575	11	/var/log/jumphost/ssh_recordings/20260105_070203_p.mojski_10_0_160_4_100.64.0.20_1767596523.175847.log	3515	f	normal	\N	2026-01-05 07:02:03.474517	\N	t	active	\N	\N	\N	\N	\N
34	100.64.0.20_1767596555.558833	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 07:02:35.856678	2026-01-05 07:04:39.435728	123	/var/log/jumphost/ssh_recordings/20260105_070235_p.mojski_10_0_160_4_100.64.0.20_1767596555.558833.log	1462	f	normal	\N	2026-01-05 07:02:35.858063	\N	t	active	\N	\N	\N	\N	\N
36	100.64.0.20_1767599199.19837	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 07:46:39.736787	2026-01-05 07:46:43.265904	3	/var/log/jumphost/ssh_recordings/20260105_074639_p.mojski_10_0_160_4_100.64.0.20_1767599199.19837.log	2415	f	normal	\N	2026-01-05 07:46:39.743376	\N	t	active	\N	\N	\N	\N	\N
38	stupefied_ramanujan_5462697	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-05 10:24:06.203369	2026-01-05 10:24:07.386011	1	rdp_replay_20260105_10-24-06_87_stupefied_ramanujan_5462697.pyrdp	\N	f	normal	\N	2026-01-05 10:24:06.206619	\N	f	active	\N	\N	\N	\N	\N
35	100.64.0.20_1767596684.214669	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 07:04:44.524181	2026-01-05 11:49:12.434337	\N	/var/log/jumphost/ssh_recordings/20260105_070444_p.mojski_10_0_160_4_100.64.0.20_1767596684.214669.log	\N	f	\N	\N	2026-01-05 07:04:44.525329	\N	t	active	\N	\N	\N	\N	\N
7	inspiring_pasteur_3058608	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 14:55:24.783831	2026-01-05 12:59:47.272749	79462	\N	\N	f	service_restart	\N	2026-01-04 14:55:24.78725	\N	f	active	\N	\N	\N	\N	\N
8	admiring_colden_7841793	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-04 14:55:28.914225	2026-01-05 12:59:47.272749	79458	\N	\N	f	service_restart	\N	2026-01-04 14:55:28.914706	\N	f	active	\N	\N	\N	\N	\N
39	eloquent_galileo_8262673	6	2	rdp	100.64.0.39	10.0.160.130	10.30.0.140	3389	\N	2026-01-05 10:24:09.814749	2026-01-05 10:24:42.732812	32	rdp_replay_20260105_10-24-09_804_eloquent_galileo_8262673.pyrdp	\N	f	normal	\N	2026-01-05 10:24:09.815265	\N	f	active	\N	\N	\N	\N	\N
37	10.30.14.3_1767608445.756636	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 10:20:46.304751	2026-01-05 11:49:12.434337	\N	/var/log/jumphost/ssh_recordings/20260105_102046_p.mojski_10_0_160_4_10.30.14.3_1767608445.756636.log	\N	f	\N	\N	2026-01-05 10:20:46.308667	\N	t	active	\N	\N	\N	\N	\N
51	100.64.0.20_1767618015.43207	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:00:15.775507	2026-01-05 13:01:30.150622	74	/var/log/jumphost/ssh_recordings/20260105_130015_p.mojski_10_0_160_4_100.64.0.20_1767618015.43207.log	\N	f	service_restart	\N	2026-01-05 13:00:15.779742	\N	t	active	\N	\N	\N	\N	\N
40	10.30.14.3_1767614242.700558	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 11:57:23.251946	2026-01-05 11:57:37.220946	13	/var/log/jumphost/ssh_recordings/20260105_115722_p.mojski_10_0_160_4_10.30.14.3_1767614242.700558.log	6133	f	normal	\N	2026-01-05 11:57:23.255133	\N	t	active	\N	\N	\N	\N	\N
41	10.30.14.3_1767614387.555266	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 11:59:48.086053	2026-01-05 11:59:49.144926	1	/var/log/jumphost/ssh_recordings/20260105_115947_p.mojski_10_0_160_4_10.30.14.3_1767614387.555266.log	2011	f	normal	\N	2026-01-05 11:59:48.086928	\N	t	active	\N	\N	\N	\N	\N
52	100.64.0.20_1767618107.088572	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:01:47.453603	2026-01-05 13:03:43.141429	115	/var/log/jumphost/ssh_recordings/20260105_130147_p.mojski_10_0_160_4_100.64.0.20_1767618107.088572.log	\N	f	service_restart	\N	2026-01-05 13:01:47.457475	\N	t	active	\N	\N	\N	\N	\N
42	10.30.14.3_1767614575.117335	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:02:55.81222	2026-01-05 12:02:59.499272	3	/var/log/jumphost/ssh_recordings/20260105_120255_p.mojski_10_0_160_4_10.30.14.3_1767614575.117335.log	1461	f	normal	\N	2026-01-05 12:02:55.818347	\N	t	active	\N	\N	\N	\N	\N
53	100.64.0.20_1767618239.231622	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:03:59.570581	2026-01-05 13:04:47.402817	47	/var/log/jumphost/ssh_recordings/20260105_130359_p.mojski_10_0_160_4_100.64.0.20_1767618239.231622.log	\N	f	service_restart	\N	2026-01-05 13:03:59.574166	\N	t	active	\N	\N	\N	\N	\N
43	10.30.14.3_1767614985.460696	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:09:46.030701	2026-01-05 12:09:46.875907	0	/var/log/jumphost/ssh_recordings/20260105_120945_p.mojski_10_0_160_4_10.30.14.3_1767614985.460696.log	1574	f	normal	\N	2026-01-05 12:09:46.036482	\N	t	active	\N	\N	\N	\N	\N
44	10.30.14.3_1767615099.773953	6	1	ssh	10.30.14.3	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:11:40.434709	2026-01-05 12:11:43.470989	3	/var/log/jumphost/ssh_recordings/20260105_121140_p.mojski_10_0_160_4_10.30.14.3_1767615099.773953.log	2885	f	normal	\N	2026-01-05 12:11:40.442756	\N	t	active	\N	\N	\N	\N	\N
54	100.64.0.20_1767618292.938079	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:04:53.279008	2026-01-05 13:06:02.136573	68	/var/log/jumphost/ssh_recordings/20260105_130453_p.mojski_10_0_160_4_100.64.0.20_1767618292.938079.log	\N	f	service_restart	\N	2026-01-05 13:04:53.282418	\N	t	active	\N	\N	\N	\N	\N
55	100.64.0.20_1767618374.493211	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:06:14.857539	2026-01-05 13:06:27.214083	12	/var/log/jumphost/ssh_recordings/20260105_130614_p.mojski_10_0_160_4_100.64.0.20_1767618374.493211.log	2491	f	normal	\N	2026-01-05 13:06:14.860182	\N	t	active	\N	\N	\N	\N	\N
46	100.64.0.20_1767617069.242528	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:44:29.67968	2026-01-05 12:44:33.444756	3	/var/log/jumphost/ssh_recordings/20260105_124429_p.mojski_10_0_160_4_100.64.0.20_1767617069.242528.log	1575	f	normal	\N	2026-01-05 12:44:29.683793	\N	t	active	\N	\N	\N	\N	\N
56	100.64.0.20_1767618482.982324	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:08:03.306052	2026-01-05 13:08:56.035185	52	/var/log/jumphost/ssh_recordings/20260105_130803_p.mojski_10_0_160_4_100.64.0.20_1767618482.982324.log	\N	f	service_restart	\N	2026-01-05 13:08:03.309407	\N	t	active	\N	\N	\N	\N	\N
48	100.64.0.20_1767617359.539168	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:49:19.942662	2026-01-05 12:50:21.43707	61	/var/log/jumphost/ssh_recordings/20260105_124919_p.mojski_10_0_160_4_100.64.0.20_1767617359.539168.log	2641	f	normal	\N	2026-01-05 12:49:19.947049	\N	t	active	\N	\N	\N	\N	\N
49	100.64.0.20_1767617571.950254	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:52:52.290815	2026-01-05 12:53:56.873487	64	/var/log/jumphost/ssh_recordings/20260105_125252_p.mojski_10_0_160_4_100.64.0.20_1767617571.950254.log	31588	f	normal	\N	2026-01-05 12:52:52.295282	\N	t	active	\N	\N	\N	\N	\N
57	100.64.0.20_1767618541.054965	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:09:01.407308	2026-01-05 13:09:03.50318	2	/var/log/jumphost/ssh_recordings/20260105_130901_p.mojski_10_0_160_4_100.64.0.20_1767618541.054965.log	2002	f	normal	\N	2026-01-05 13:09:01.410844	\N	t	active	\N	\N	\N	\N	\N
45	100.64.0.20_1767615300.989813	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:15:01.282245	2026-01-05 12:59:47.272749	2685	/var/log/jumphost/ssh_recordings/20260105_121501_p.mojski_10_0_160_4_100.64.0.20_1767615300.989813.log	\N	f	service_restart	\N	2026-01-05 12:15:01.283237	\N	t	active	\N	\N	\N	\N	\N
47	100.64.0.20_1767617133.266727	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:45:33.586514	2026-01-05 12:59:47.272749	853	/var/log/jumphost/ssh_recordings/20260105_124533_p.mojski_10_0_160_4_100.64.0.20_1767617133.266727.log	\N	f	service_restart	\N	2026-01-05 12:45:33.587561	\N	t	active	\N	\N	\N	\N	\N
50	100.64.0.20_1767617643.765951	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 12:54:04.071678	2026-01-05 12:59:47.272749	343	/var/log/jumphost/ssh_recordings/20260105_125403_p.mojski_10_0_160_4_100.64.0.20_1767617643.765951.log	\N	f	service_restart	\N	2026-01-05 12:54:04.072588	\N	t	active	\N	\N	\N	\N	\N
58	100.64.0.20_1767618633.794714	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:10:34.150042	2026-01-05 13:12:30.023334	115	/var/log/jumphost/ssh_recordings/20260105_131033_p.mojski_10_0_160_4_100.64.0.20_1767618633.794714.log	\N	f	service_restart	\N	2026-01-05 13:10:34.153489	\N	t	active	\N	\N	\N	\N	\N
59	100.64.0.20_1767618768.770073	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:12:49.109445	2026-01-05 13:16:26.412679	217	/var/log/jumphost/ssh_recordings/20260105_131248_p.mojski_10_0_160_4_100.64.0.20_1767618768.770073.log	\N	f	service_restart	\N	2026-01-05 13:12:49.111988	\N	t	active	\N	\N	\N	\N	\N
60	100.64.0.20_1767618991.513833	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:16:31.831002	2026-01-05 13:17:28.836795	57	/var/log/jumphost/ssh_recordings/20260105_131631_p.mojski_10_0_160_4_100.64.0.20_1767618991.513833.log	\N	f	service_restart	\N	2026-01-05 13:16:31.834341	\N	t	active	\N	\N	\N	\N	\N
61	100.64.0.20_1767619069.816008	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:17:50.164242	2026-01-05 13:18:38.14314	47	/var/log/jumphost/ssh_recordings/20260105_131749_p.mojski_10_0_160_4_100.64.0.20_1767619069.816008.log	\N	f	service_restart	\N	2026-01-05 13:17:50.167693	\N	t	active	\N	\N	\N	\N	\N
62	100.64.0.20_1767619122.630367	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:18:42.980854	2026-01-05 13:20:33.808929	110	/var/log/jumphost/ssh_recordings/20260105_131842_p.mojski_10_0_160_4_100.64.0.20_1767619122.630367.log	\N	f	service_restart	\N	2026-01-05 13:18:42.985161	\N	t	active	\N	\N	\N	\N	\N
63	100.64.0.20_1767619548.640001	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:25:48.991791	2026-01-05 13:27:31.442678	102	/var/log/jumphost/ssh_recordings/20260105_132548_p.mojski_10_0_160_4_100.64.0.20_1767619548.640001.log	\N	f	service_restart	\N	2026-01-05 13:25:48.995009	\N	t	active	\N	\N	\N	\N	\N
64	100.64.0.20_1767619657.867492	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:27:38.195181	2026-01-05 13:27:56.373104	18	/var/log/jumphost/ssh_recordings/20260105_132738_p.mojski_10_0_160_4_100.64.0.20_1767619657.867492.log	5375	f	normal	\N	2026-01-05 13:27:38.199314	\N	t	active	\N	\N	\N	\N	\N
65	100.64.0.20_1767619880.732106	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 13:31:21.061724	2026-01-05 14:15:34.961586	2653	/var/log/jumphost/ssh_recordings/20260105_133120_p.mojski_10_0_160_4_100.64.0.20_1767619880.732106.log	\N	f	service_restart	\N	2026-01-05 13:31:21.06542	\N	t	active	\N	\N	\N	\N	\N
66	100.64.0.20_1767622948.024648	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:22:28.423335	2026-01-05 14:23:42.56275	74	/var/log/jumphost/ssh_recordings/20260105_142228_p.mojski_10_0_160_4_100.64.0.20_1767622948.024648.log	4378	f	normal	\N	2026-01-05 14:22:28.426762	\N	t	active	\N	\N	\N	\N	\N
67	100.64.0.20_1767623023.431301	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:23:43.793906	2026-01-05 14:26:26.903423	163	/var/log/jumphost/ssh_recordings/20260105_142343_p.mojski_10_0_160_4_100.64.0.20_1767623023.431301.log	\N	f	service_restart	\N	2026-01-05 14:23:43.795293	\N	t	active	\N	\N	\N	\N	\N
68	100.64.0.20_1767623196.374411	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:26:36.745378	2026-01-05 14:27:57.212316	80	/var/log/jumphost/ssh_recordings/20260105_142636_p.mojski_10_0_160_4_100.64.0.20_1767623196.374411.log	\N	f	service_restart	\N	2026-01-05 14:26:36.748139	\N	t	active	\N	\N	\N	\N	\N
69	100.64.0.20_1767623295.403284	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:28:15.785162	2026-01-05 14:29:03.022329	47	/var/log/jumphost/ssh_recordings/20260105_142815_p.mojski_10_0_160_4_100.64.0.20_1767623295.403284.log	\N	f	service_restart	\N	2026-01-05 14:28:15.788735	\N	t	active	\N	\N	\N	\N	\N
70	100.64.0.20_1767623351.333009	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:29:11.707189	2026-01-05 14:31:42.825363	151	/var/log/jumphost/ssh_recordings/20260105_142911_p.mojski_10_0_160_4_100.64.0.20_1767623351.333009.log	\N	f	service_restart	\N	2026-01-05 14:29:11.709797	\N	t	active	\N	\N	\N	\N	\N
71	100.64.0.20_1767623511.841442	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:31:52.173856	2026-01-05 14:34:56.852839	184	/var/log/jumphost/ssh_recordings/20260105_143151_p.mojski_10_0_160_4_100.64.0.20_1767623511.841442.log	\N	f	service_restart	\N	2026-01-05 14:31:52.176923	\N	t	active	\N	\N	\N	\N	\N
72	100.64.0.20_1767623699.30478	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:34:59.659797	2026-01-05 14:37:48.062347	168	/var/log/jumphost/ssh_recordings/20260105_143459_p.mojski_10_0_160_4_100.64.0.20_1767623699.30478.log	\N	f	service_restart	\N	2026-01-05 14:34:59.666064	\N	t	active	\N	\N	\N	\N	\N
73	100.64.0.20_1767623881.187711	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:38:01.52976	2026-01-05 14:40:06.405902	124	/var/log/jumphost/ssh_recordings/20260105_143801_p.mojski_10_0_160_4_100.64.0.20_1767623881.187711.log	14085	f	normal	\N	2026-01-05 14:38:01.534533	\N	t	active	\N	\N	\N	\N	\N
74	100.64.0.20_1767624014.079579	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:40:14.411018	2026-01-05 14:40:57.328576	42	/var/log/jumphost/ssh_recordings/20260105_144014_p.mojski_10_0_160_4_100.64.0.20_1767624014.079579.log	8174	f	normal	\N	2026-01-05 14:40:14.412023	\N	t	active	\N	\N	\N	\N	\N
75	100.64.0.20_1767624061.577082	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:41:01.893269	2026-01-05 14:50:54.528667	592	/var/log/jumphost/ssh_recordings/20260105_144101_p.mojski_10_0_160_4_100.64.0.20_1767624061.577082.log	7624	f	normal	\N	2026-01-05 14:41:01.894752	\N	t	active	\N	\N	\N	\N	\N
76	100.64.0.20_1767624666.127733	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:51:06.433808	2026-01-05 14:51:07.512921	1	/var/log/jumphost/ssh_recordings/20260105_145106_p.mojski_10_0_160_4_100.64.0.20_1767624666.127733.log	1575	f	normal	\N	2026-01-05 14:51:06.44414	\N	t	active	\N	\N	\N	\N	\N
77	100.64.0.20_1767624670.574146	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-05 14:51:10.87271	2026-01-06 12:14:34.280823	77003	/var/log/jumphost/ssh_recordings/20260105_145110_p.mojski_10_0_160_4_100.64.0.20_1767624670.574146.log	\N	f	service_restart	\N	2026-01-05 14:51:10.874056	\N	t	active	\N	\N	\N	\N	\N
78	100.64.0.20_1767701740.645875	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:15:40.962896	2026-01-06 12:16:47.103557	66	/var/log/jumphost/ssh_recordings/20260106_121540_p.mojski_10_0_160_4_100.64.0.20_1767701740.645875.log	2336	f	normal	\N	2026-01-06 12:15:40.967777	\N	t	active	\N	\N	\N	\N	\N
79	100.64.0.20_1767701825.28053	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:17:05.573019	2026-01-06 12:17:22.011412	16	/var/log/jumphost/ssh_recordings/20260106_121705_p.mojski_10_0_160_4_100.64.0.20_1767701825.28053.log	2322	f	normal	\N	2026-01-06 12:17:05.57463	\N	t	active	\N	\N	\N	\N	\N
80	100.64.0.20_1767701848.477401	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:17:28.779554	2026-01-06 12:17:56.81537	28	/var/log/jumphost/ssh_recordings/20260106_121728_p.mojski_10_0_160_4_100.64.0.20_1767701848.477401.log	1786	f	normal	\N	2026-01-06 12:17:28.78128	\N	t	active	\N	\N	\N	\N	\N
81	100.64.0.20_1767701878.494342	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:17:58.809773	2026-01-06 12:18:14.503632	15	/var/log/jumphost/ssh_recordings/20260106_121758_p.mojski_10_0_160_4_100.64.0.20_1767701878.494342.log	2438	f	normal	\N	2026-01-06 12:17:58.811101	\N	t	active	\N	\N	\N	\N	\N
82	100.64.0.20_1767702054.691188	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:20:55.008282	2026-01-06 12:28:01.720795	426	/var/log/jumphost/ssh_recordings/20260106_122054_p.mojski_10_0_160_4_100.64.0.20_1767702054.691188.log	3988	f	normal	\N	2026-01-06 12:20:55.010259	\N	t	active	\N	\N	\N	\N	\N
83	100.64.0.20_1767702697.323124	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:31:37.671036	2026-01-06 12:31:37.696471	0	/var/log/jumphost/ssh_recordings/20260106_133137_p.mojski_10_0_160_4_100.64.0.20_1767702697.323124.log	\N	f	error	\N	2026-01-06 12:31:37.67459	\N	t	active	\N	\N	\N	\N	\N
84	100.64.0.20_1767702814.383355	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:33:34.707986	2026-01-06 12:33:34.751275	0	/var/log/jumphost/ssh_recordings/20260106_133334_p.mojski_10_0_160_4_100.64.0.20_1767702814.383355.log	\N	f	error	\N	2026-01-06 12:33:34.711607	\N	t	active	\N	\N	\N	\N	\N
85	100.64.0.20_1767702863.568423	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:34:24.014113	2026-01-06 12:34:24.051136	0	/var/log/jumphost/ssh_recordings/20260106_133423_p.mojski_10_0_160_4_100.64.0.20_1767702863.568423.log	\N	f	error	\N	2026-01-06 12:34:24.018733	\N	t	active	\N	\N	\N	\N	\N
86	100.64.0.20_1767702913.260003	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:35:13.606283	2026-01-06 12:35:13.742112	0	/var/log/jumphost/ssh_recordings/20260106_133513_p.mojski_10_0_160_4_100.64.0.20_1767702913.260003.log	898	f	normal	\N	2026-01-06 12:35:13.610743	\N	t	active	\N	\N	\N	\N	\N
87	100.64.0.20_1767703007.043673	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:36:47.355144	2026-01-06 12:36:47.480111	0	/var/log/jumphost/ssh_recordings/20260106_133647_p.mojski_10_0_160_4_100.64.0.20_1767703007.043673.log	318	f	normal	\N	2026-01-06 12:36:47.35659	\N	t	active	\N	\N	\N	\N	\N
88	100.64.0.20_1767703257.86489	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:40:58.234855	2026-01-06 12:42:28.454612	90	/var/log/jumphost/ssh_recordings/20260106_134058_p.mojski_10_0_160_4_100.64.0.20_1767703257.86489.log	1461	f	normal	\N	2026-01-06 12:40:58.239277	\N	t	active	\N	\N	\N	\N	\N
89	100.64.0.20_1767703383.592504	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:43:03.91993	2026-01-06 12:45:42.69579	158	/var/log/jumphost/ssh_recordings/20260106_134303_p.mojski_10_0_160_4_100.64.0.20_1767703383.592504.log	3707	f	normal	\N	2026-01-06 12:43:03.923664	\N	t	active	\N	\N	\N	\N	\N
90	100.64.0.20_1767703782.487888	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:49:42.811079	2026-01-06 12:50:49.104345	66	/var/log/jumphost/ssh_recordings/20260106_134942_p.mojski_10_0_160_4_100.64.0.20_1767703782.487888.log	\N	f	service_restart	\N	2026-01-06 12:49:42.812416	\N	t	active	\N	\N	\N	\N	\N
122	100.64.0.20_1767793641.212853	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 13:47:22.006091	2026-01-07 13:47:51.679698	29	/tmp/gate-recordings/100.64.0.20_1767793641.212853.jsonl	\N	f	error	30	2026-01-07 13:47:22.011742	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
91	100.64.0.20_1767703851.763934	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:50:52.068607	2026-01-06 12:50:56.417952	4	/var/log/jumphost/ssh_recordings/20260106_135051_p.mojski_10_0_160_4_100.64.0.20_1767703851.763934.log	1462	f	normal	\N	2026-01-06 12:50:52.072853	\N	t	active	\N	\N	\N	\N	\N
123	100.64.0.20_1767793677.875832	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 13:47:58.393364	2026-01-07 13:51:19.993691	201	/tmp/gate-recordings/100.64.0.20_1767793677.875832.jsonl	\N	f	service_restart	30	2026-01-07 13:47:58.394384	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
92	100.64.0.20_1767703884.177395	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 12:51:24.492417	2026-01-06 12:58:22.6979	418	/var/log/jumphost/ssh_recordings/20260106_135124_p.mojski_10_0_160_4_100.64.0.20_1767703884.177395.log	3921	f	normal	\N	2026-01-06 12:51:24.494156	\N	t	active	\N	\N	\N	\N	\N
272	100.64.0.20_1769595359.762432	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:16:07.120553	2026-01-28 10:16:16.294507	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_111607_100.64.0.20_1769595359.762432.rec	1433	f	normal	39	2026-01-28 10:16:07.122106	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	122	3
93	100.64.0.20_1767704825.842602	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 13:07:06.161409	2026-01-06 13:08:10.357436	64	/var/log/jumphost/ssh_recordings/20260106_140705_p.mojski_10_0_160_4_100.64.0.20_1767704825.842602.log	11759	f	normal	\N	2026-01-06 13:07:06.162772	\N	t	active	\N	\N	\N	\N	\N
128	100.64.0.20_1768127596.411562	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 10:33:16.908273	2026-01-11 10:35:54.371632	157	/tmp/gate-recordings/100.64.0.20_1768127596.411562.jsonl	\N	f	service_restart	30	2026-01-11 10:33:16.915233	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
94	100.64.0.20_1767704891.000083	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 13:08:11.319506	2026-01-06 13:08:23.25136	11	/var/log/jumphost/ssh_recordings/20260106_140811_p.mojski_10_0_160_4_100.64.0.20_1767704891.000083.log	19600	f	normal	\N	2026-01-06 13:08:11.320328	\N	t	active	\N	\N	\N	\N	\N
95	100.64.0.20_1767704905.240004	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 13:08:25.549094	2026-01-06 13:09:06.898379	41	/var/log/jumphost/ssh_recordings/20260106_140825_p.mojski_10_0_160_4_100.64.0.20_1767704905.240004.log	\N	f	service_restart	\N	2026-01-06 13:08:25.550055	\N	t	active	\N	\N	\N	\N	\N
131	100.64.0.20_1768128531.73203	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 10:48:52.314311	2026-01-11 10:51:28.062305	\N	/tmp/gate-recordings/100.64.0.20_1768128531.73203.jsonl	\N	f	error	30	2026-01-11 10:48:52.316659	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	1	1
96	100.64.0.20_1767704951.09462	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 13:09:11.419481	2026-01-06 13:14:15.994583	304	/var/log/jumphost/ssh_recordings/20260106_140911_p.mojski_10_0_160_4_100.64.0.20_1767704951.09462.log	\N	f	service_restart	\N	2026-01-06 13:09:11.423859	\N	t	active	\N	\N	\N	\N	\N
97	100.64.0.20_1767705284.974052	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 13:14:45.308054	2026-01-06 13:55:07.616716	2422	/var/log/jumphost/ssh_recordings/20260106_141445_p.mojski_10_0_160_4_100.64.0.20_1767705284.974052.log	77987	f	normal	\N	2026-01-06 13:14:45.311199	\N	t	active	\N	\N	\N	\N	\N
133	100.64.0.20_1768129540.656111	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 11:05:41.084089	2026-01-11 11:22:26.846877	\N	/tmp/gate-recordings/100.64.0.20_1768129540.656111.jsonl	\N	f	error	30	2026-01-11 11:05:41.086163	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	2	1
98	100.64.0.20_1767708060.778818	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:01:01.101833	2026-01-06 14:01:10.221118	9	/var/log/jumphost/ssh_recordings/20260106_150100_p.mojski_10_0_160_4_100.64.0.20_1767708060.778818.log	8364	f	normal	\N	2026-01-06 14:01:01.10577	\N	t	active	\N	\N	\N	\N	\N
99	100.64.0.20_1767708077.779318	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:01:18.084895	2026-01-06 14:01:18.21913	0	/var/log/jumphost/ssh_recordings/20260106_150117_p.mojski_10_0_160_4_100.64.0.20_1767708077.779318.log	2920	f	normal	\N	2026-01-06 14:01:18.085861	sftp	t	active	\N	\N	\N	\N	\N
135	100.64.0.20_1768130560.974566	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 11:22:41.3415	2026-01-11 11:57:08.202184	\N	/tmp/gate-recordings/100.64.0.20_1768130560.974566.jsonl	\N	f	error	30	2026-01-11 11:22:41.342216	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	2	1
100	100.64.0.20_1767708085.70214	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:01:25.99506	2026-01-06 14:01:40.399478	14	/var/log/jumphost/ssh_recordings/20260106_150125_p.mojski_10_0_160_4_100.64.0.20_1767708085.70214.log	459848	f	normal	\N	2026-01-06 14:01:25.996924	sftp	t	active	\N	\N	\N	\N	\N
101	100.64.0.20_1767708213.559754	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:03:33.861634	2026-01-06 14:03:42.608201	8	/var/log/jumphost/ssh_recordings/20260106_150333_p.mojski_10_0_160_4_100.64.0.20_1767708213.559754.log	1192970	f	normal	\N	2026-01-06 14:03:33.86261	sftp	t	active	\N	\N	\N	\N	\N
137	100.64.0.20_1768139884.075043	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 13:58:04.559762	2026-01-11 14:16:50.74819	\N	/tmp/gate-recordings/100.64.0.20_1768139884.075043.jsonl	\N	f	error	30	2026-01-11 13:58:04.562324	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	4	1
102	100.64.0.20_1767708497.277034	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:08:17.643147	2026-01-06 14:08:25.539474	7	/var/log/jumphost/ssh_recordings/20260106_150817_p.mojski_10_0_160_4_100.64.0.20_1767708497.277034.log	1192970	f	normal	\N	2026-01-06 14:08:17.646262	sftp	t	active	\N	\N	\N	\N	\N
139	100.64.0.20_1768141241.801477	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 14:20:42.259797	2026-01-11 14:35:59.912451	\N	/tmp/gate-recordings/100.64.0.20_1768141241.801477.jsonl	\N	f	error	30	2026-01-11 14:20:42.272556	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	4	1
140	100.64.0.20_1768144011.122864	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 15:06:51.582611	2026-01-11 15:50:12.85381	2601	/tmp/gate-recordings/100.64.0.20_1768144011.122864.jsonl	\N	f	service_restart	30	2026-01-11 15:06:51.585715	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	5	1
141	100.64.0.20_1768148133.322756	6	7	ssh	100.64.0.20	10.0.160.134	10.30.10.15	22	admin	2026-01-11 16:15:35.645022	2026-01-11 16:16:00.619289	\N	/tmp/gate-recordings/100.64.0.20_1768148133.322756.jsonl	\N	f	error	33	2026-01-11 16:15:35.647716	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	6	1
142	100.64.0.20_1768148173.323479	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 16:16:13.817159	2026-01-11 16:16:15.510062	\N	/tmp/gate-recordings/100.64.0.20_1768148173.323479.jsonl	\N	f	error	30	2026-01-11 16:16:13.817883	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	7	1
143	100.64.0.20_1768148388.195282	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 16:19:51.965149	2026-01-11 16:19:52.983367	\N	/tmp/gate-recordings/100.64.0.20_1768148388.195282.jsonl	\N	f	error	30	2026-01-11 16:19:51.967192	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	8	1
144	100.64.0.20_1768148397.097706	6	7	ssh	100.64.0.20	10.0.160.134	10.30.10.15	22	admin	2026-01-11 16:20:01.509515	2026-01-11 16:20:20.438925	\N	/tmp/gate-recordings/100.64.0.20_1768148397.097706.jsonl	\N	f	error	33	2026-01-11 16:20:01.510206	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	9	1
105	100.64.0.20_1767709119.57683	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:18:39.922239	2026-01-06 14:18:48.154538	8	\N	\N	f	normal	\N	2026-01-06 14:18:39.927859	sftp	t	active	\N	\N	\N	\N	\N
209	100.64.0.20_1768206403.471897	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:26:44.42002	2026-01-12 08:27:57.442672	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_092644_100.64.0.20_1768206403.471897.rec	4296	f	normal	34	2026-01-12 08:26:44.421336	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	62	3
106	100.64.0.20_1767709158.455067	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:19:18.742941	2026-01-06 14:19:26.923785	8	\N	\N	f	normal	\N	2026-01-06 14:19:18.743597	sftp	t	active	\N	\N	\N	\N	\N
127	100.64.0.20_1767799209.69177	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 15:20:10.066083	2026-01-07 15:24:19.0662	249	/tmp/gate-recordings/100.64.0.20_1767799209.69177.jsonl	\N	f	error	30	2026-01-07 15:20:10.067152	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
107	100.64.0.20_1767709241.785376	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:20:42.109537	2026-01-06 14:21:16.206639	34	/var/log/jumphost/ssh_recordings/20260106_152042_p.mojski_10_0_160_4_100.64.0.20_1767709241.785376.log	1899	f	normal	\N	2026-01-06 14:20:42.110774	\N	t	active	\N	\N	\N	\N	\N
108	100.64.0.20_1767709661.51448	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:27:41.838535	2026-01-06 14:32:41.713197	299	/var/log/jumphost/ssh_recordings/20260106_152741_p.mojski_10_0_160_4_100.64.0.20_1767709661.51448.log	\N	f	service_restart	\N	2026-01-06 14:27:41.840562	\N	t	active	\N	\N	\N	\N	\N
121	100.64.0.20_1767784798.393246	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 11:19:58.809811	2026-01-07 13:44:53.922247	8695	/opt/jumphost/logs/recordings/20260107/test_short_types.jsonl	\N	f	service_restart	30	2026-01-07 11:19:58.811928	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
109	100.64.0.20_1767710001.953716	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 14:33:22.404204	2026-01-06 14:33:26.265639	3	/var/log/jumphost/ssh_recordings/20260106_153322_p.mojski_10_0_160_4_100.64.0.20_1767710001.953716.log	5915	f	normal	\N	2026-01-06 14:33:22.412882	\N	t	active	\N	\N	\N	\N	\N
110	100.64.0.20_1767711912.574857	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 15:05:12.965543	2026-01-06 15:49:07.746051	2634	/var/log/jumphost/ssh_recordings/20260106_160512_p.mojski_10_0_160_4_100.64.0.20_1767711912.574857.log	\N	f	service_restart	\N	2026-01-06 15:05:12.970668	\N	t	active	\N	\N	\N	\N	\N
124	100.64.0.20_1767793888.564246	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 13:51:29.154268	2026-01-07 13:53:25.279397	116	/tmp/gate-recordings/100.64.0.20_1767793888.564246.jsonl	\N	f	error	30	2026-01-07 13:51:29.156829	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
111	100.64.0.20_1767716931.56875	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:28:51.910189	2026-01-06 16:29:17.190878	25	/var/log/jumphost/ssh_recordings/20260106_172851_p.mojski_10_0_160_4_100.64.0.20_1767716931.56875.log	1461	f	normal	\N	2026-01-06 16:28:51.913791	\N	t	active	\N	\N	\N	\N	\N
112	100.64.0.20_1767716999.734006	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:30:00.122457	2026-01-06 16:33:52.806424	232	/var/log/jumphost/ssh_recordings/20260106_173000_p.mojski_10_0_160_4_100.64.0.20_1767716999.734006.log	3421	f	normal	\N	2026-01-06 16:30:00.126698	\N	t	active	\N	\N	\N	\N	\N
125	100.64.0.20_1767794049.710766	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 13:54:10.100896	2026-01-07 14:32:43.417476	2313	/tmp/gate-recordings/100.64.0.20_1767794049.710766.jsonl	\N	f	error	30	2026-01-07 13:54:10.10255	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
113	100.64.0.20_1767717233.457814	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:33:53.900804	2026-01-06 16:33:54.64403	0	/var/log/jumphost/ssh_recordings/20260106_173353_p.mojski_10_0_160_4_100.64.0.20_1767717233.457814.log	1575	f	normal	\N	2026-01-06 16:33:53.902189	\N	t	active	\N	\N	\N	\N	\N
114	100.64.0.20_1767717235.526758	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:33:55.96771	2026-01-06 16:33:56.080758	0	/var/log/jumphost/ssh_recordings/20260106_173355_p.mojski_10_0_160_4_100.64.0.20_1767717235.526758.log	739	f	normal	\N	2026-01-06 16:33:55.969014	\N	t	active	\N	\N	\N	\N	\N
126	100.64.0.20_1767799197.058581	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 15:19:57.426787	2026-01-07 15:20:08.995498	11	/tmp/gate-recordings/100.64.0.20_1767799197.058581.jsonl	\N	f	error	30	2026-01-07 15:19:57.428092	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
115	100.64.0.20_1767717251.891832	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:34:12.332449	2026-01-06 16:40:31.068613	378	/var/log/jumphost/ssh_recordings/20260106_173412_p.mojski_10_0_160_4_100.64.0.20_1767717251.891832.log	2012	f	normal	\N	2026-01-06 16:34:12.333716	\N	t	active	\N	\N	\N	\N	\N
129	100.64.0.20_1768127766.841099	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 10:36:07.434178	2026-01-11 10:47:11.707011	664	/tmp/gate-recordings/100.64.0.20_1768127766.841099.jsonl	\N	f	error	30	2026-01-11 10:36:07.437571	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
116	100.64.0.20_1767717634.433451	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 16:40:34.733645	2026-01-06 16:59:01.105969	1106	/var/log/jumphost/ssh_recordings/20260106_174034_p.mojski_10_0_160_4_100.64.0.20_1767717634.433451.log	1201	f	normal	\N	2026-01-06 16:40:34.734708	\N	t	active	\N	\N	\N	\N	\N
130	100.64.0.20_1768128432.654993	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 10:47:13.22154	2026-01-11 10:48:36.163101	82	/tmp/gate-recordings/100.64.0.20_1768128432.654993.jsonl	\N	f	service_restart	30	2026-01-11 10:47:13.223539	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
117	100.64.0.20_1767721590.61279	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 17:46:31.070803	2026-01-06 18:00:01.10503	810	/var/log/jumphost/ssh_recordings/20260106_184631_p.mojski_10_0_160_4_100.64.0.20_1767721590.61279.log	2153	f	normal	30	2026-01-06 17:46:31.0765	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	\N	\N
118	d713eee5-5ec8-45b6-bfd8-13a536a94c27	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 18:21:32.402706	2026-01-06 18:21:32.402759	\N	\N	\N	f	\N	30	2026-01-06 18:21:32.406785	\N	f	denied	outside_schedule	Outside allowed time windows	\N	\N	\N
119	1ba5ef03-7039-474c-bf32-2c71e7ed80fd	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-06 18:34:58.057345	2026-01-06 18:34:58.057351	\N	\N	\N	f	\N	30	2026-01-06 18:34:58.058116	\N	f	denied	outside_schedule	Outside allowed time windows	\N	\N	\N
120	e00b824c-977b-442a-b47c-7975910056a8	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-07 09:12:16.559112	2026-01-07 09:12:16.559119	\N	\N	\N	f	\N	30	2026-01-07 09:12:16.560049	\N	f	denied	outside_schedule	Outside allowed time windows	\N	\N	\N
132	100.64.0.20_1768128646.578964	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 10:50:46.938823	2026-01-11 10:52:04.571884	\N	/tmp/gate-recordings/100.64.0.20_1768128646.578964.jsonl	\N	f	error	30	2026-01-11 10:50:46.939663	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	1	1
134	100.64.0.20_1768130532.577375	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 11:22:13.037292	2026-01-11 11:22:47.120503	\N	/tmp/gate-recordings/100.64.0.20_1768130532.577375.jsonl	\N	f	error	30	2026-01-11 11:22:13.039669	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	2	1
136	100.64.0.20_1768133056.790764	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 12:04:17.224952	2026-01-11 12:04:24.80543	\N	/tmp/gate-recordings/100.64.0.20_1768133056.790764.jsonl	\N	f	error	30	2026-01-11 12:04:17.236829	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	3	1
138	100.64.0.20_1768140714.49933	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 14:11:54.936507	2026-01-11 14:36:22.959254	\N	/tmp/gate-recordings/100.64.0.20_1768140714.49933.jsonl	\N	f	error	30	2026-01-11 14:11:54.939164	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	4	1
145	100.64.0.20_1768148422.876284	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 16:20:23.272809	2026-01-11 16:20:24.690616	\N	/tmp/gate-recordings/100.64.0.20_1768148422.876284.jsonl	\N	f	error	30	2026-01-11 16:20:23.273845	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	10	1
146	100.64.0.20_1768149884.605343	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 16:44:45.150194	2026-01-11 16:51:05.642992	\N	/tmp/gate-recordings/100.64.0.20_1768149884.605343.jsonl	2862	f	normal	30	2026-01-11 16:44:45.151929	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	11	1
147	100.64.0.20_1768150561.207566	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 16:56:01.622358	2026-01-11 17:04:37.129478	515	/tmp/gate-recordings/100.64.0.20_1768150561.207566.jsonl	\N	f	service_restart	30	2026-01-11 16:56:01.624359	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	12	1
150	100.64.0.20_1768151173.419097	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:06:13.882922	2026-01-11 17:12:18.618843	364	/tmp/gate-recordings/100.64.0.20_1768151173.419097.jsonl	\N	f	service_restart	30	2026-01-11 17:06:13.885482	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	13	1
152	100.64.0.20_1768151609.790956	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:13:30.215735	2026-01-11 17:13:59.378142	\N	/tmp/gate-recordings/100.64.0.20_1768151609.790956.jsonl	739	f	normal	30	2026-01-11 17:13:30.218068	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	14	1
159	100.64.0.20_1768153189.308806	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:39:49.734387	2026-01-11 17:41:47.529898	117	/tmp/gate-recordings/100.64.0.20_1768153189.308806.jsonl	\N	f	service_restart	30	2026-01-11 17:39:49.735082	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	19	1
153	100.64.0.20_1768151781.816581	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:16:22.363441	2026-01-11 17:16:59.498734	\N	/tmp/gate-recordings/100.64.0.20_1768151781.816581.jsonl	739	f	normal	30	2026-01-11 17:16:22.365851	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	15	1
156	100.64.0.20_1768152585.285081	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:29:45.69717	2026-01-11 17:33:03.059205	197	/tmp/gate-recordings/100.64.0.20_1768152585.285081.jsonl	\N	f	service_restart	30	2026-01-11 17:29:45.699248	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	16	1
157	100.64.0.20_1768152804.63246	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:33:25.090126	2026-01-11 17:38:24.937167	299	/tmp/gate-recordings/100.64.0.20_1768152804.63246.jsonl	\N	f	service_restart	30	2026-01-11 17:33:25.09203	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	17	1
158	100.64.0.20_1768153110.949508	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:38:31.439153	2026-01-11 17:39:27.609232	\N	/tmp/gate-recordings/100.64.0.20_1768153110.949508.jsonl	739	f	normal	30	2026-01-11 17:38:31.441354	\N	t	active	\N	{"reason": "Scheduled maintenance", "disconnect_at": "2026-01-11T17:39:02.309147"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	18	1
160	100.64.0.20_1768153311.019851	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:41:51.497528	2026-01-11 17:42:49.665312	\N	/tmp/gate-recordings/100.64.0.20_1768153311.019851.jsonl	739	f	normal	30	2026-01-11 17:41:51.499882	\N	t	active	\N	{"reason": "Scheduled maintenance", "disconnect_at": "2026-01-11T17:42:30.561154"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	20	1
161	100.64.0.20_1768153378.341801	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:42:58.754555	2026-01-11 17:43:01.328773	\N	/tmp/gate-recordings/100.64.0.20_1768153378.341801.jsonl	1149	f	normal	30	2026-01-11 17:42:58.756268	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	21	1
164	100.64.0.20_1768156606.831309	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 18:36:47.227171	2026-01-11 18:49:41.544154	\N	/tmp/gate-recordings/100.64.0.20_1768156606.831309.jsonl	1708	f	normal	30	2026-01-11 18:36:47.232035	\N	t	active	\N	{"reason": "Scheduled gate maintenance", "disconnect_at": "2026-01-11T18:49:12.948867"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	23	1
162	100.64.0.20_1768153669.117298	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 17:47:49.551874	2026-01-11 17:58:28.525739	638	/tmp/gate-recordings/100.64.0.20_1768153669.117298.jsonl	1472	f	normal	30	2026-01-11 17:47:49.553713	\N	t	active	\N	{"reason": "Scheduled maintenance", "disconnect_at": "2026-01-11T17:50:30.562406"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	22	1
170	100.64.0.20_1768157875.473375	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 18:57:55.970052	2026-01-11 18:59:12.130115	\N	/tmp/gate-recordings/100.64.0.20_1768157875.473375.jsonl	889	f	normal	30	2026-01-11 18:57:55.971879	\N	t	active	\N	{"reason": "Scheduled gate maintenance", "disconnect_at": "2026-01-11T18:58:48.661851"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	24	1
172	100.64.0.20_1768157966.569621	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 18:59:26.978233	2026-01-11 19:04:10.133464	\N	/tmp/gate-recordings/100.64.0.20_1768157966.569621.jsonl	2144	f	normal	30	2026-01-11 18:59:26.979209	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	25	1
173	100.64.0.20_1768158251.272022	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:04:11.663041	2026-01-11 19:08:43.83196	\N	/tmp/gate-recordings/100.64.0.20_1768158251.272022.jsonl	889	f	normal	30	2026-01-11 19:04:11.663579	\N	t	active	\N	{"reason": "Scheduled server maintenance", "disconnect_at": "2026-01-11T19:08:14.845989"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	26	1
178	100.64.0.20_1768158544.847562	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:09:05.274817	2026-01-11 19:09:22.879256	\N	/tmp/gate-recordings/100.64.0.20_1768158544.847562.jsonl	1149	f	normal	30	2026-01-11 19:09:05.276823	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	27	1
179	100.64.0.20_1768158563.788692	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:09:24.201195	2026-01-11 19:09:37.591923	\N	/tmp/gate-recordings/100.64.0.20_1768158563.788692.jsonl	2516	f	normal	30	2026-01-11 19:09:24.201932	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	28	1
180	100.64.0.20_1768158751.943087	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:12:32.38973	2026-01-11 19:13:22.567989	\N	/tmp/gate-recordings/100.64.0.20_1768158751.943087.jsonl	739	f	normal	30	2026-01-11 19:12:32.392227	\N	t	active	\N	{"reason": "Scheduled server maintenance", "disconnect_at": "2026-01-11T19:12:52.405138"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	29	1
182	100.64.0.20_1768158826.604674	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:13:47.002892	2026-01-11 19:20:57.634099	\N	/tmp/gate-recordings/100.64.0.20_1768158826.604674.jsonl	2118	f	normal	30	2026-01-11 19:13:47.003679	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	30	1
183	100.64.0.20_1768159261.611374	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:21:02.049468	2026-01-11 19:58:49.496835	\N	/tmp/gate-recordings/100.64.0.20_1768159261.611374.jsonl	1322	f	normal	30	2026-01-11 19:21:02.051624	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	31	1
184	100.64.0.20_1768161216.593916	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:53:36.991433	2026-01-11 20:00:00.187413	\N	/tmp/gate-recordings/100.64.0.20_1768161216.593916.jsonl	1212	f	normal	30	2026-01-11 19:53:36.993401	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	31	1
185	100.64.0.20_1768161530.21388	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 19:58:50.605029	2026-01-11 19:59:00.73141	\N	/tmp/gate-recordings/100.64.0.20_1768161530.21388.jsonl	7288	f	normal	30	2026-01-11 19:58:50.605685	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	31	1
186	100.64.0.20_1768161744.832113	6	1	ssh	100.64.0.20	10.0.160.129	10.0.160.4	22	p.mojski	2026-01-11 20:02:25.230971	2026-01-11 20:02:28.199699	\N	/tmp/gate-recordings/100.64.0.20_1768161744.832113.jsonl	2441	f	normal	30	2026-01-11 20:02:25.231592	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	32	1
187	100.64.0.20_1768169212.55208	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 22:06:53.592743	2026-01-11 22:06:53.615372	\N	/tmp/gate-recordings/100.64.0.20_1768169212.55208.jsonl	\N	f	error	34	2026-01-11 22:06:53.594384	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	33	3
188	100.64.0.20_1768169265.427445	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 22:07:46.440348	2026-01-11 22:07:46.459021	\N	/tmp/gate-recordings/100.64.0.20_1768169265.427445.jsonl	\N	f	error	34	2026-01-11 22:07:46.441295	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	34	3
190	100.64.0.20_1768169727.045782	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 22:15:28.13571	2026-01-11 22:20:48.639914	\N	/opt/jumphost/logs/recordings/20260111/p.mojski_rancher-2_20260111_231528_100.64.0.20_1768169727.045782.rec	6858	f	normal	34	2026-01-11 22:15:28.13819	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	35	3
189	100.64.0.20_1768169407.631718	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 22:10:08.734846	2026-01-11 23:00:19.024409	3010	/tmp/gate-recordings/100.64.0.20_1768169407.631718.jsonl	\N	f	gate_restart	34	2026-01-11 22:10:08.736583	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	35	3
191	100.64.0.20_1768172458.254177	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 23:01:00.057579	2026-01-11 23:06:09.577644	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_000059_100.64.0.20_1768172458.254177.rec	4240	f	normal	34	2026-01-11 23:01:00.059003	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	36	3
194	100.64.0.20_1768202444.552407	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:20:45.913614	2026-01-12 07:22:27.723991	101	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_082045_100.64.0.20_1768202444.552407.rec	\N	f	gate_restart	34	2026-01-12 07:20:45.914763	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	39	3
192	100.64.0.20_1768172848.159519	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-11 23:07:29.536498	2026-01-12 07:14:33.00127	29223	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_000729_100.64.0.20_1768172848.159519.rec	\N	f	gate_restart	34	2026-01-11 23:07:29.539285	\N	t	active	\N	{"reason": "Scheduled server maintenance", "disconnect_at": "2026-01-11T23:13:42.799238"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	37	3
193	100.64.0.20_1768202166.708687	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:16:08.578402	2026-01-12 07:20:14.122771	245	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_081608_100.64.0.20_1768202166.708687.rec	\N	f	gate_restart	34	2026-01-12 07:16:08.579703	\N	t	active	\N	{"reason": "Scheduled server maintenance", "disconnect_at": "2026-01-12T07:16:28.609253"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	38	3
196	100.64.0.20_1768202696.547586	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:24:57.97192	2026-01-12 07:25:34.133645	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_082457_100.64.0.20_1768202696.547586.rec	1511	f	normal	34	2026-01-12 07:24:57.972335	\N	t	active	\N	{"reason": "Scheduled gate maintenance", "disconnect_at": "2026-01-12T07:25:15.538335"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	41	3
195	100.64.0.20_1768202567.254893	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:22:48.603797	2026-01-12 07:24:03.858862	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_082248_100.64.0.20_1768202567.254893.rec	1436	f	normal	34	2026-01-12 07:22:48.608111	\N	t	active	\N	{"reason": "Scheduled server maintenance", "disconnect_at": "2026-01-12T07:23:36.910092"}	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	40	3
197	100.64.0.20_1768202801.58725	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:26:43.014088	2026-01-12 07:29:54.188483	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_082642_100.64.0.20_1768202801.58725.rec	12244	f	normal	34	2026-01-12 07:26:43.015027	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	42	3
198	100.64.0.20_1768202997.595426	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:29:58.918342	2026-01-12 07:42:49.871702	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_082958_100.64.0.20_1768202997.595426.rec	1593	f	normal	34	2026-01-12 07:29:58.918766	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	43	3
199	100.64.0.20_1768203854.142148	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:44:16.015286	2026-01-12 07:44:16.287524	\N	\N	\N	f	normal	34	2026-01-12 07:44:16.015938	sftp	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	44	3
200	100.64.0.20_1768203875.628178	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:44:37.000373	2026-01-12 07:57:26.068216	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_084436_100.64.0.20_1768203875.628178.rec	9731	f	normal	34	2026-01-12 07:44:37.001278	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	45	3
201	100.64.0.20_1768204647.23187	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 07:57:28.498176	2026-01-12 08:01:54.837732	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_085728_100.64.0.20_1768204647.23187.rec	2751	f	normal	34	2026-01-12 07:57:28.498703	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	46	3
202	100.64.0.20_1768204916.30613	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:01:57.377719	2026-01-12 08:05:24.148255	206	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_090157_100.64.0.20_1768204916.30613.rec	\N	f	gate_restart	34	2026-01-12 08:01:57.380615	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	48	3
203	100.64.0.20_1768205165.678716	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:06:07.141531	2026-01-12 08:14:22.319636	495	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_090607_100.64.0.20_1768205165.678716.rec	\N	f	gate_restart	34	2026-01-12 08:06:07.143053	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	50	3
204	100.64.0.20_1768205675.057968	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:14:36.77463	2026-01-12 08:16:54.71077	137	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_091436_100.64.0.20_1768205675.057968.rec	\N	f	gate_restart	34	2026-01-12 08:14:36.776952	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	52	3
205	100.64.0.20_1768205824.631245	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:17:06.312539	2026-01-12 08:20:26.086822	199	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_091706_100.64.0.20_1768205824.631245.rec	\N	f	gate_restart	34	2026-01-12 08:17:06.315544	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	54	3
206	100.64.0.20_1768206033.339989	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:20:34.73043	2026-01-12 08:20:48.170467	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_092034_100.64.0.20_1768206033.339989.rec	3734	f	normal	34	2026-01-12 08:20:34.732628	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	56	3
207	100.64.0.20_1768206072.462169	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:21:13.827612	2026-01-12 08:21:24.5694	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_092113_100.64.0.20_1768206072.462169.rec	1592	f	normal	34	2026-01-12 08:21:13.828246	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	58	3
210	100.64.0.20_1768206494.391851	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:28:19.198964	2026-01-12 08:28:27.765671	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_092819_100.64.0.20_1768206494.391851.rec	1591	f	normal	34	2026-01-12 08:28:19.199749	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	64	3
208	100.64.0.20_1768206088.690399	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:21:29.641212	2026-01-12 08:26:38.594879	308	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_092129_100.64.0.20_1768206088.690399.rec	\N	f	gate_restart	34	2026-01-12 08:21:29.641602	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	60	3
211	100.64.0.20_1768206656.866841	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:31:03.585503	2026-01-12 08:31:46.210498	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_093103_100.64.0.20_1768206656.866841.rec	1517	f	normal	34	2026-01-12 08:31:03.587912	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	66	3
212	100.64.0.20_1768207896.114324	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 08:51:38.187607	2026-01-12 08:53:46.23051	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_095138_100.64.0.20_1768207896.114324.rec	1805	f	normal	34	2026-01-12 08:51:38.188225	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	68	3
213	100.64.0.20_1768208552.34678	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:02:33.89816	2026-01-12 09:02:42.552742	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_100233_100.64.0.20_1768208552.34678.rec	1516	f	normal	34	2026-01-12 09:02:33.89867	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	70	3
282	100.64.0.20_1769600094.332713	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 11:35:05.635148	2026-01-28 11:36:38.342855	92	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_123505_100.64.0.20_1769600094.332713.rec	\N	f	gate_restart	39	2026-01-28 11:35:05.637644	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	130	3
214	100.64.0.20_1768209453.727542	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:17:35.343026	2026-01-12 09:19:11.069011	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_101735_100.64.0.20_1768209453.727542.rec	1517	f	normal	34	2026-01-12 09:17:35.344833	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	71	3
215	100.64.0.20_1768209705.99952	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:21:47.044082	2026-01-12 09:25:00.685036	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_102147_100.64.0.20_1768209705.99952.rec	24666	f	normal	35	2026-01-12 09:21:47.044758	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
217	100.64.0.20_1768209920.89855	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:25:21.910556	2026-01-12 09:25:52.347129	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_102521_100.64.0.20_1768209920.89855.rec	1590	f	normal	35	2026-01-12 09:25:21.911618	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
216	100.64.0.20_1768209744.570003	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:22:25.981494	2026-01-12 09:26:46.414214	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_102225_100.64.0.20_1768209744.570003.rec	1593	f	normal	34	2026-01-12 09:22:25.982544	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
219	100.64.0.20_1768210038.165343	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:27:19.138725	2026-01-12 09:28:08.910024	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_102719_100.64.0.20_1768210038.165343.rec	1590	f	normal	35	2026-01-12 09:27:19.139219	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
218	100.64.0.20_1768209964.023967	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:26:05.088607	2026-01-12 09:29:32.273422	207	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_102605_100.64.0.20_1768209964.023967.rec	\N	f	gate_restart	34	2026-01-12 09:26:05.089728	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
220	100.64.0.20_1768210091.36113	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:28:12.358727	2026-01-12 09:29:32.273422	79	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_102812_100.64.0.20_1768210091.36113.rec	\N	f	gate_restart	34	2026-01-12 09:28:12.35952	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	72	3
222	100.64.0.20_1768210334.075211	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:32:15.606149	2026-01-12 09:35:54.208513	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_103215_100.64.0.20_1768210334.075211.rec	1593	f	normal	34	2026-01-12 09:32:15.607084	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	73	3
221	100.64.0.20_1768210213.901766	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:30:14.907838	2026-01-12 09:36:28.076828	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_103014_100.64.0.20_1768210213.901766.rec	5186	f	normal	35	2026-01-12 09:30:14.909238	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	73	3
223	100.64.0.20_1768210570.222624	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:36:11.050772	2026-01-12 09:37:47.039262	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_103611_100.64.0.20_1768210570.222624.rec	1590	f	normal	35	2026-01-12 09:36:11.053422	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	73	3
224	100.64.0.20_1768210596.001759	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 09:36:37.44695	2026-01-12 09:59:14.826614	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_103637_100.64.0.20_1768210596.001759.rec	2380	f	normal	34	2026-01-12 09:36:37.447894	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	73	3
225	100.64.0.20_1768211498.109446	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 09:51:39.168145	2026-01-12 09:59:33.116658	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_105139_100.64.0.20_1768211498.109446.rec	1591	f	normal	35	2026-01-12 09:51:39.169062	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	73	3
226	100.64.0.20_1768213019.527189	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 10:17:02.162122	2026-01-12 10:17:04.592889	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_111702_100.64.0.20_1768213019.527189.rec	2961	f	normal	34	2026-01-12 10:17:02.163998	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	74	3
227	100.64.0.20_1768214784.442599	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 10:46:26.077483	2026-01-12 10:58:44.056214	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_114626_100.64.0.20_1768214784.442599.rec	1518	f	normal	37	2026-01-12 10:46:26.080059	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	75	3
228	100.64.0.20_1768216083.298578	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 11:08:04.910531	2026-01-12 11:08:07.709075	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_120804_100.64.0.20_1768216083.298578.rec	1676	f	normal	37	2026-01-12 11:08:04.912624	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	76	3
273	100.64.0.20_1769597318.683831	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:48:44.005442	2026-01-28 10:48:44.026295	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_114843_100.64.0.20_1769597318.683831.rec	\N	f	error	39	2026-01-28 10:48:44.007288	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	123	3
229	100.64.0.20_1768220921.884486	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 12:28:43.65273	2026-01-12 12:31:05.978706	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_132843_100.64.0.20_1768220921.884486.rec	1512	f	normal	37	2026-01-12 12:28:43.65512	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	77	3
278	100.64.0.20_1769598464.877074	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 11:07:54.2369	2026-01-28 11:20:47.218909	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_120754_100.64.0.20_1769598464.877074.rec	1647	f	normal	39	2026-01-28 11:07:54.239329	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	128	3
230	100.64.0.20_1768221287.710062	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 12:34:49.042865	2026-01-12 15:47:10.551361	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_164710_100.64.0.20_1768221287.710062.rec	5784	f	normal	37	2026-01-12 12:34:49.045243	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	78	3
231	100.64.0.1_1768227178.510036	8	9	ssh	100.64.0.1	10.210.1.189	10.210.1.189	22	k.kawalec	2026-01-12 14:12:59.719424	2026-01-12 16:00:47.757565	6468	/opt/jumphost/logs/recordings/20260112/k.kawalec_rancher1_20260112_151259_100.64.0.1_1768227178.510036.rec	\N	f	gate_restart	38	2026-01-12 14:12:59.722226	\N	t	active	\N	No matching policy (user or group)	SSH-2.0-OpenSSH_10.0	79	3
283	100.64.0.20_1769600203.975116	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 11:36:51.252161	2026-01-28 12:26:39.314178	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_123651_100.64.0.20_1769600203.975116.rec	1436	f	normal	39	2026-01-28 11:36:51.253954	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	131	3
289	100.64.0.20_1769608343.799955	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:52:41.738996	2026-01-28 13:52:51.714194	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_145241_100.64.0.20_1769608343.799955.rec	1245	f	normal	45	2026-01-28 13:52:41.739773	\N	f	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
291	100.64.0.20_1769608504.076864	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:55:33.489667	2026-01-28 13:55:51.868358	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_145533_100.64.0.20_1769608504.076864.rec	1244	f	normal	45	2026-01-28 13:55:33.490327	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
302	100.64.0.20_1769613735.706409	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:22:16.242385	2026-01-28 15:22:16.374432	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_162216_100.64.0.20_1769613735.706409.rec	553	f	normal	45	2026-01-28 15:22:16.243732	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	137	4
301	100.64.0.20_1769613708.261397	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:22:11.595905	2026-01-28 15:23:50.465335	98	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_162211_100.64.0.20_1769613708.261397.rec	\N	f	gate_restart	45	2026-01-28 15:22:11.597934	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	137	4
307	100.64.0.20_1769764195.516024	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-30 09:10:01.310954	2026-01-30 10:09:31.731973	\N	/opt/jumphost/logs/recordings/20260130/p.mojski_rancher1_20260130_101001_100.64.0.20_1769764195.516024.rec	12116	f	normal	39	2026-01-30 09:10:01.311614	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	141	3
310	100.64.0.20_1771418228.984312	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:37:22.278808	2026-02-18 12:39:45.781631	143	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_133722_100.64.0.20_1771418228.984312.rec	\N	f	gate_restart	45	2026-02-18 12:37:22.279672	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	143	4
318	100.64.0.20_1771418659.205035	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:44:19.741625	2026-02-18 12:44:19.871712	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134419_100.64.0.20_1771418659.205035.rec	553	f	normal	45	2026-02-18 12:44:19.742543	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	146	4
319	100.64.0.20_1771418806.797558	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:46:53.731632	2026-02-18 12:49:41.781457	168	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134653_100.64.0.20_1771418806.797558.rec	\N	f	gate_restart	45	2026-02-18 12:46:53.733706	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	147	4
232	100.64.0.20_1768228221.029435	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 14:30:22.226718	2026-01-12 14:30:40.795462	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_153022_100.64.0.20_1768228221.029435.rec	2461	f	normal	35	2026-01-12 14:30:22.227481	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	78	3
274	100.64.0.20_1769597448.487275	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:50:53.772162	2026-01-28 10:50:53.790952	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_115053_100.64.0.20_1769597448.487275.rec	\N	f	error	39	2026-01-28 10:50:53.773318	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	124	3
233	100.64.0.20_1768228275.5344	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-12 14:31:16.734157	2026-01-12 15:45:25.569023	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher1_20260112_153116_100.64.0.20_1768228275.5344.rec	2016	f	normal	39	2026-01-12 14:31:16.735214	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	78	3
234	100.64.0.20_1768232889.595923	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 15:48:11.321378	2026-01-12 15:51:41.668604	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_164811_100.64.0.20_1768232889.595923.rec	1512	f	normal	37	2026-01-12 15:48:11.322643	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	80	3
235	100.64.0.20_1768233202.804448	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 15:53:24.407611	2026-01-12 15:54:42.620213	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_165324_100.64.0.20_1768233202.804448.rec	1511	f	normal	37	2026-01-12 15:53:24.409917	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	81	3
236	100.64.0.20_1768233995.223626	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 16:06:36.689994	2026-01-12 16:08:07.864495	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_170636_100.64.0.20_1768233995.223626.rec	1511	f	normal	40	2026-01-12 16:06:36.691592	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	82	3
237	100.64.0.20_1768235091.686589	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 16:24:53.05571	2026-01-12 16:25:58.287956	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_172453_100.64.0.20_1768235091.686589.rec	1511	f	normal	40	2026-01-12 16:24:53.057606	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	83	3
238	100.64.0.20_1768235182.460844	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 16:26:23.786477	2026-01-12 16:26:57.939634	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_172623_100.64.0.20_1768235182.460844.rec	1511	f	normal	41	2026-01-12 16:26:23.787169	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	84	3
239	100.64.0.20_1768235577.216532	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 16:32:58.524191	2026-01-12 16:35:28.804758	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_173258_100.64.0.20_1768235577.216532.rec	1512	f	normal	42	2026-01-12 16:32:58.525943	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	85	3
243	100.64.0.20_1768237807.937049	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 17:10:09.37068	2026-01-12 17:19:35.148181	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_181009_100.64.0.20_1768237807.937049.rec	1512	f	normal	43	2026-01-12 17:10:09.373978	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	89	3
240	100.64.0.20_1768235763.078289	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 16:36:04.58665	2026-01-12 16:43:30.176593	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_173604_100.64.0.20_1768235763.078289.rec	1512	f	normal	42	2026-01-12 16:36:04.5872	\N	t	active	\N	No matching access policy	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	86	3
241	100.64.0.20_1768237262.884988	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 17:01:04.570476	2026-01-12 17:04:11.238011	186	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_180104_100.64.0.20_1768237262.884988.rec	\N	f	gate_restart	43	2026-01-12 17:01:04.572129	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	87	3
242	100.64.0.20_1768237490.674649	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 17:04:52.866818	2026-01-12 17:09:58.422642	305	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_180452_100.64.0.20_1768237490.674649.rec	\N	f	gate_restart	43	2026-01-12 17:04:52.867941	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	88	3
244	100.64.0.20_1768238576.907829	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-12 17:22:58.204708	2026-01-12 17:32:00.973962	\N	/opt/jumphost/logs/recordings/20260112/p.mojski_rancher-2_20260112_182258_100.64.0.20_1768238576.907829.rec	4842	f	normal	43	2026-01-12 17:22:58.207599	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	90	3
245	100.64.0.20_1769092044.181841	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 14:27:25.453468	2026-01-22 14:34:18.869306	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_152725_100.64.0.20_1769092044.181841.rec	4556	f	normal	44	2026-01-22 14:27:25.456204	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	91	3
246	100.64.0.20_1769092459.856813	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 14:34:20.738242	2026-01-22 14:40:21.652596	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_153420_100.64.0.20_1769092459.856813.rec	1512	f	normal	44	2026-01-22 14:34:20.738862	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	92	3
247	100.64.0.20_1769093206.497545	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 14:46:47.762217	2026-01-22 14:47:08.312859	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_154647_100.64.0.20_1769093206.497545.rec	2372	f	normal	44	2026-01-22 14:46:47.764956	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	93	3
248	100.64.0.20_1769093260.613828	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 14:47:41.739976	2026-01-22 14:51:55.012497	253	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_154741_100.64.0.20_1769093260.613828.rec	\N	f	gate_restart	44	2026-01-22 14:47:41.740497	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	94	3
249	100.64.0.20_1769093529.984984	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 14:52:11.146472	2026-01-22 15:02:22.337895	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_155211_100.64.0.20_1769093529.984984.rec	29344	f	normal	44	2026-01-22 14:52:11.148068	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	95	3
250	100.64.0.20_1769094191.518755	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 15:03:12.795975	2026-01-22 15:03:29.339983	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_160312_100.64.0.20_1769094191.518755.rec	1517	f	normal	44	2026-01-22 15:03:12.797732	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	96	3
251	100.64.0.20_1769094461.701231	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-22 15:07:42.956151	2026-01-22 15:08:15.541345	\N	/opt/jumphost/logs/recordings/20260122/p.mojski_rancher-2_20260122_160742_100.64.0.20_1769094461.701231.rec	1517	f	normal	44	2026-01-22 15:07:42.958636	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	97	3
252	100.64.0.20_1769527059.512709	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 15:17:41.793333	2026-01-27 15:20:51.799068	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_161741_100.64.0.20_1769527059.512709.rec	3062	f	normal	44	2026-01-27 15:17:41.795257	\N	t	active	\N	MFA authentication required	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	101	3
275	100.64.0.20_1769597530.428744	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:52:17.682714	2026-01-28 10:52:17.70395	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_115217_100.64.0.20_1769597530.428744.rec	\N	f	error	39	2026-01-28 10:52:17.684897	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	125	3
253	100.64.0.20_1769527565.227936	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 15:26:06.469245	2026-01-27 15:26:30.215615	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_162606_100.64.0.20_1769527565.227936.rec	1517	f	normal	44	2026-01-27 15:26:06.470415	\N	t	active	\N	MFA authentication required	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	102	3
257	100.64.0.20_1769533119.197297	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 16:58:46.672919	2026-01-27 17:00:18.912339	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_175846_100.64.0.20_1769533119.197297.rec	1648	f	normal	44	2026-01-27 16:58:46.680094	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	107	3
254	100.64.0.20_1769527645.748282	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 15:27:35.197644	2026-01-27 15:29:08.423758	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_162735_100.64.0.20_1769527645.748282.rec	1511	f	normal	44	2026-01-27 15:27:35.199379	\N	t	active	\N	MFA authentication required	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	103	3
280	100.64.0.20_1769599570.641298	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-28 11:26:11.97187	2026-01-28 11:26:15.072396	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher-2_20260128_122611_100.64.0.20_1769599570.641298.rec	2961	f	normal	44	2026-01-28 11:26:11.972628	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	129	3
255	100.64.0.20_1769530375.090042	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 16:12:56.415091	2026-01-27 16:12:59.499118	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_171256_100.64.0.20_1769530375.090042.rec	2818	f	normal	44	2026-01-27 16:12:56.417154	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	104	3
256	100.64.0.20_1769531817.658849	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 16:36:58.917903	2026-01-27 16:37:01.000931	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_173658_100.64.0.20_1769531817.658849.rec	2599	f	normal	44	2026-01-27 16:36:58.919129	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	105	3
290	100.64.0.20_1769608479.431714	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:54:39.953626	2026-01-28 13:54:41.591913	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_145439_100.64.0.20_1769608479.431714.rec	1746	f	normal	45	2026-01-28 13:54:39.954448	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
284	100.64.0.20_1769605013.464593	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-28 12:57:05.811517	2026-01-28 12:57:24.351274	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher-2_20260128_135705_100.64.0.20_1769605013.464593.rec	3765	f	normal	44	2026-01-28 12:57:05.814286	\N	f	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	132	3
258	100.64.0.20_1769533223.757138	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-27 17:00:31.395986	2026-01-27 17:01:49.657314	\N	/opt/jumphost/logs/recordings/20260127/p.mojski_rancher-2_20260127_180031_100.64.0.20_1769533223.757138.rec	4779	f	normal	44	2026-01-27 17:00:31.396874	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	108	3
259	100.64.0.20_1769592048.55305	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:21:02.326613	2026-01-28 09:21:25.524279	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_102102_100.64.0.20_1769592048.55305.rec	1508	f	normal	39	2026-01-28 09:21:02.328359	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	109	3
260	100.64.0.20_1769592236.304808	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:24:11.486938	2026-01-28 09:24:26.622186	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_102411_100.64.0.20_1769592236.304808.rec	9374	f	normal	39	2026-01-28 09:24:11.487565	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	110	3
261	100.64.0.20_1769592271.710539	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:24:42.863589	2026-01-28 09:24:55.996502	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_102442_100.64.0.20_1769592271.710539.rec	2295	f	normal	39	2026-01-28 09:24:42.864147	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	111	3
292	100.64.0.20_1769608577.875744	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:56:18.396783	2026-01-28 14:05:52.090241	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_145618_100.64.0.20_1769608577.875744.rec	1245	f	normal	45	2026-01-28 13:56:18.397392	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
265	100.64.0.20_1769593301.424962	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:41:48.788954	2026-01-28 09:42:06.01312	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_104148_100.64.0.20_1769593301.424962.rec	1434	f	normal	39	2026-01-28 09:41:48.79179	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	115	3
303	100.64.0.20_1769613858.057367	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:24:22.955798	2026-01-28 16:24:26.5389	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_162422_100.64.0.20_1769613858.057367.rec	1165	f	normal	45	2026-01-28 15:24:22.957699	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	138	4
305	100.64.0.20_1769670113.60347	6	11	ssh	100.64.0.20	10.30.10.29	10.30.10.29	22	cisco	2026-01-29 07:02:36.62634	2026-01-29 07:02:52.352851	\N	/opt/jumphost/logs/recordings/20260129/p.mojski_ideo 10g_20260129_080236_100.64.0.20_1769670113.60347.rec	1336	f	normal	46	2026-01-29 07:02:36.627474	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	139	4
314	100.64.0.20_1771418429.352752	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:40:29.860852	2026-02-18 12:40:29.993167	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134029_100.64.0.20_1771418429.352752.rec	553	f	normal	45	2026-02-18 12:40:29.861607	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	144	4
313	100.64.0.20_1771418415.325679	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:40:26.295889	2026-02-18 12:41:51.180432	84	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134026_100.64.0.20_1771418415.325679.rec	\N	f	gate_restart	45	2026-02-18 12:40:26.297945	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	144	4
321	100.64.0.20_1771418997.753393	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:50:04.842057	\N	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_135004_100.64.0.20_1771418997.753393.rec	\N	t	access_revoked	45	2026-02-18 12:50:04.842676	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	148	4
262	100.64.0.20_1769592939.903269	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:35:47.554799	2026-01-28 09:35:47.584047	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_103547_100.64.0.20_1769592939.903269.rec	\N	f	error	39	2026-01-28 09:35:47.556326	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	112	3
263	100.64.0.20_1769593089.053283	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:38:16.353827	2026-01-28 09:38:16.385743	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_103816_100.64.0.20_1769593089.053283.rec	\N	f	error	39	2026-01-28 09:38:16.3559	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	113	3
264	100.64.0.20_1769593134.349774	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:39:01.668711	2026-01-28 09:39:01.689861	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_103901_100.64.0.20_1769593134.349774.rec	\N	f	error	39	2026-01-28 09:39:01.670164	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	114	3
276	100.64.0.20_1769597716.445422	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:55:23.903367	2026-01-28 10:55:23.928404	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_115523_100.64.0.20_1769597716.445422.rec	\N	f	error	39	2026-01-28 10:55:23.905825	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	126	3
266	100.64.0.20_1769593442.604063	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:44:18.209995	2026-01-28 09:44:26.39466	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_104418_100.64.0.20_1769593442.604063.rec	1433	f	normal	39	2026-01-28 09:44:18.212317	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	116	3
281	100.64.0.20_1769599615.076836	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 11:26:56.733127	2026-01-28 11:29:49.91529	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_122656_100.64.0.20_1769599615.076836.rec	1591	f	normal	39	2026-01-28 11:26:56.734028	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	129	3
285	100.64.0.20_1769607102.345217	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:31:47.168623	2026-01-28 13:32:12.571994	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_143147_100.64.0.20_1769607102.345217.rec	5825	f	normal	45	2026-01-28 13:31:47.170784	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	133	4
293	100.64.0.20_1769609153.378763	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 14:05:53.908353	2026-01-28 14:10:08.013472	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_150553_100.64.0.20_1769609153.378763.rec	36156	f	normal	45	2026-01-28 14:05:53.911488	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
304	100.64.0.20_1769613872.118779	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:24:32.643543	2026-01-28 15:24:32.773888	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_162432_100.64.0.20_1769613872.118779.rec	553	f	normal	45	2026-01-28 15:24:32.644424	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	138	4
294	100.64.0.20_1769609410.696625	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 14:10:11.24266	2026-01-28 14:10:28.624228	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_151011_100.64.0.20_1769609410.696625.rec	1244	f	normal	45	2026-01-28 14:10:11.24396	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
308	100.64.0.20_1771418033.877417	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:34:12.516041	2026-02-18 12:34:12.646118	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_133412_100.64.0.20_1771418033.877417.rec	553	f	normal	45	2026-02-18 12:34:12.516717	\N	f	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	142	4
311	100.64.0.20_1771418263.449303	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:37:43.982142	2026-02-18 12:37:44.114115	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_133743_100.64.0.20_1771418263.449303.rec	553	f	normal	45	2026-02-18 12:37:43.983115	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	143	4
315	100.64.0.20_1771418522.054857	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:42:11.03963	2026-02-18 12:43:47.310295	96	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134210_100.64.0.20_1771418522.054857.rec	\N	f	gate_restart	45	2026-02-18 12:42:11.041546	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	145	4
317	100.64.0.20_1771418648.528212	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:44:13.427837	2026-02-18 12:46:35.464197	142	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134413_100.64.0.20_1771418648.528212.rec	\N	f	gate_restart	45	2026-02-18 12:44:13.430601	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	146	4
320	100.64.0.20_1771418820.068481	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:47:00.683893	2026-02-18 12:47:00.710209	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134700_100.64.0.20_1771418820.068481.rec	553	f	normal	45	2026-02-18 12:47:00.684659	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	147	4
322	100.64.0.20_1771419025.289936	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:50:25.884144	2026-02-18 12:50:25.912792	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_135025_100.64.0.20_1771419025.289936.rec	553	f	normal	45	2026-02-18 12:50:25.884956	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	148	4
267	100.64.0.20_1769593586.638393	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:46:35.917899	2026-01-28 09:46:50.118512	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_104635_100.64.0.20_1769593586.638393.rec	1434	f	normal	39	2026-01-28 09:46:35.921814	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	117	3
277	100.64.0.20_1769597857.369025	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:57:44.566742	2026-01-28 11:07:26.375634	581	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_115744_100.64.0.20_1769597857.369025.rec	\N	f	gate_restart	39	2026-01-28 10:57:44.568872	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	127	3
268	100.64.0.20_1769594340.805969	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 09:59:10.166099	2026-01-28 09:59:41.372844	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_105910_100.64.0.20_1769594340.805969.rec	1434	f	normal	39	2026-01-28 09:59:10.168882	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	118	3
269	100.64.0.20_1769594582.970639	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:03:10.320753	2026-01-28 10:03:10.350741	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_110310_100.64.0.20_1769594582.970639.rec	\N	f	error	39	2026-01-28 10:03:10.323417	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	119	3
279	100.64.0.20_1769599536.812976	6	8	ssh	100.64.0.20	10.210.1.190	10.210.1.190	22	p.mojski	2026-01-28 11:25:45.689489	2026-01-28 11:29:27.36545	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher-2_20260128_122545_100.64.0.20_1769599536.812976.rec	17893	f	normal	44	2026-01-28 11:25:45.690838	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	129	3
270	100.64.0.20_1769594975.329879	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:09:40.615437	2026-01-28 10:09:40.653671	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_110940_100.64.0.20_1769594975.329879.rec	\N	f	error	39	2026-01-28 10:09:40.617635	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	120	3
297	100.64.0.20_1769613361.48701	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:16:02.022897	2026-01-28 15:16:03.63645	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_161601_100.64.0.20_1769613361.48701.rec	1352	f	normal	45	2026-01-28 15:16:02.023703	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	136	4
271	100.64.0.20_1769595076.944247	6	9	ssh	100.64.0.20	10.210.1.189	10.210.1.189	22	p.mojski	2026-01-28 10:11:24.207724	2026-01-28 10:11:40.399987	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_rancher1_20260128_111124_100.64.0.20_1769595076.944247.rec	1434	f	normal	39	2026-01-28 10:11:24.209224	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	121	3
286	100.64.0.20_1769607156.952555	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 13:32:48.239413	2026-01-28 14:10:48.767265	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_143248_100.64.0.20_1769607156.952555.rec	1490	f	normal	45	2026-01-28 13:32:48.239982	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
287	100.64.0.20_1769607517.866605	6	11	ssh	100.64.0.20	10.30.10.29	10.30.10.29	22	cisco	2026-01-28 13:38:48.703029	2026-01-28 13:48:48.451321	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_ideo 10g_20260128_143848_100.64.0.20_1769607517.866605.rec	646	f	normal	46	2026-01-28 13:38:48.703989	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
288	100.64.0.20_1769608155.104576	6	12	ssh	100.64.0.20	10.30.10.3	10.30.10.3	22	root	2026-01-28 13:49:17.58194	2026-01-28 13:51:12.167948	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_ideo sw p105_20260128_144917_100.64.0.20_1769608155.104576.rec	2518	f	normal	47	2026-01-28 13:49:17.582774	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	134	4
295	100.64.0.20_1769609460.409899	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 14:11:11.416152	2026-01-28 14:19:05.235521	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_151111_100.64.0.20_1769609460.409899.rec	1164	f	normal	45	2026-01-28 14:11:11.416714	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	135	4
298	100.64.0.20_1769613364.844332	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:16:05.382555	2026-01-28 15:16:05.508503	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_161605_100.64.0.20_1769613364.844332.rec	553	f	normal	45	2026-01-28 15:16:05.383271	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	136	4
299	100.64.0.20_1769613391.376032	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:16:31.908131	2026-01-28 15:16:36.265654	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_161631_100.64.0.20_1769613391.376032.rec	30110	f	normal	45	2026-01-28 15:16:31.909057	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	136	4
300	100.64.0.20_1769613398.183718	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 15:16:38.71304	2026-01-28 15:16:38.841068	\N	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_161638_100.64.0.20_1769613398.183718.rec	553	f	normal	45	2026-01-28 15:16:38.71467	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	136	4
296	100.64.0.20_1769611878.204102	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-01-28 14:51:27.13531	2026-01-28 15:21:12.906247	1785	/opt/jumphost/logs/recordings/20260128/p.mojski_p.mojski - lab_20260128_155127_100.64.0.20_1769611878.204102.rec	\N	f	gate_restart	45	2026-01-28 14:51:27.136415	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	136	4
306	100.64.0.20_1769670197.021266	6	11	ssh	100.64.0.20	10.30.10.29	10.30.10.29	22	cisco	2026-01-29 07:03:30.748807	2026-01-29 07:10:41.67538	\N	/opt/jumphost/logs/recordings/20260129/p.mojski_ideo 10g_20260129_080330_100.64.0.20_1769670197.021266.rec	821	f	normal	46	2026-01-29 07:03:30.74963	\N	t	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	140	4
312	100.64.0.20_1771418266.021036	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:37:46.534053	2026-02-18 12:37:46.66498	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_133746_100.64.0.20_1771418266.021036.rec	553	f	normal	45	2026-02-18 12:37:46.535117	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	143	4
309	100.64.0.20_1771418074.091976	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:34:51.070784	2026-02-18 12:39:45.781631	294	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_133451_100.64.0.20_1771418074.091976.rec	\N	f	gate_restart	45	2026-02-18 12:34:51.071531	\N	f	active	\N	Unknown source IP 100.64.0.20	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	143	4
316	100.64.0.20_1771418534.951312	6	10	ssh	100.64.0.20	10.30.14.3	10.30.14.3	22	pmojski	2026-02-18 12:42:15.479805	2026-02-18 12:42:15.608342	\N	/opt/jumphost/logs/recordings/20260218/p.mojski_p.mojski - lab_20260218_134215_100.64.0.20_1771418534.951312.rec	553	f	normal	45	2026-02-18 12:42:15.480566	\N	t	active	\N	\N	SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u7	145	4
\.


--
-- Data for Name: stays; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.stays (id, user_id, policy_id, gate_id, server_id, started_at, ended_at, duration_seconds, is_active, termination_reason, created_at, updated_at, ssh_key_fingerprint) FROM stdin;
63	6	34	3	8	2026-01-12 08:28:19.168014	2026-01-12 08:30:41.542812	142	f	gate_restart	2026-01-12 08:28:19.168014	2026-01-12 08:30:41.559817	\N
1	6	30	1	1	2026-01-11 10:48:52.308595	2026-01-11 10:52:04.571884	192	f	error	2026-01-11 10:48:52.311133	2026-01-11 10:52:04.596409	\N
64	6	34	3	8	2026-01-12 08:28:19.196714	2026-01-12 08:30:41.542812	142	f	gate_restart	2026-01-12 08:28:19.197507	2026-01-12 08:30:41.559825	\N
2	6	30	1	1	2026-01-11 11:05:41.076402	2026-01-11 11:57:08.202184	3087	f	error	2026-01-11 11:05:41.079058	2026-01-11 11:57:08.232343	\N
138	6	45	4	10	2026-01-28 15:24:22.952354	2026-01-28 16:24:26.5389	3603	f	normal	2026-01-28 15:24:22.953567	2026-01-28 16:24:26.580728	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
3	6	30	1	1	2026-01-11 12:04:17.218107	2026-01-11 12:04:24.80543	7	f	error	2026-01-11 12:04:17.22141	2026-01-11 12:04:24.827177	\N
4	6	30	1	1	2026-01-11 13:58:04.550199	2026-01-11 14:36:22.959254	2298	f	error	2026-01-11 13:58:04.556757	2026-01-11 14:36:22.975192	\N
65	6	34	3	8	2026-01-12 08:31:03.537388	2026-01-12 08:31:46.210498	42	f	normal	2026-01-12 08:31:03.537388	2026-01-12 08:31:46.23639	\N
66	6	34	3	8	2026-01-12 08:31:03.582285	2026-01-12 09:51:14.670761	4811	f	\N	2026-01-12 08:31:03.583628	2026-01-12 08:31:03.583633	\N
5	6	30	1	1	2026-01-11 15:06:51.577576	2026-01-11 16:16:00.619289	4149	f	error	2026-01-11 15:06:51.579911	2026-01-11 16:16:00.64531	\N
6	6	33	1	7	2026-01-11 16:15:35.638688	2026-01-11 16:16:15.510062	39	f	error	2026-01-11 16:15:35.641326	2026-01-11 16:16:15.523287	\N
7	6	30	1	1	2026-01-11 16:16:13.813901	2026-01-11 16:19:52.983367	219	f	error	2026-01-11 16:16:13.814854	2026-01-11 16:19:53.007656	\N
67	6	34	3	8	2026-01-12 08:51:38.158795	2026-01-12 08:53:46.23051	128	f	normal	2026-01-12 08:51:38.158795	2026-01-12 08:53:46.243645	\N
8	6	30	1	1	2026-01-11 16:19:51.95736	2026-01-11 16:20:20.438925	28	f	error	2026-01-11 16:19:51.960072	2026-01-11 16:20:20.447836	\N
9	6	33	1	7	2026-01-11 16:20:01.507502	2026-01-11 16:20:24.690616	23	f	error	2026-01-11 16:20:01.508193	2026-01-11 16:20:24.702286	\N
10	6	30	1	1	2026-01-11 16:20:23.270015	2026-01-11 16:51:05.642992	1842	f	normal	2026-01-11 16:20:23.270884	2026-01-11 16:51:05.672826	\N
68	6	34	3	8	2026-01-12 08:51:38.185579	2026-01-12 09:02:42.552742	664	f	normal	2026-01-12 08:51:38.186118	2026-01-12 09:02:42.573504	\N
69	6	34	3	8	2026-01-12 09:02:33.847809	2026-01-12 09:15:54.286721	800	f	gate_restart	2026-01-12 09:02:33.847809	2026-01-12 09:15:54.29696	\N
70	6	34	3	8	2026-01-12 09:02:33.896708	2026-01-12 09:15:54.286721	800	f	gate_restart	2026-01-12 09:02:33.897173	2026-01-12 09:15:54.296996	\N
11	6	30	1	1	2026-01-11 16:44:45.142528	2026-01-11 17:13:59.279849	1754	f	grant_expired	2026-01-11 16:44:45.144936	2026-01-11 17:13:59.309762	\N
12	6	30	1	1	2026-01-11 16:56:01.616515	2026-01-11 17:13:59.378142	1077	f	normal	2026-01-11 16:56:01.61952	2026-01-11 17:13:59.387408	\N
13	6	30	1	1	2026-01-11 17:06:13.87777	2026-01-11 17:16:59.400534	645	f	grant_expired	2026-01-11 17:06:13.879348	2026-01-11 17:16:59.423297	\N
14	6	30	1	1	2026-01-11 17:13:30.209222	2026-01-11 17:16:59.498734	209	f	normal	2026-01-11 17:13:30.212294	2026-01-11 17:16:59.519352	\N
71	6	34	3	8	2026-01-12 09:17:35.338321	2026-01-12 09:19:11.069011	95	f	normal	2026-01-12 09:17:35.340409	2026-01-12 09:19:11.098639	\N
72	6	35	3	9	2026-01-12 09:21:47.04215	2026-01-12 09:29:32.273422	465	f	gate_restart	2026-01-12 09:21:47.042778	2026-01-12 09:29:32.286418	\N
15	6	30	1	1	2026-01-11 17:16:22.357246	2026-01-11 17:39:27.510597	1385	f	grant_expired	2026-01-11 17:16:22.360245	2026-01-11 17:39:27.533067	\N
16	6	30	1	1	2026-01-11 17:29:45.691526	2026-01-11 17:39:27.609232	581	f	normal	2026-01-11 17:29:45.693825	2026-01-11 17:39:27.621192	\N
73	6	35	3	9	2026-01-12 09:30:14.904218	2026-01-12 09:59:33.116658	1758	f	normal	2026-01-12 09:30:14.905602	2026-01-12 09:59:33.134347	\N
17	6	30	1	1	2026-01-11 17:33:25.083825	2026-01-11 17:42:49.567217	564	f	gate_maintenance	2026-01-11 17:33:25.085935	2026-01-11 17:42:49.588321	\N
18	6	30	1	1	2026-01-11 17:38:31.433989	2026-01-11 17:42:49.665312	258	f	normal	2026-01-11 17:38:31.436178	2026-01-11 17:42:49.681351	\N
19	6	30	1	1	2026-01-11 17:39:49.730567	2026-01-11 17:43:01.328773	191	f	normal	2026-01-11 17:39:49.731215	2026-01-11 17:43:01.347899	\N
74	6	34	3	8	2026-01-12 10:17:02.158118	2026-01-12 10:17:04.592889	2	f	normal	2026-01-12 10:17:02.159971	2026-01-12 10:17:04.618111	\N
20	6	30	1	1	2026-01-11 17:41:51.49143	2026-01-11 18:49:41.448505	4069	f	gate_maintenance	2026-01-11 17:41:51.494231	2026-01-11 18:49:41.47963	\N
21	6	30	1	1	2026-01-11 17:42:58.750523	2026-01-11 18:49:41.544154	4002	f	normal	2026-01-11 17:42:58.751215	2026-01-11 18:49:41.555962	\N
75	6	37	3	8	2026-01-12 10:46:26.072302	2026-01-12 10:58:44.056214	737	f	normal	2026-01-12 10:46:26.074305	2026-01-12 10:58:44.094349	\N
22	6	30	1	1	2026-01-11 17:47:49.545308	2026-01-11 18:59:12.032257	4282	f	gate_maintenance	2026-01-11 17:47:49.547125	2026-01-11 18:59:12.052698	\N
23	6	30	1	1	2026-01-11 18:36:47.219813	2026-01-11 18:59:12.130115	1344	f	normal	2026-01-11 18:36:47.222141	2026-01-11 18:59:12.146223	\N
24	6	30	1	1	2026-01-11 18:57:55.96342	2026-01-11 19:04:10.133464	374	f	normal	2026-01-11 18:57:55.96705	2026-01-11 19:04:10.144375	\N
25	6	30	1	1	2026-01-11 18:59:26.974459	2026-01-11 19:08:43.735006	556	f	backend_maintenance	2026-01-11 18:59:26.975307	2026-01-11 19:08:43.763975	\N
26	6	30	1	1	2026-01-11 19:04:11.660482	2026-01-11 19:08:43.83196	272	f	normal	2026-01-11 19:04:11.660885	2026-01-11 19:08:43.848841	\N
27	6	30	1	1	2026-01-11 19:09:05.269087	2026-01-11 19:09:22.879256	17	f	normal	2026-01-11 19:09:05.271146	2026-01-11 19:09:22.895775	\N
28	6	30	1	1	2026-01-11 19:09:24.198632	2026-01-11 19:09:37.591923	13	f	normal	2026-01-11 19:09:24.19932	2026-01-11 19:09:37.603921	\N
29	6	30	1	1	2026-01-11 19:12:32.383027	2026-01-11 19:13:22.470228	50	f	backend_maintenance	2026-01-11 19:12:32.386323	2026-01-11 19:13:22.491017	\N
30	6	30	1	1	2026-01-11 19:13:46.999501	2026-01-11 19:20:57.634099	430	f	normal	2026-01-11 19:13:47.00021	2026-01-11 19:20:57.66	\N
31	6	30	1	1	2026-01-11 19:21:02.042623	2026-01-11 20:00:00.088921	2338	f	grant_expired	2026-01-11 19:21:02.044949	2026-01-11 20:00:00.098942	\N
32	6	30	1	1	2026-01-11 20:02:25.226914	2026-01-11 20:02:28.199699	2	f	normal	2026-01-11 20:02:25.228636	2026-01-11 20:02:28.214453	\N
33	6	34	3	8	2026-01-11 22:06:53.588814	2026-01-11 22:06:53.615372	0	f	error	2026-01-11 22:06:53.590683	2026-01-11 22:06:53.63723	\N
34	6	34	3	8	2026-01-11 22:07:46.437774	2026-01-11 22:07:46.459021	0	f	error	2026-01-11 22:07:46.438425	2026-01-11 22:07:46.47186	\N
35	6	34	3	8	2026-01-11 22:10:08.729638	2026-01-11 23:00:19.024409	3010	f	gate_restart	2026-01-11 22:10:08.73148	2026-01-11 23:00:19.032429	\N
36	6	34	3	8	2026-01-11 23:01:00.053447	2026-01-11 23:06:09.47604	309	f	grant_expired	2026-01-11 23:01:00.055322	2026-01-11 23:06:09.508571	\N
37	6	34	3	8	2026-01-11 23:07:29.527184	2026-01-12 07:14:33.00127	29223	f	gate_restart	2026-01-11 23:07:29.530113	2026-01-12 07:14:33.014599	\N
38	6	34	3	8	2026-01-12 07:16:08.573787	2026-01-12 07:20:14.122771	245	f	gate_restart	2026-01-12 07:16:08.575975	2026-01-12 07:20:14.138366	\N
39	6	34	3	8	2026-01-12 07:20:45.908126	2026-01-12 07:22:27.723991	101	f	gate_restart	2026-01-12 07:20:45.90947	2026-01-12 07:22:27.750625	\N
40	6	34	3	8	2026-01-12 07:22:48.597921	2026-01-12 07:24:03.760204	75	f	gate_maintenance	2026-01-12 07:22:48.600186	2026-01-12 07:24:03.781488	\N
41	6	34	3	8	2026-01-12 07:24:57.969221	2026-01-12 07:25:34.033239	36	f	gate_maintenance	2026-01-12 07:24:57.969681	2026-01-12 07:25:34.048622	\N
42	6	34	3	8	2026-01-12 07:26:43.011231	2026-01-12 07:29:54.188483	191	f	normal	2026-01-12 07:26:43.012098	2026-01-12 07:29:54.202305	\N
43	6	34	3	8	2026-01-12 07:29:58.916218	2026-01-12 07:42:49.871702	770	f	normal	2026-01-12 07:29:58.916676	2026-01-12 07:42:49.891008	\N
44	6	34	3	8	2026-01-12 07:44:16.012198	2026-01-12 07:44:16.287524	0	f	normal	2026-01-12 07:44:16.012861	2026-01-12 07:44:16.302614	\N
45	6	34	3	8	2026-01-12 07:44:36.997274	2026-01-12 07:57:26.068216	769	f	normal	2026-01-12 07:44:36.998112	2026-01-12 07:57:26.084677	\N
46	6	34	3	8	2026-01-12 07:57:28.49619	2026-01-12 08:01:54.837732	266	f	normal	2026-01-12 07:57:28.496701	2026-01-12 08:01:54.869446	\N
47	6	34	3	8	2026-01-12 08:01:57.335603	2026-01-12 08:05:24.148255	206	f	gate_restart	2026-01-12 08:01:57.335603	2026-01-12 08:05:24.163005	\N
48	6	34	3	8	2026-01-12 08:01:57.374742	2026-01-12 08:05:24.148255	206	f	gate_restart	2026-01-12 08:01:57.375771	2026-01-12 08:05:24.16301	\N
49	6	34	3	8	2026-01-12 08:06:07.103517	2026-01-12 08:14:22.319636	495	f	gate_restart	2026-01-12 08:06:07.103517	2026-01-12 08:14:22.339024	\N
50	6	34	3	8	2026-01-12 08:06:07.139351	2026-01-12 08:14:22.319636	495	f	gate_restart	2026-01-12 08:06:07.140389	2026-01-12 08:14:22.33903	\N
51	6	34	3	8	2026-01-12 08:14:36.732755	2026-01-12 08:16:54.71077	137	f	gate_restart	2026-01-12 08:14:36.732755	2026-01-12 08:16:54.730935	\N
52	6	34	3	8	2026-01-12 08:14:36.771355	2026-01-12 08:16:54.71077	137	f	gate_restart	2026-01-12 08:14:36.7728	2026-01-12 08:16:54.730943	\N
53	6	34	3	8	2026-01-12 08:17:06.264197	2026-01-12 08:20:26.086822	199	f	gate_restart	2026-01-12 08:17:06.264197	2026-01-12 08:20:26.115357	\N
54	6	34	3	8	2026-01-12 08:17:06.308956	2026-01-12 08:20:26.086822	199	f	gate_restart	2026-01-12 08:17:06.310532	2026-01-12 08:20:26.115366	\N
55	6	34	3	8	2026-01-12 08:20:34.666739	2026-01-12 08:20:48.170467	13	f	normal	2026-01-12 08:20:34.666739	2026-01-12 08:20:48.197968	\N
56	6	34	3	8	2026-01-12 08:20:34.726905	2026-01-12 08:21:24.5694	49	f	normal	2026-01-12 08:20:34.728602	2026-01-12 08:21:24.584288	\N
57	6	34	3	8	2026-01-12 08:21:13.803298	2026-01-12 08:26:38.594879	324	f	gate_restart	2026-01-12 08:21:13.803298	2026-01-12 08:26:38.62608	\N
58	6	34	3	8	2026-01-12 08:21:13.825926	2026-01-12 08:26:38.594879	324	f	gate_restart	2026-01-12 08:21:13.826447	2026-01-12 08:26:38.626087	\N
59	6	34	3	8	2026-01-12 08:21:29.608285	2026-01-12 08:26:38.594879	308	f	gate_restart	2026-01-12 08:21:29.608285	2026-01-12 08:26:38.626089	\N
60	6	34	3	8	2026-01-12 08:21:29.639308	2026-01-12 08:26:38.594879	308	f	gate_restart	2026-01-12 08:21:29.639819	2026-01-12 08:26:38.626091	\N
61	6	34	3	8	2026-01-12 08:26:44.375782	2026-01-12 08:27:57.442672	73	f	normal	2026-01-12 08:26:44.375782	2026-01-12 08:27:57.471419	\N
62	6	34	3	8	2026-01-12 08:26:44.417466	2026-01-12 08:28:27.765671	103	f	normal	2026-01-12 08:26:44.418661	2026-01-12 08:28:27.77881	\N
76	6	37	3	8	2026-01-12 11:08:04.904903	2026-01-12 11:08:07.709075	2	f	normal	2026-01-12 11:08:04.907469	2026-01-12 11:08:07.731778	\N
77	6	37	3	8	2026-01-12 12:28:43.647415	2026-01-12 12:31:05.87718	142	f	gate_maintenance	2026-01-12 12:28:43.650156	2026-01-12 12:31:05.90652	\N
78	6	37	3	8	2026-01-12 12:34:49.037242	2026-01-12 15:47:10.452337	11541	f	gate_maintenance	2026-01-12 12:34:49.039305	2026-01-12 15:47:10.469883	\N
80	6	37	3	8	2026-01-12 15:48:11.317653	2026-01-12 15:51:41.567005	210	f	gate_maintenance	2026-01-12 15:48:11.319055	2026-01-12 15:51:41.601977	\N
81	6	37	3	8	2026-01-12 15:53:24.402297	2026-01-12 15:54:42.521345	78	f	gate_maintenance	2026-01-12 15:53:24.404612	2026-01-12 15:54:42.540905	\N
79	8	38	3	9	2026-01-12 14:12:59.71231	2026-01-12 16:00:47.757565	6468	f	gate_restart	2026-01-12 14:12:59.715475	2026-01-12 16:00:47.770575	\N
82	6	40	3	8	2026-01-12 16:06:36.685936	2026-01-12 16:08:07.766187	91	f	gate_maintenance	2026-01-12 16:06:36.687244	2026-01-12 16:08:07.790834	\N
83	6	40	3	8	2026-01-12 16:24:53.047068	2026-01-12 16:25:58.186184	65	f	gate_maintenance	2026-01-12 16:24:53.049369	2026-01-12 16:25:58.215534	\N
84	6	41	3	8	2026-01-12 16:26:23.783468	2026-01-12 16:26:57.842112	34	f	gate_maintenance	2026-01-12 16:26:23.784038	2026-01-12 16:26:57.85628	\N
85	6	42	3	8	2026-01-12 16:32:58.518733	2026-01-12 16:35:28.706125	150	f	gate_maintenance	2026-01-12 16:32:58.52017	2026-01-12 16:35:28.731511	\N
86	6	42	3	8	2026-01-12 16:36:04.582954	2026-01-12 16:43:30.078594	445	f	gate_maintenance	2026-01-12 16:36:04.584177	2026-01-12 16:43:30.11141	\N
87	6	43	3	8	2026-01-12 17:01:04.564934	2026-01-12 17:04:11.238011	186	f	gate_restart	2026-01-12 17:01:04.567737	2026-01-12 17:04:11.250967	\N
88	6	43	3	8	2026-01-12 17:04:52.863373	2026-01-12 17:09:58.422642	305	f	gate_restart	2026-01-12 17:04:52.865037	2026-01-12 17:09:58.437899	\N
89	6	43	3	8	2026-01-12 17:10:09.366491	2026-01-12 17:19:35.05119	565	f	gate_maintenance	2026-01-12 17:10:09.368113	2026-01-12 17:19:35.070032	\N
90	6	43	3	8	2026-01-12 17:22:58.198283	2026-01-12 17:32:00.871441	542	f	grant_expired	2026-01-12 17:22:58.201385	2026-01-12 17:32:00.897919	\N
91	6	44	3	8	2026-01-22 14:27:25.447722	2026-01-22 14:34:18.869306	413	f	normal	2026-01-22 14:27:25.4502	2026-01-22 14:34:18.899397	\N
92	6	44	3	8	2026-01-22 14:34:20.736398	2026-01-22 14:40:21.652596	360	f	normal	2026-01-22 14:34:20.737026	2026-01-22 14:40:21.666995	\N
93	6	44	3	8	2026-01-22 14:46:47.753791	2026-01-22 14:47:08.312859	20	f	normal	2026-01-22 14:46:47.758217	2026-01-22 14:47:08.336341	\N
94	6	44	3	8	2026-01-22 14:47:41.738443	2026-01-22 14:51:55.012497	253	f	gate_restart	2026-01-22 14:47:41.73895	2026-01-22 14:51:55.025967	\N
95	6	44	3	8	2026-01-22 14:52:11.14283	2026-01-22 15:02:22.337895	611	f	normal	2026-01-22 14:52:11.144491	2026-01-22 15:02:22.390465	\N
96	6	44	3	8	2026-01-22 15:03:12.792293	2026-01-22 15:03:29.339983	16	f	normal	2026-01-22 15:03:12.79415	2026-01-22 15:03:29.357277	\N
97	6	44	3	8	2026-01-22 15:07:42.948569	2026-01-22 15:08:15.541345	32	f	normal	2026-01-22 15:07:42.952451	2026-01-22 15:08:15.56745	\N
101	6	44	3	8	2026-01-27 15:17:41.790027	2026-01-27 15:20:51.799068	190	f	normal	2026-01-27 15:17:41.791328	2026-01-27 15:20:51.830425	\N
100	6	44	3	8	2026-01-27 15:17:32.929004	2026-01-27 16:21:42.938087	\N	f	manual_cleanup	2026-01-27 15:17:32.922838	2026-01-27 15:17:32.929011	\N
102	6	44	3	8	2026-01-27 15:26:06.464533	2026-01-27 15:26:30.215615	23	f	normal	2026-01-27 15:26:06.466536	2026-01-27 15:26:30.234012	\N
103	6	44	3	8	2026-01-27 15:27:35.19305	2026-01-27 15:29:08.324985	93	f	gate_maintenance	2026-01-27 15:27:35.194427	2026-01-27 15:29:08.346615	\N
104	6	44	3	8	2026-01-27 16:12:56.409279	2026-01-27 16:12:59.499118	3	f	normal	2026-01-27 16:12:56.411036	2026-01-27 16:12:59.522532	\N
105	6	44	3	8	2026-01-27 16:36:58.914861	2026-01-27 16:37:01.000931	2	f	normal	2026-01-27 16:36:58.916047	2026-01-27 16:37:01.021384	\N
107	6	44	3	8	2026-01-27 16:58:46.662559	2026-01-27 17:00:18.813716	92	f	gate_maintenance	2026-01-27 16:58:46.667513	2026-01-27 17:00:18.840369	\N
108	6	44	3	8	2026-01-27 17:00:31.393365	2026-01-27 17:01:49.558101	78	f	gate_maintenance	2026-01-27 17:00:31.394072	2026-01-27 17:01:49.578381	\N
106	6	44	3	8	2026-01-27 16:58:45.581751	\N	\N	f	\N	2026-01-27 16:58:45.579968	2026-01-27 16:58:45.581756	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
109	6	39	3	9	2026-01-28 09:21:02.323154	2026-01-28 09:21:25.423859	23	f	gate_maintenance	2026-01-28 09:21:02.324447	2026-01-28 09:21:25.447295	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
110	6	39	3	9	2026-01-28 09:24:11.484857	2026-01-28 09:24:26.523051	15	f	gate_maintenance	2026-01-28 09:24:11.485481	2026-01-28 09:24:26.538779	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
111	6	39	3	9	2026-01-28 09:24:42.861458	2026-01-28 09:24:55.897989	13	f	gate_maintenance	2026-01-28 09:24:42.862	2026-01-28 09:24:55.913534	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
112	6	39	3	9	2026-01-28 09:35:47.550844	2026-01-28 09:35:47.584047	0	f	error	2026-01-28 09:35:47.552267	2026-01-28 09:35:47.614544	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
113	6	39	3	9	2026-01-28 09:38:16.349354	2026-01-28 09:38:16.385743	0	f	error	2026-01-28 09:38:16.350743	2026-01-28 09:38:16.413249	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
114	6	39	3	9	2026-01-28 09:39:01.663694	2026-01-28 09:39:01.689861	0	f	error	2026-01-28 09:39:01.664922	2026-01-28 09:39:01.702404	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
115	6	39	3	9	2026-01-28 09:41:48.783019	2026-01-28 09:42:05.911383	17	f	gate_maintenance	2026-01-28 09:41:48.785549	2026-01-28 09:42:05.944962	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
116	6	39	3	9	2026-01-28 09:44:18.204632	2026-01-28 09:44:26.296116	8	f	gate_maintenance	2026-01-28 09:44:18.206726	2026-01-28 09:44:26.319827	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
117	6	39	3	9	2026-01-28 09:46:35.912714	2026-01-28 09:46:50.019732	14	f	gate_maintenance	2026-01-28 09:46:35.914803	2026-01-28 09:46:50.050012	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
118	6	39	3	9	2026-01-28 09:59:10.159617	2026-01-28 09:59:41.27226	31	f	gate_maintenance	2026-01-28 09:59:10.161623	2026-01-28 09:59:41.299562	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
119	6	39	3	9	2026-01-28 10:03:10.316593	2026-01-28 10:03:10.350741	0	f	error	2026-01-28 10:03:10.318321	2026-01-28 10:03:10.378671	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
120	6	39	3	9	2026-01-28 10:09:40.610164	2026-01-28 10:09:40.653671	0	f	error	2026-01-28 10:09:40.612155	2026-01-28 10:09:40.69449	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
121	6	39	3	9	2026-01-28 10:11:24.202514	2026-01-28 10:11:40.300979	16	f	gate_maintenance	2026-01-28 10:11:24.204077	2026-01-28 10:11:40.328455	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
122	6	39	3	9	2026-01-28 10:16:07.115968	2026-01-28 10:16:16.195621	9	f	gate_maintenance	2026-01-28 10:16:07.117448	2026-01-28 10:16:16.217828	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
123	6	39	3	9	2026-01-28 10:48:44.000697	2026-01-28 10:48:44.026295	0	f	error	2026-01-28 10:48:44.002195	2026-01-28 10:48:44.04942	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
124	6	39	3	9	2026-01-28 10:50:53.768083	2026-01-28 10:50:53.790952	0	f	error	2026-01-28 10:50:53.769811	2026-01-28 10:50:53.81429	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
125	6	39	3	9	2026-01-28 10:52:17.678579	2026-01-28 10:52:17.70395	0	f	error	2026-01-28 10:52:17.680092	2026-01-28 10:52:17.730374	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
126	6	39	3	9	2026-01-28 10:55:23.899036	2026-01-28 10:55:23.928404	0	f	error	2026-01-28 10:55:23.900825	2026-01-28 10:55:23.953606	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
127	6	39	3	9	2026-01-28 10:57:44.561396	2026-01-28 11:07:26.375634	581	f	gate_restart	2026-01-28 10:57:44.563346	2026-01-28 11:07:26.384222	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
128	6	39	3	9	2026-01-28 11:07:54.234025	2026-01-28 11:20:47.120101	772	f	grant_revoked	2026-01-28 11:07:54.235182	2026-01-28 11:20:47.145791	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
129	6	44	3	8	2026-01-28 11:25:45.685275	2026-01-28 11:29:49.91529	244	f	normal	2026-01-28 11:25:45.68638	2026-01-28 11:29:49.933784	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
130	6	39	3	9	2026-01-28 11:35:05.630292	2026-01-28 11:36:38.342855	92	f	gate_restart	2026-01-28 11:35:05.632217	2026-01-28 11:36:38.351585	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
131	6	39	3	9	2026-01-28 11:36:51.249441	2026-01-28 12:26:39.216524	2987	f	grant_revoked	2026-01-28 11:36:51.250522	2026-01-28 12:26:39.239852	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
132	6	44	3	8	2026-01-28 12:57:05.803798	2026-01-28 12:57:24.351274	18	f	normal	2026-01-28 12:57:05.807579	2026-01-28 12:57:24.378594	\N
133	6	45	4	10	2026-01-28 13:31:47.16249	2026-01-28 13:32:12.571994	25	f	normal	2026-01-28 13:31:47.164103	2026-01-28 13:32:12.622543	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
134	6	45	4	10	2026-01-28 13:32:48.237355	2026-01-28 14:10:48.767265	2280	f	normal	2026-01-28 13:32:48.237794	2026-01-28 14:10:48.812462	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
135	6	45	4	10	2026-01-28 14:11:11.412034	2026-01-28 14:19:05.138382	473	f	grant_revoked	2026-01-28 14:11:11.413432	2026-01-28 14:19:05.17874	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
136	6	45	4	10	2026-01-28 14:51:27.132138	2026-01-28 15:21:12.906247	1785	f	gate_restart	2026-01-28 14:51:27.133456	2026-01-28 15:21:12.92166	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
137	6	45	4	10	2026-01-28 15:22:11.591922	2026-01-28 15:23:50.465335	98	f	gate_restart	2026-01-28 15:22:11.593827	2026-01-28 15:23:50.476148	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
139	6	46	4	11	2026-01-29 07:02:36.622133	2026-01-29 07:02:52.352851	15	f	normal	2026-01-29 07:02:36.62282	2026-01-29 07:02:52.388183	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
140	6	46	4	11	2026-01-29 07:03:30.743826	2026-01-29 07:10:41.67538	430	f	normal	2026-01-29 07:03:30.744734	2026-01-29 07:10:41.715858	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
141	6	39	3	9	2026-01-30 09:10:01.307437	2026-01-30 10:09:31.633792	3570	f	grant_revoked	2026-01-30 09:10:01.308238	2026-01-30 10:09:31.687283	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
142	6	45	4	10	2026-02-18 12:34:12.512285	2026-02-18 12:34:12.646118	0	f	normal	2026-02-18 12:34:12.512939	2026-02-18 12:34:12.685306	\N
143	6	45	4	10	2026-02-18 12:34:51.067567	2026-02-18 12:39:45.781631	294	f	gate_restart	2026-02-18 12:34:51.068253	2026-02-18 12:39:45.789415	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
144	6	45	4	10	2026-02-18 12:40:26.291387	2026-02-18 12:41:51.180432	84	f	gate_restart	2026-02-18 12:40:26.292947	2026-02-18 12:41:51.189163	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
145	6	45	4	10	2026-02-18 12:42:11.035647	2026-02-18 12:43:47.310295	96	f	gate_restart	2026-02-18 12:42:11.037262	2026-02-18 12:43:47.320771	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
146	6	45	4	10	2026-02-18 12:44:13.421973	2026-02-18 12:46:35.464197	142	f	gate_restart	2026-02-18 12:44:13.424274	2026-02-18 12:46:35.473185	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
147	6	45	4	10	2026-02-18 12:46:53.72699	2026-02-18 12:49:41.781457	168	f	gate_restart	2026-02-18 12:46:53.728653	2026-02-18 12:49:41.784846	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
148	6	45	4	10	2026-02-18 12:50:04.839571	\N	\N	t	\N	2026-02-18 12:50:04.840203	2026-02-18 12:50:04.840209	FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=
\.


--
-- Data for Name: user_group_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_group_members (id, user_group_id, user_id, added_at) FROM stdin;
1	3	6	2026-01-05 11:40:10.836236
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
6	6	10.30.14.3	Biuro Linux	t	2026-01-04 10:29:18.715811
8	8	100.64.0.1	\N	t	2026-01-12 14:10:39.497108
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: jumphost_user
--

COPY public.users (id, username, email, full_name, is_active, created_at, updated_at, source_ip, port_forwarding_allowed) FROM stdin;
7	admin	admin@jumphost.local	\N	t	2026-01-04 13:32:30.049145	2026-01-04 13:32:30.049152	\N	f
6	p.mojski	p.mojski@ideosoftware.com	Paweł Mojski	t	2026-01-04 10:29:04.030238	2026-01-11 17:29:37.241911	\N	f
8	k.kawalec	k.kawalec@ideosoftware.com	Krzysztof Kawalec	t	2026-01-12 14:10:12.266367	2026-01-12 14:10:12.26638	\N	f
\.


--
-- Name: access_grants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.access_grants_id_seq', 6, true);


--
-- Name: access_policies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.access_policies_id_seq', 47, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 62, true);


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

SELECT pg_catalog.setval('public.mfa_challenges_id_seq', 148, true);


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

SELECT pg_catalog.setval('public.sessions_id_seq', 322, true);


--
-- Name: stays_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jumphost_user
--

SELECT pg_catalog.setval('public.stays_id_seq', 148, true);


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

SELECT pg_catalog.setval('public.users_id_seq', 8, true);


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

\unrestrict B3KL1Rzel6NcvHExPH8HX2Km38MzIE4chf9W8qOGg2obemTgV6mBgerekkjWZl6

