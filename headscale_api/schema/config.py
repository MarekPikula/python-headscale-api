# generated by datamodel-codegen:
#   filename:  config-example.yaml
#   timestamp: 2023-04-04T19:42:36+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Extra


class Noise(BaseModel):
    class Config:
        extra = Extra.allow

    private_key_path: Optional[str] = None


class Server(BaseModel):
    class Config:
        extra = Extra.allow

    enabled: Optional[bool] = None
    region_id: Optional[int] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    stun_listen_addr: Optional[str] = None


class Derp(BaseModel):
    class Config:
        extra = Extra.allow

    server: Optional[Server] = None
    urls: Optional[List[str]] = None
    paths: Optional[List] = None
    auto_update_enabled: Optional[bool] = None
    update_frequency: Optional[str] = None


class Log(BaseModel):
    class Config:
        extra = Extra.allow

    format: Optional[str] = None
    level: Optional[str] = None


class DnsConfig(BaseModel):
    class Config:
        extra = Extra.allow

    override_local_dns: Optional[bool] = None
    nameservers: Optional[List[str]] = None
    domains: Optional[List] = None
    magic_dns: Optional[bool] = None
    base_domain: Optional[str] = None


class Logtail(BaseModel):
    class Config:
        extra = Extra.allow

    enabled: Optional[bool] = None


class Model(BaseModel):
    class Config:
        extra = Extra.allow

    server_url: Optional[str] = None
    listen_addr: Optional[str] = None
    metrics_listen_addr: Optional[str] = None
    grpc_listen_addr: Optional[str] = None
    grpc_allow_insecure: Optional[bool] = None
    private_key_path: Optional[str] = None
    noise: Optional[Noise] = None
    ip_prefixes: Optional[List[str]] = None
    derp: Optional[Derp] = None
    disable_check_updates: Optional[bool] = None
    ephemeral_node_inactivity_timeout: Optional[str] = None
    node_update_check_interval: Optional[str] = None
    db_type: Optional[str] = None
    db_path: Optional[str] = None
    acme_url: Optional[str] = None
    acme_email: Optional[str] = None
    tls_letsencrypt_hostname: Optional[str] = None
    tls_letsencrypt_cache_dir: Optional[str] = None
    tls_letsencrypt_challenge_type: Optional[str] = None
    tls_letsencrypt_listen: Optional[str] = None
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    log: Optional[Log] = None
    acl_policy_path: Optional[str] = None
    dns_config: Optional[DnsConfig] = None
    unix_socket: Optional[str] = None
    unix_socket_permission: Optional[str] = None
    logtail: Optional[Logtail] = None
    randomize_client_port: Optional[bool] = None
