--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.2
-- Dumped by pg_dump version 9.6.2

-- Started on 2017-05-08 00:08:34 CEST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2147 (class 1262 OID 172125)
-- Name: scradaway; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE scradaway WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'es_ES.UTF-8' LC_CTYPE = 'es_ES.UTF-8';


\connect scradaway

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 1 (class 3079 OID 12410)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2149 (class 0 OID 0)
-- Dependencies: 1
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_with_oids = false;

--
-- TOC entry 185 (class 1259 OID 172141)
-- Name: downloaded_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE downloaded_data (
    site_name text NOT NULL,
    url text NOT NULL,
    timewhen timestamp with time zone,
    jsondata jsonb,
    pending_download boolean DEFAULT true,
    canonical_url text
);


--
-- TOC entry 2024 (class 2606 OID 172148)
-- Name: downloaded_data downloaded_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY downloaded_data
    ADD CONSTRAINT downloaded_data_pkey PRIMARY KEY (site_name, url);


--
-- TOC entry 2022 (class 1259 OID 173443)
-- Name: downloaded_data_jsondata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX downloaded_data_jsondata_idx ON downloaded_data USING gin (jsondata);


--
-- TOC entry 2025 (class 1259 OID 175357)
-- Name: downloaded_data_site_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX downloaded_data_site_name_idx ON downloaded_data USING btree (site_name) WHERE pending_download;


-- Completed on 2017-05-08 00:08:34 CEST

--
-- PostgreSQL database dump complete
--

